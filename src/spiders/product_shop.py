from base64 import b64encode

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from src.items import ProductScraperItem
import w3lib.html
from requests import request

from src.spiders.models import CacheModel
from src.spiders.schemas import ModelShop, ModelProducts, Image
from src.spiders.service import ApiRequests


class LivemasterShopSpider(CrawlSpider):
    api = ApiRequests('https://parser.handm.shop/v1', 'post', )
    redis_cache = CacheModel
    name = 'livemaster'
    host = 'https://www.livemaster.ru/'
    allowed_domains = ['livemaster.ru']
    start_urls = ['https://www.livemaster.ru/brands/']
    # www\.livemaster\.ru/\S+
    rules = (
        Rule(LinkExtractor(allow=r'/brand/\S+',
                           deny=('/item/', '/tag/', '/auth/', '/user*', '/help/', '/topic/')),
             callback='parse_shop'),

    )

    def parse_shop(self, response, **kwargs):
        """Парсинг бренд в магазин"""
        self.logger.info('Hi, this is an shop page! %s', response.url)
        item = ProductScraperItem()
        url = response.url.replace('brand/', '') + "?v=1&sortitems=0&cat=0&cid=0&from=0"
        yield response.follow(url, callback=self.parse_detail, cb_kwargs=dict(item=item),
                              meta=({"PerPageCount": {'value': 25}}))

    def parse_detail(self, response, item, next_page=True, **kwargs):
        """ Собираем информацию о магазине и его товаров """
        self.logger.info('Hi, this is an detail page! %s', response.url)
        item['shop_url'], _ = response.url.split('?')
        item['shop_name'] = response.xpath('//h1/text()').extract_first() \
            .replace('\n', '').replace('\t', '').replace('\r', '')  # название магазина
        item['shop_location'] = response.xpath('//div[@class="menu__location"]/text()').extract_first()
        item['shop_status'] = response.xpath(
            '//div[@class="menu__status js-content-master-status"]/text()').extract_first()
        item['profile_url'] = self.host + response.xpath(
            '//div[@class="menu-content"]//a[text()="Профиль"]/@href').extract_first()
        item['products_count'] = response.xpath(
            '//div[text()="Магазин"]/span[@class="menu-content__count"]/text()').extract_first()
        item['feedbacks_count'] = response.xpath(
            '//div[contains(text(),"Отзывы")]/span[@class="menu-content__count"]/text()').extract_first()
        item['feedbacks_url'] = self.host + response.xpath(
            '//div[@class="menu-content"]//div[contains(text(),"Отзывы")]/parent::a/@href').extract_first()
        item['policy_url'] = self.host + response.xpath(
            '//div[@class="menu-content"]//a[text()="Оплата и доставка"]/@href').extract_first()
        item['blog_url'] = self.host + response.xpath(
            '//div[@class="menu-content"]//div[text()="Блог"]/parent::a/@href').extract_first()
        item['blogs_count'] = response.xpath(
            '//div[text()="Блог"]/span[@class="menu-content__count"]/text()').extract_first()
        folowers_url = response.xpath(
            '//div[text()="Подписчики"]/span[@class="menu-content__count"]/text()').extract_first()
        item['folowers_url'] = self.host + folowers_url if folowers_url else None
        item['folowers_count'] = response.xpath(
            '//div[@class="menu-content"]//div[text()="Подписчики"]/parent::a/@href').extract_first()
        source_url = response.xpath('//img[@class="menu__avatar-img"]/@data-original').extract_first()
        item['shop_img'] = source_url
        img_dict = Image()
        if source_url:
            item['shop_img'] = source_url
            response_img = request("GET", source_url)
            img_content = response_img.content
            name, extension = source_url.split('?')[0].split('/')[-1].split('.')
            img_dict.content = b64encode(img_content)
            img_dict.extension = extension
            img_dict.source_url = source_url
            img_dict.name = name

        item_all = response.xpath('//a[@class="js-preview-images"]')
        if next_page:
            next_page_url = response.xpath('//a[@class="pagebar__page"]')  # пагинация
            data_shop: ModelShop = ModelShop.parse_obj(item.__dict__['_values'])
            data_shop.images.append(img_dict)
            data_json = data_shop.json(by_alias=True, exclude_none=True)

            if self.redis_cache.cache(item['shop_url'], data_json):
                if self.api.send('/Parse/Shop', data_json):
                    self.redis_cache.set(self.name, item['shop_url'], data_json)
            yield from response.follow_all(next_page_url, callback=self.parse_detail,
                                           cb_kwargs=dict(item=item, next_page=False))

        self.logger.info('item_all: %s', len(item_all))
        yield from response.follow_all(item_all, callback=self.parse_item, cb_kwargs=dict(item=item))

    def parse_item(self, response, item):
        """ Собираем информацию о товаре """
        self.logger.info('Hi, this is an item page! %s', response.url)
        item['products_url'] = response.url

        item['products_name'] = response.xpath('//h1/text()').extract_first() \
            .replace('\n', '').replace('\t', '').replace('\r', '')  # название товара

        product_price = w3lib.html.remove_tags(
            response.xpath('//span[@class="price__main"]/span//text()').extract_first())
        item['product_price'] = float(product_price.replace('\xa0', ''))  # цена

        discount = response.xpath('//div[@class="price__discount-count"]/text()').extract_first()
        item['product_discount'] = discount.strip().replace(u'\u2009', '') if discount else None

        old_price = response.xpath('//span[@class="dynamic-price-amount"]/text()').extract_first()
        item['product_old_price'] = old_price.replace('\xa0', '') if old_price else None

        count_sales = response.xpath(
            '//div[@class="rating-info__item rating-info__statistics"]/text()').extract_first()
        item['count_product_sales'] = count_sales.strip().split("\xa0")[0] if count_sales else None

        item['count_product_likes'] = response.xpath(
            '//span[@class="favorite-btn__counter js-favorite-counter"]/text()').extract_first()

        material = response.xpath('//span[@class="js-translate-item-materials"]/text()').extract_first()
        item['product_material'] = material.strip().replace('\t', '') if material else None

        size = response.xpath('//div[@class="js-translate-item-size"]/text()[2]').extract_first()
        item['product_size'] = size.strip() if size else None

        description = response.xpath('//div[starts-with(@class, "content__description")]/text()').getall()
        item['product_description'] = ''.join(description) if description else None

        care = response.xpath('//div[@class="js-translate-item-itemcare"]/text()').getall()
        item['product_care'] = ''.join(care) if care else None

        item['master_name'] = response.xpath('//a[@class="master__name"]/text()').extract_first()
        item['master_url'] = self.host + response.xpath('//a[@class="master__name"]/@href').extract_first()
        item['master_location'] = response.xpath('//div[@class="master__location"]/text()').extract_first()
        item['master_status'] = response.xpath('//div[@class="master__status ds-mb-6"]/text()').extract_first()

        item['terms_return'] = response.xpath(
            '//div[text()="Условия возврата и обмена"]/following-sibling::div/text()').extract_first()

        source_urls = response.xpath(
            '//a[@class="photo-switcher__slide js-switcher-slide"]//@href').getall()
        item['product_img'] = source_urls
        item['category_url'] = [self.host + i for i in
                                set(response.xpath('//a[@class="breadcrumbs__link"]/@href').extract())]

        data_product = ModelProducts.parse_obj(item.__dict__['_values'])
        # for key in data_product.__dict__:
        #     if value := item.get(key):
        #         setattr(data_product, key, value)
        for url in source_urls:
            response_img = request("GET", url)
            img_content = response_img.content
            name, extension = url.split('/')[-1].split('.')
            img_dict = {
                'content': b64encode(img_content),
                'extension': extension,
                'source_url': url,
                'name': name,
            }
            data_product.images.append(Image.parse_obj(img_dict))
        data_json = data_product.json(by_alias=True, exclude_none=True)

        if self.redis_cache.cache(item['products_url'], data_json):
            if self.api.send('/Parse/Product', data_json):
                self.redis_cache.set(self.name, item['products_url'], data_json)

        yield item
