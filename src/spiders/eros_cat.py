import scrapy

from src.items import CategoriesItem


class ErosCatSpider(scrapy.Spider):
    name = 'eros_cat'
    allowed_domains = ['www.eros.ae']
    start_urls = [
        'https://www.eros.ae/smart-phones.html',
        'https://www.eros.ae/computers-tablets.html',
        'https://www.eros.ae/wearables.html',
        'https://www.eros.ae/accessories.html',
    ]

    def parse(self, response, **kwargs):
        """Парсинг всех категориев"""
        self.logger.info('Hi, this is an categories page! %s', response.url)
        item = CategoriesItem()
        parent = response.css('a.has-sub-cat.active')
        item['url'] = parent.attrib['href']
        item['name'] = parent.css('::text').get().strip()
        cat: list = response.xpath('//div[@data-role="title" and contains(text(), "Brand")]/..//a')
        cat_2 = response.xpath('//div[@data-role="title" and contains(text(), "Category")]/..//a')
        if cat_2:
            cat.extend(cat_2)
        urls = [url.attrib['href'] for url in cat]
        names = [t.css('span.label::text').get() for t in cat]
        item['categories'] = [{"name": v, "url": urls[k]} for k, v in enumerate(names)]
        yield item
