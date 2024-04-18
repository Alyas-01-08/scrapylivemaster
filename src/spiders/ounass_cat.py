from pprint import pprint

import scrapy


class OunassCatSpider(scrapy.Spider):
    name = 'ounass_cat'
    host = 'https://www.ounass.ae'
    allowed_domains = ['www.ounass.ae']
    start_urls = [
        'https://www.ounass.ae/women/designers',
        'https://www.ounass.ae/men/designers',
        'https://www.ounass.ae/kids/designers'
    ]

    def parse(self, response, **kwargs):
        """Парсинг всех категориев"""
        self.logger.info('Hi, this is an categories page! %s', response.url)
        parent = response.css('a.SiteNavigation-l1Link.is-selected')
        result = self.detail_cat(parent)
        result["categories"] = [self.detail_cat(i) for i in response.css('a.L2Category')]
        pprint(result)
        yield result

    def detail_cat(self, selector):
        return {
            "name": selector.css(' ::text').get(),
            "url": self.host + selector.attrib['href'],

        }
