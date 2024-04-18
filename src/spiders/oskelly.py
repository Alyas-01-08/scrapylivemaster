from base64 import b64encode

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from src.items import OskellyScraperItem
import w3lib.html
from requests import request

from src.spiders.models import CacheModel
from src.spiders.schemas import ModelShop, ModelProducts, Image
from src.spiders.service import ApiRequests, RedisCache


class OskellyShopSpider(scrapy.Spider):
    api = ApiRequests('https://parser.bloha.pro/v1', 'post', )
    redis_cache = CacheModel
    name = 'oskelly'
    host = 'https://oskelly.ru'
    allowed_domains = ['oskelly.ru']
    start_urls = [
        'https://oskelly.ru/catalog/muzhskoe/aksessuary',
        'https://oskelly.ru/catalog/muzhskoe/beauty',
        'https://oskelly.ru/catalog/muzhskoe/obuv',
        'https://oskelly.ru/catalog/muzhskoe/odezhda',
        'https://oskelly.ru/catalog/muzhskoe/sumki',
        'https://oskelly.ru/catalog/detskoe/devochki-0-3',
        'https://oskelly.ru/catalog/detskoe/devochki-4-14',
        'https://oskelly.ru/catalog/detskoe/malchiki-0-3',
        'https://oskelly.ru/catalog/detskoe/malchiki-4-14',
        'https://oskelly.ru/catalog/zhenskoe/aksessuary',
        'https://oskelly.ru/catalog/zhenskoe/beauty',
        'https://oskelly.ru/catalog/zhenskoe/obuv',
        'https://oskelly.ru/catalog/zhenskoe/odezhda',
        'https://oskelly.ru/catalog/zhenskoe/sumki',
    ]

    # rules = (
    #     Rule(LinkExtractor(allow=r'/products/\S+'),
    #          callback='parse_detail'),
    #
    # )

    def parse(self, response, **kwargs):
        """Парсинг всех товаров"""
        self.logger.info('Hi, this is an product page! %s', response.url)
        item = OskellyScraperItem()
        products_url = response.xpath('//a[@class="catalog-product-item__card-img"]/@href')
        yield from response.follow_all(products_url, callback=self.parse_detail, cb_kwargs=dict(item=item))
        next_page = response.xpath('//div[@class="next_pag"]/a/@data-next-page').get()
        if next_page:
            next_page_url = f'https://oskelly.ru/catalog?page={next_page}'
            yield response.follow(next_page_url, callback=self.parse)

    def parse_shop(self, response, item):
        """Парсинг страницы магазина"""
        self.logger.info('Hi, this is an shop page! %s', response.url)

        item['profile_url'] = response.url
        item['shop_name'] = response.xpath('//div[@class="profile-data__title playfair"]/text()').extract_first()  # название магазина
        item['how_long'] = response.xpath('//p[@class="profile-data__text"]/text()').extract_first()
        item['seller_type'] = response.xpath('//span[@class="profile-data__text"]/text()').extract_first()
        account_info = response.xpath('//div[@class="profile-data__count-number"]/text()').getall()
        item['products_count'] = int(account_info[0])
        item['followers_count'] = int(account_info[1])
        item['follows_count'] = int(account_info[2])
        verified_icon = response.xpath('//div[@class="profile-data__trust"]').extract_first()
        item['verified_icon'] = True if verified_icon else False
        source_url = response.xpath('//img[@class="user-avatar__image"]/@src').extract_first()
        item['shop_img'] = source_url
        img_dict = Image()
        if source_url:
            response_img = request("GET", source_url)
            img_content = response_img.content
            name_extension = source_url.split('/')[-1].split('.')
            name, extension = name_extension if len(name_extension) == 2 else (name_extension[0], None)
            img_dict.content = b64encode(img_content)
            img_dict.extension = extension
            img_dict.source_url = source_url
            img_dict.name = name

        data_shop: ModelShop = ModelShop.parse_obj(item.__dict__['_values'])
        data_shop.images.append(img_dict)
        data_json = data_shop.json(by_alias=True, exclude_none=True)

        if self.redis_cache.cache(item['profile_url'], data_json):
            if self.api.send('/Parse/Shop', data_shop.json(by_alias=True, exclude_none=True)):
                self.redis_cache.set(self.name, item['profile_url'], data_json)

        yield item

        # item_all = response.xpath('//div[@class="product_img"]/a')
        # self.logger.info('item_all: %s', len(item_all))
        # yield from response.follow_all(item_all, callback=self.parse_detail, cb_kwargs=dict(item=item))

    def parse_detail(self, response, item):
        """ Собираем информацию о товаре """
        self.logger.info('Hi, this is an item page! %s', response.url)
        item['products_url'] = response.url
        brand = response.xpath('//h1[@class="product__heading"]')
        products_name = response.xpath('//div[@class="product__info"]/span/text()').get()
        item['products_name'] = products_name + brand.xpath('text()').get()
        item['brands_name'] = brand.xpath('text()').get()
        # item['short_info'] = response.xpath('//div[@class="all_info-block__text"]/p/text()').extract_first()
        item['product_price'] = \
            float(response.xpath('//span[@class="product__price__curr__num"]/text()').get().strip().replace('\xa0', ''))
        old_price = response.xpath('//div[@class="product__price__old"]/text()').extract_first()
        item['product_old_price'] = float(old_price.replace('\xa0', '').replace('₽', '').strip()) if old_price else None
        item['product_discount'] = response.xpath('//div[@class="product__price__discount"]/text()').extract_first()
        item['master_name'] = response.xpath('//div[@class="user-card__name"]/a/text()').extract_first()
        # item['short_about_seller'] = ', '.join(response.xpath('//div[@class="info"]/text()').getall()[1:]).strip()
        shop_url = self.host + response.xpath('//div[@class="user-card__name"]/a/@href').get()
        item['master_url'] = shop_url
        description = response.xpath('//div[@class="product-seller__description"]/text()').get()
        item['product_description'] = description.replace('\r', '') if description else ''
        item['section'] = response.xpath('//span[text()="Раздел"]/../following-sibling::div//span/text()').get()
        item['category'] = response.xpath('//span[text()="Категория"]/../following-sibling::div//span/text()').get()
        item['color'] = response.xpath('//span[text()="Цвет"]/../following-sibling::div//span/text()').get()
        item['product_condition'] = \
            response.xpath('//span[text()="Состояние товара"]/../following-sibling::div//span/text()').get()
        item['oskelly_id'] = int(response.xpath('//span[text()="Oskelly ID"]/../following-sibling::div//span/text()').get())
        item['size_type'] = response.xpath('//span[text()="Тип размера"]/../following-sibling::div//span/text()').get()
        size = response.xpath('//span[text()="Размер"]/../following-sibling::div//span/text()').get()
        item['product_size'] = size.strip() if size else None
        item['vintage'] = response.xpath('//span[text()="Винтаж"]/../following-sibling::div//span/text()').get()
        item['product_material'] = \
            response.xpath('//span[starts-with(text(), "Материал")]/../following-sibling::div//span/text()').get()
        item['bracelet'] = response.xpath('//span[text()="Браслет часов"]/../following-sibling::div//span/text()').get()
        item['mechanism'] = response.xpath('//span[text()="Механизм"]/../following-sibling::div//span/text()').get()
        item['have_box'] = response.xpath('//span[text()="Наличие коробки"]/../following-sibling::div//span/text()').get()
        source_urls = response.xpath('//li[contains(@class, "image")]/img/@src').getall()
        item['product_images'] = source_urls
        category_url = response.xpath('//div[@class="breadcrumbs product"]/a/@href').getall()[1:-1]
        item['category_url'] = [self.host + i for i in category_url]
        data_product = ModelProducts.parse_obj(item.__dict__['_values'])
        for url in source_urls:
            response_img = request("GET", url)
            img_content = response_img.content
            name_extension = url.split('/')[-1].split('.')
            name, extension = name_extension if len(name_extension) == 2 else (name_extension[0], None)
            img_dict = {
                'content': b64encode(img_content),
                'extension': extension,
                'source_url': url,
                'name': name,
            }
            data_product.images.append(Image.parse_obj(img_dict))
        data_json = data_product.json(by_alias=True, exclude_none=True, exclude={'images'})
        #
        if self.redis_cache.cache(item['products_url'], data_json):
            if self.api.send('/Parse/Product', data_product.json(by_alias=True, exclude_none=True)):
                self.redis_cache.set(self.name, item['products_url'], data_json)
        yield response.follow(shop_url, callback=self.parse_shop, cb_kwargs=dict(item=item))
