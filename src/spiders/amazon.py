import json
import re
from base64 import b64encode

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from src.items import AmazonScrapperItem
from src.spiders.models import CacheModel
from requests import request

from src.spiders.schemas import ProductsModel, Image
from src.spiders.service import ApiRequests


# TODO: Класс который исправляет ошибки в .json
class LazyDecoder(json.JSONDecoder):
    def decode(self, s, **kwargs):
        regex_replacements = [
            (re.compile(r'([^\\])\\([^\\])'), r'\1\\\\\2'),
            (re.compile(r',(\s*])'), r'\1'),
        ]
        for regex, replacement in regex_replacements:
            s = regex.sub(replacement, s)
        return super().decode(s, **kwargs)


def list_split(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class AmazonProductSpider(scrapy.Spider):
    api = ApiRequests('https://parser.shoppertopper.tech/v1', 'post', )
    redis_cache = CacheModel
    name = 'amazon'
    host = 'https://www.amazon.ae'
    allowed_domains = ['amazon.ae']
    start_urls = [
        # 'https://www.amazon.ae/s?i=electronics&rh=n%3A11601326031&fs=true&page=1&qid=1659072439&ref=sr_pg_1',
        # 'https://www.amazon.ae/s?rh=n%3A11601326031&fs=true&ref=lp_11601326031_sar'
        # f'https://www.amazon.ae/s?i=electronics&rh=n%3A11601326031&fs=true&page={i}' for i in range(1, 401)
        f'https://www.amazon.ae/s?i=electronics&rh=n%3A15415001031&fs=true&page={i}' for i in range(1, 401)

    ]
    default_category = ['https://www.amazon.ae/b/ref=dp_bc_aui_C_3?ie=UTF8&node=15415001031']
    # TODO: Селекторы для всех возможных цен
    price_selectors = [
        {
            'price': 'span.a-price-whole::text',
            'currency': 'span.a-price-symbol::text',
            'fraction': 'span.a-price-fraction::text',
            'discount': 'span.savingsPercentage::text',
            'old_price': 'span.a-price.a-text-price span::text'
        },
        {
            'price': 'span.a-text-price.a-size-medium span.a-offscreen::text',
            'discount': 'td.a-color-price.a-size-base span.a-color-price ::text',
            'old_price': 'span.a-text-price.a-size-base span::text'
        }

    ]

    def parse(self, response, **kwargs):
        """Парсинг всех товаров"""
        self.logger.info('Hi, this is an product page! %s', response.url)
        item = AmazonScrapperItem()
        see_all_results = response.xpath('//span[text()="See all results"]/../@href').get()
        if see_all_results:
            yield response.follow(see_all_results, callback=self.parse)
        products_url = response.xpath('//a[@class="a-link-normal s-underline-text s-underline-link-text '
                                      's-link-style a-text-normal" and not(contains(@href, "/gp/"))]/@href').getall()
        yield from response.follow_all(products_url, callback=self.parse_detail, cb_kwargs=dict(item=item))
        # next_page = response.xpath('//a[contains(@class,"s-pagination-next")]/@href').get()
        # if next_page:
        #     yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response, item):
        """ Собираем информацию о товаре """
        self.logger.info('Hi, this is an item page! %s', response.url)
        item['products_url'] = response.url
        item['products_title'] = \
            response.xpath('//span[contains(@class, "product-title-word-break")]/text()').get().strip()
        shop = response.css('.tabular-buybox-text[tabular-attribute-name="Sold by"] a')
        if shop:
            item['shop_link'] = self.host + shop.css('::attr(href)').get()
            item['shop_name'] = shop.css('::text').get()
        else:
            item['shop_link'] = self.host
            item['shop_name'] = \
                response.css('.tabular-buybox-text[tabular-attribute-name="Sold by"] .a-size-small::text').get()
        # TODO: Парсит к какому категорию товар принадлежит при наличии таковых, иначе парсит смежные категории
        category = [self.host + i for i in response.css('a.a-link-normal.a-color-tertiary::attr(href)').getall()]
        item['category_url'] = [category[-1]] if category else self.default_category
        # TODO: Парсим цен
        selector = self.price_selectors
        price_1 = response.css(selector[0].get('price')).get()
        price_2 = response.css(selector[1].get('price')).get()
        max_price = None
        if price_1 or price_2:
            if price_1 and price_2 is None:
                item['price'] = price_1.replace(',', '') + '.' + response.css(selector[0].get('fraction')).get()
                item['price_currency'] = response.css(selector[0]['currency']).get()
                old_price = response.css(selector[0]['old_price']).get()
                discount = response.css(selector[0]['discount']).get()
                item['products_discount'] = discount.replace('%', '').replace('-', '') if discount else None
            else:
                max_p = response.css(selector[1].get('price'))[1].get()
                if max_p and max_p != price_2:
                    max_price = max_p.replace(',', '').replace('AED', '')
                item['price'], item['price_currency'] = price_2.replace(',', '').replace('AED', ''), 'AED'
                old_price = response.css(selector[1]['old_price']).get()
                discount = response.css(selector[1]['discount']).getall()
                item['products_discount'] = discount[-1].split('(')[1].replace('%)', '') if discount else None

        else:
            item['price'] = None
            item['price_currency'] = None
            old_price = None
            item['products_discount'] = None
            max_price = None

        item['products_old_price'] = old_price.replace(',', '').replace('AED', '') if old_price else None
        item['max_price'] = max_price
        subscription_price = response.xpath('//span[@id="subscriptionPrice"]/span/text()').get()
        if subscription_price:
            item['subscription_discount'] = response.xpath('//span[@class="discountText"]/text()').get()
            item['subscription_price'] = subscription_price.strip().replace('\xa0', '')

        installment_section = response.xpath('//span[@class="best-offer-name a-text-bold"]/text()').get()
        if installment_section:
            installments = {'installment_description': installment_section.replace('\xa0', ''),
                            'bank_offers': self.host + response.xpath('//a[contains(text(), "Click here") '
                                                                      'and contains(@href, "/gp/help/customer/")]/@href').get()
                            }
            table_1 = response.xpath('//table[@id="InstallmentCalculatorTable"]//th/text()').extract()
            table_2 = response.xpath('//table[@id="InstallmentCalculatorTable"]//td/text()').extract()
            table_3 = list(list_split(table_2, 3))
            installments['installment_table'] = [{j: i[n].replace('\xa0', '') for n, j in enumerate(table_1)}
                                                 for i in table_3]

            item['installments'] = installments
        info_tr = response.xpath('//table[@class="a-normal a-spacing-micro"]//tr')
        short_info = {i.xpath('td[@class="a-span3"]/span/text()').get().strip():
                          i.xpath('td[@class="a-span9"]/span/text()').get().strip() for i in
                      info_tr} if info_tr else None

        about_this_item = \
            response.xpath('//ul[contains(@class, "a-spacing-mini")]/li[not(@id)]/span/text()').getall()
        t_details_tr = response.xpath('//table[@id="productDetails_techSpec_section_1"]//tr')
        t_detail_tr_2 = response.xpath('//h2[text()="Technical details"]/following::table[@class="a-bordered"]//tr')
        detail = \
            response.xpath(
                '//h2[text()="Product details"]/following::div[@id="detailBullets_feature_div"]//span[@class="a-list-item"]')
        if t_details_tr:
            technical_details = \
                {i.xpath('th/text()').get().strip(): x.strip().replace('\u200e', '') if (
                    x := i.xpath('td/text()').get()) else None for i in t_details_tr} \
                if t_details_tr.xpath('th/text()') else {}
        elif t_detail_tr_2:
            technical_details = {i.xpath('td/p/strong/text()').get().strip():
                                     x.strip().replace('\u200e', '') if (x := i.xpath('td/p/text()').get()) else None
                                 for i in t_detail_tr_2} if t_detail_tr_2.xpath('td/p/strong/text()') else {}
        elif detail:
            technical_details = \
                {i.xpath('span[@class="a-text-bold"]/text()').get().replace('\u200f', '').replace('\n', '')
                    .replace('\u200e', '').replace(':', '').strip(): x.replace('\u200e', '').strip()
                    if (x := i.xpath('span[not(@class)]/text()').get()) else None for i in detail} \
                if detail.xpath('span[@class="a-text-bold"]/text()') else {}
        else:
            technical_details = {}
        item['technical_details'] = technical_details
        item['short_info'] = short_info
        item['about_this_item'] = about_this_item
        if short_info:
            technical_details.update(short_info)
        if about_this_item:
            technical_details.update({k: v for k, v in enumerate(about_this_item, 1)})
        item['features'] = technical_details
        brand = response.css('tr.po-brand span::text')
        model = response.css('tr.po-model_name span::text')
        item['brand'] = brand[1].get() if brand else None
        item['model'] = model[1].get() if model else None
        # TODO: Парсим изображений
        script = response.css('div#imageBlockVariations_feature_div script[type="text/javascript"]').get()
        script_2 = response.css(
            'div#imageBlock_feature_div script[type="text/javascript"]:contains("colorImages")::text').get()
        if script:
            img_json = re.findall("var obj = jQuery.parseJSON\('(.+?)'\);\n", script, re.S)
            data = json.loads(img_json[0], cls=LazyDecoder)
            image_urls = \
                set([x if (x := j.get('hiRes')) else j.get('large') for i in data['colorImages'].values() for j in i])
            item['image_urls'] = image_urls
        else:
            image_urls = []
        if len(image_urls) == 0 and script_2:
            img_json = re.findall("'colorImages': \{ 'initial': (.+?)\},\n", script_2, re.S)
            data = json.loads(img_json[0])
            image_urls = [x if (x := i.get('hiRes')) else i.get('large') for i in data]
        item['image_urls'] = image_urls
        other_s_price = response.xpath('//span[contains(@id,"mbc-price-")]')
        other_s_name = [{'price': i.xpath('text()').get().replace("\xa0", "").strip(),
                         'name': i.xpath('..//span[@class="a-size-small mbcMerchantName"]')} for i in other_s_price]
        item['other_sellers'] = [{'price': i["price"],
                                  'name': i["name"].xpath("text()").get().strip(),
                                  'url': self.host + x if
                                  (x := response.xpath(f'//a[contains(text(),"{i["name"].xpath("text()").get()}")]'
                                                       f'/@href').get()) else None} for i in other_s_name]
        data_product = ProductsModel.parse_obj(item.__dict__['_values'])
        for url in image_urls:
            response_img = request("GET", url)
            img_content = response_img.content
            name = url.split('/')[-1].split('.')[0]
            extension = url.split('/')[-1].split('.')[-1]
            img_dict = {
                'content': b64encode(img_content),
                'extension': extension,
                'source_url': url,
                'name': name,
            }
            data_product.images.append(Image.parse_obj(img_dict))
        data_json = data_product.json(by_alias=True, exclude_none=True)

        if self.redis_cache.cache(item['products_url'], data_json):
            if self.api.send('/Parse/Product', data_product.json(by_alias=True, exclude_none=True)):
                self.redis_cache.set(self.name, item['products_url'], data_json)

        yield item
