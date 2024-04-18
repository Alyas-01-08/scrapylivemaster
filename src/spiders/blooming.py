from base64 import b64encode

import scrapy
from requests import request

from src.items import AeScrapperItem
from src.spiders.models import CacheModel
from src.spiders.schemas import ProductsModel, Image, ShopModel
from src.spiders.service import ApiRequests


class BloomingSpider(scrapy.Spider):
    api = ApiRequests('https://parser.shoppertopper.fashion/v1', 'post', )
    redis_cache = CacheModel
    name = 'blooming'
    host = 'http://bloomingdales.ae'
    allowed_domains = ['bloomingdales.ae']
    start_urls = ['https://bloomingdales.ae/designers/']

    def parse(self, response, **kwargs):
        """Парсинг всех брендов"""
        self.logger.info('Hi, this is an designers page! %s', response.url)
        urls = response.css('a.b-brands-list__item::attr(href)')
        yield from response.follow_all(urls, callback=self.parse_shop)

    def parse_shop(self, response, **kwargs):
        """Парсинг всех товаров бренда"""
        self.logger.info('Hi, this is an shop page! %s', response.url)
        item = AeScrapperItem()
        item['brands_url'] = response.url
        brands_name = response.css('h1.b-category-intro__category::text').get()
        item['brands_name'] = brands_name.strip() if brands_name else None
        banner_image = response.css('img.b-banner__image::attr(src)').get()
        img_url = self.host + banner_image if banner_image else None
        item['brands_main_photo'] = img_url
        item['brands_description'] = response.css('span.b-readmore__content::text').get()
        total_hits = response.css('div.b-progress-bar::attr(aria-valuemax)').get()
        item['products_count'] = total_hits.replace(".0", "") if total_hits else None
        data_shop: ShopModel = ShopModel.parse_obj(item.__dict__['_values'])
        if img_url:
            response_img = request("GET", img_url)
            img_content = response_img.content
            name, extension = img_url.split('/')[-1].split('.')
            img_dict = {
                'content': b64encode(img_content),
                'extension': extension,
                'source_url': img_url,
                'name': name,
            }
            data_shop.images.append(Image.parse_obj(img_dict))
        data_json = data_shop.json(by_alias=True, exclude_none=True)
        if self.redis_cache.cache(item['brands_url'], data_json):
            if self.api.send('/Parse/Shop', data_json):
                self.redis_cache.set(f'{self.name}_shop', item['brands_url'], data_json)

        if total_hits:
            url = f'{response.url}?start=0&sz={total_hits.replace(".0", "")}'
            yield response.follow(url, callback=self.parse_shop, cb_kwargs=dict(item=item))
        products_url = response.css('a.blm-producttile__image-link::attr(href)').getall()
        yield from response.follow_all(products_url, callback=self.parse_detail, cb_kwargs=dict(item=item))

    def parse_detail(self, response, item):
        """ Собираем информацию о товаре """
        self.logger.info('Hi, this is an item page! %s', response.url)
        item['products_url'] = response.url
        item['products_title'] = response.css('div.blm-pdpmain__product-name::text').get()
        item['shop_name'] = response.css('a.blm-pdpmain__product-brand::text').get()
        item['shop_link'] = self.host + response.css('a.blm-pdpmain__product-brand').attrib['href']
        item['price'] = response.css('.blm-pdpmain__price .blm-price__sale .blm-price__value::attr(content)').get()
        item['products_old_price'] = \
            response.css('.blm-pdpmain__price .blm-price__standard .blm-price__value::attr(content)').get()
        discount = response.css('.blm-pdpmain__price .blm-price__standard .blm-price__percentage::text').get()
        item['products_discount'] = discount.strip().replace(' OFF', '').replace('%', '') if discount else None
        item['products_color'] = response.css('.js-color-label-value::text').get()
        item['products_size'] = response.css('.js-size-label::text').get()
        availability = response.css('.js-attribute-availability::text').get()
        item['products_availability'] = availability.strip().replace('(', '').replace(')', '') if availability else None
        images = response.css('.js-carousel__images-item img::attr(src)').getall()
        description: list = response.css('div#pdp-details p ::text').getall()
        tr = response.css('figure.table tr')
        tr2 = [i for i in tr if len(i.css('td')) > 1]
        # table = [td.css('td ::text').getall()[1:] for td in tr2]
        items = []
        for td in tr2:
            items.extend(td.css('td ::text').getall()[1:])
        item['products_description'] = ' '.join(description)
        item['product_code'] = response.css('.product-id::text').get()
        item['product_master_id'] = response.css('.product-master-id::text').get()
        item['about_products_brand'] = response.css('div#pdp-brandinfo p::text').get()
        size = response.css('div#pdp-sizeandfit .blm-accordion__scroll ::text').getall()
        if size:
            size_fit = [i for i in size if i != '\n']
            items.extend(size_fit)
            item['size_fit'] = size_fit
        item['products_ingredients'] = response.css('div#pdp-ingredients p::text').get()
        item['img_urls'] = images
        category = response.css('a.blm-breadcrumb__link::attr(href)').getall()
        item['category_url'] = [i if i.startswith('https://') else self.host + i for i in category] \
            if len(category) > 0 else []
        data_product = ProductsModel.parse_obj(item.__dict__['_values'])
        for url in images:
            response_img = request("GET", url)
            img_content = response_img.content
            name, extension = url.split('/')[-1].split('?')[0].split('.')
            img_dict = {
                'content': b64encode(img_content),
                'extension': extension,
                'source_url': url,
                'name': name,
            }
            data_product.images.append(Image.parse_obj(img_dict))
        data_product.features = {k: v for k, v in enumerate(items, 1)}
        data_json = data_product.json(by_alias=True, exclude_none=True)

        if self.redis_cache.cache(item['products_url'], data_json):
            if self.api.send('/Parse/Product', data_product.json(by_alias=True, exclude_none=True)):
                self.redis_cache.set(self.name, item['products_url'], data_json)

        yield item
