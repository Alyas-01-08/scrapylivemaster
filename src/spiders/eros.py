import json
from base64 import b64encode

import scrapy
from requests import request

from src.items import ErosScrapperItem
from src.spiders.models import CacheModel
from src.spiders.schemas import ProductsModel, Image
from src.spiders.service import ApiRequests


class ErosProductSpider(scrapy.Spider):
    api = ApiRequests('https://parser.shoppertopper.online/v1', 'post', )
    redis_cache = CacheModel
    name = 'eros'
    host = 'https://www.eros.ae'
    allowed_domains = ['eros.ae']
    start_urls = [
        'https://www.eros.ae/smart-phones.html?product_list_limit=all',
        'https://www.eros.ae/computers-tablets.html?product_list_limit=all',
        'https://www.eros.ae/wearables.html?product_list_limit=all',
        'https://www.eros.ae/accessories.html?product_list_limit=all',
    ]

    def parse(self, response, **kwargs):
        """Парсинг всех товаров"""
        self.logger.info('Hi, this is an product page! %s', response.url)
        item = ErosScrapperItem()
        products_url = response.xpath('//div[contains(@class,"product photo ")]/a/@href')
        yield from response.follow_all(products_url, callback=self.parse_detail, cb_kwargs=dict(item=item))

    def parse_detail(self, response, item):
        """ Собираем информацию о товаре """
        self.logger.info('Hi, this is an item page! %s', response.url)
        item['products_url'] = response.url
        item['products_title'] = response.xpath('//span[@data-ui-id="page-title-wrapper"]/text()').get()
        item['model'] = response.xpath('//strong[@class="type-model"]/following-sibling::text()').get().strip()
        highlights = response.xpath('//div[@class="pdp-key_features"]//li/text()').getall()
        item['highlights'] = highlights
        price = response.xpath('//span[contains(@id,"product-price-")]/span/text()').get()
        item['price'] = price
        old_price = response.xpath('//span[contains(@id,"old-price-")]/span/text()').get()
        if old_price:
            item['products_old_price'] = old_price
            item['products_discount'] = round((float(old_price) - float(price)) * 100 / float(old_price))
        item['warranty'] = response.xpath('//strong[contains(text(), "Warranty")]/following-sibling::div/text()').get()
        tr = response.xpath('//table[contains(@id,"product-attribute-specs-table")]//tr')
        technical_details = {i.xpath('th/text()').get().strip(): i.xpath('td/text()').get().strip() for i in tr} \
            if tr else None
        item['technical_details'] = technical_details
        if highlights:
            technical_details.update({k: v for k, v in enumerate(highlights, 1)})
        item['category_url'] = response.css('.breadcrumbs a::attr(href)').getall()
        gallery_json = response.xpath('//script[@type="text/x-magento-init" '
                                      'and contains(text(),"[data-gallery-role=gallery-placeholder]")]/text()').get()
        g_dict = json.loads(gallery_json)
        g_data = g_dict['[data-gallery-role=gallery-placeholder]']['mage/gallery/gallery']['data']
        images = [i.get('full') for i in g_data]
        item['img_urls'] = images

        data_product = ProductsModel.parse_obj(item.__dict__['_values'])
        for url in images:
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

        data_product.features = technical_details
        data_json = data_product.json(by_alias=True, exclude_none=True, exclude={'images'})
        if self.redis_cache.cache(item['products_url'], data_json):
            if self.api.send('/Parse/Product', data_product.json(by_alias=True, exclude_none=True)):
                self.redis_cache.set(self.name, item['products_url'], data_json)

        yield item
