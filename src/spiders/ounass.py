from base64 import b64encode

import scrapy
from requests import request

from src.items import AeScrapperItem
from src.spiders.models import CacheModel
from src.spiders.schemas import ProductsModel, Image, ShopModel
from src.spiders.service import ApiRequests


class OunassSpider(scrapy.Spider):
    api = ApiRequests('https://parser.shoppertopper.fashion/v1', 'post', )
    redis_cache = CacheModel
    name = 'ounass'
    host = 'https://www.ounass.ae'
    allowed_domains = ['www.ounass.ae']
    start_urls = [
        'https://www.ounass.ae/women/designers',
        'https://www.ounass.ae/men/designers',
        'https://www.ounass.ae/kids/designers'
    ]

    def parse(self, response, **kwargs):
        """Парсинг всех дизайнеров"""
        self.logger.info('Hi, this is an designers page! %s', response.url)
        urls = response.css('div.Brands-names a::attr(href)')
        yield from response.follow_all(urls, callback=self.parse_shop)

    def parse_shop(self, response, **kwargs):
        """Парсинг всех товаров дизайнера"""
        self.logger.info('Hi, this is an shop page! %s', response.url)
        item = AeScrapperItem()
        item['brands_url'] = response.url
        item['brands_name'] = response.css('.PLP-title ::text').get()
        main_photo = response.css('img.Banner-image::attr(src)').get()
        img_url = 'https:' + main_photo if main_photo else None
        item['brands_main_photo'] = img_url
        item['brands_description'] = response.css('p.Banner-description-text::text').get()
        total_hits = response.css('span.PLP-resultCount::attr(data-total-hits)').get()
        item['products_count'] = total_hits
        data_shop: ShopModel = ShopModel.parse_obj(item.__dict__['_values'])
        if img_url:
            response_img = request("GET", img_url)
            img_content = response_img.content
            img_name_context = img_url.split('/')[-1].split('?')[0]
            name, extension = ('.'.join(x[:-1]), x[-1]) if len(x := img_name_context.split('.')) > 2 else \
                x if len(x) == 2 else (*x, 'jpg')
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

        total_pages = int(total_hits) // 24 if total_hits else 0
        for i in range(0, total_pages + 1):
            # url = f'{response.url}&p={i}'
            url = f'{response.url}?p={i}'
            yield response.follow(url, callback=self.products_parse, cb_kwargs=dict(item=item))

    def products_parse(self, response, item):
        """ Собираем ссылки продуктов """
        products_url = response.css('a.Product-link::attr(href)').getall()
        yield from response.follow_all(products_url, callback=self.parse_detail, cb_kwargs=dict(item=item))

    def parse_detail(self, response, item):
        """ Собираем информацию о товаре """
        self.logger.info('Hi, this is an item page! %s', response.url)
        item['products_url'] = response.url
        item['price'] = response.css('[itemprop="price"]').attrib['content']
        item['price_currency'] = response.css('[itemprop="priceCurrency"]').attrib['content']
        category_url = response.css('.BreadcrumbList a::attr(href)').getall()
        item['category_url'] = [self.host + '/' + i for i in category_url] if category_url else []
        brand = response.css('.PDPDesktop-designerCategoryName a')
        if brand:
            item['products_title'] = response.css('h1.PDPDesktop-name span::text').get()
            item['shop_link'] = self.host + brand.css('::attr(href)').get()
            item['shop_name'] = brand.css('::text').get()
            old_price = response.css('span.PriceContainer-slashedPrice::text').get()
            if old_price:
                item['products_old_price'] = old_price.replace(' AED', '').replace(',', '')
                item['products_discount'] = \
                    response.css('span.PriceContainer-discountPercent::text').get().replace(' OFF', '').replace('%', '')
            img = response.css('img.ImageGallery-thumbnail~link::attr(href)').getall()
            images = ['https:' + i.replace('small_light(dw=81,ch=158,cc=fafafa,of=webp)/', '') for i in img]
            item['img_urls'] = images
            res = {
                response.css(f'#content-tab-{i} ::text').get():
                    response.css(f'#content-tab-panel-{i} p::text').getall() for i in range(0, 3)
            }
            delivery = {
                response.css(f'#delivery-details-tab-{i} ::text').get(): {
                    j.css('strong::text').get(): j.css('::text')[1].get() for j in
                    response.css(f'div#delivery-details-tab-panel-{i} li')} for i in range(0, 2)
            }
            res['Delivery'] = delivery
            returns = response.xpath('//div[@class="DeliveryDetails"]/h3[contains(text(), "Return")]')[0]
            res['Returns'] = {returns.css('::text').get(): returns.xpath('following::p/text()').get()}
            product_code = response.css('.Help-selectedSku::text').get()
            item['product_code'] = product_code.split(': ')[-1] if product_code else None
            item['products_detail'] = res
            items = []
            for i in res.values():
                if type(i) == list:
                    items.extend(i)

        else:
            item['products_title'] = response.css('h1.Brief-title::text').get()
            shop_link = response.css('a.Brief-brand::attr(href)').get()
            item['shop_link'] = self.host + shop_link if shop_link else None
            item['shop_name'] = response.css('a.Brief-brand [itemprop="name"]::text').get()
            old_price = response.css('span.Brief-price::text').get()
            if old_price:
                item['products_old_price'] = old_price.replace(' AED', '').replace(',', '')
                item['products_discount'] = \
                    response.css('span.Brief-discount::text').get().replace(' OFF', '').replace('%', '')
            img = response.css('img.swiper-lazy::attr(data-src)').getall()
            h2 = response.css('.TabView-tab::text').getall()
            items = [i.css('p::text').getall() for i in
                     response.xpath('//div[contains(@class, "TabView-contentWrapper")]/div[not(@class)]')]
            res = dict(zip(h2[:3], items[:3]))
            delivery_sections = response.css('.DeliveryAndReturn-content')
            delivery = [{li.css('span::text').get(): li.css('.DeliveryAndReturn-methodAmount::text').get()
                         for li in ul.css('li')} for ul in delivery_sections]
            res['Delivery'] = dict(zip(h2[4:], delivery))
            res['Returns'] = items[-1] if len(items) > 1 else None
            item['products_detail'] = res
            product_code = response.css('div.Share-sku::text')
            item['product_code'] = product_code.getall()[-1] if product_code else None
            images = ['https:' + i for i in img]
            item['img_urls'] = images

        data_product = ProductsModel.parse_obj(item.__dict__['_values'])
        for url in images:
            response_img = request("GET", url)
            img_content = response_img.content
            img_name_context = url.split('/')[-1].split('?')[0]
            name, extension = ('.'.join(x[:-1]), x[-1]) if len(x := img_name_context.split('.')) > 2 else \
                x if len(x) == 2 else (*x, 'jpg')
            img_dict = {
                'content': b64encode(img_content),
                'extension': extension,
                'source_url': url,
                'name': name,
            }
            data_product.images.append(Image.parse_obj(img_dict))
        data_product.features = {k: v for k, v in enumerate(items, 1)}
        data_json = data_product.json(by_alias=True, exclude_none=True)

        # data_json = data_product.json(by_alias=True, exclude_none=True, exclude={'images'})

        if self.redis_cache.cache(item['products_url'], data_json):
            if self.api.send('/Parse/Product', data_product.json(by_alias=True, exclude_none=True)):
                self.redis_cache.set(self.name, item['products_url'], data_json)

        yield item
