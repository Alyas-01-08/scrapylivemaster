import json
from pprint import pprint

import scrapy


class BloomingCatSpider(scrapy.Spider):
    name = 'blooming_cat'
    host = 'http://bloomingdales.ae'
    allowed_domains = ['bloomingdales.ae']
    start_urls = ['http://bloomingdales.ae/']

    def parse(self, response, **kwargs):
        """Парсинг всех категориев"""
        self.logger.info('Hi, this is an categories page! %s', response.url)
        parents = response.css('ul.js-main-nav-list[role] a.b-menu__nav-link')
        result = []
        for m in parents:
            cat = self.main_cat(m)
            mid_cat_selectors = m.xpath('..//li[contains(@class,"b-menu__nav-item--level-2")]')
            for s in mid_cat_selectors:
                mid_cat = self.sub_cat(s)
                mid_cat["categories"] = \
                    [self.sub_cat(j) for j in s.xpath('..//li[contains(@class,"b-menu__nav-item--level-3")]')]
                cat["categories"].append(mid_cat)
            result.append(cat)
        pprint(result)
        with open("blooming_cat.json", "w") as write_file:
            json.dump(result, write_file)

    def main_cat(self, selector):
        return {
            "name": selector.css('::text').get().strip(),
            "url": self.host + selector.attrib['href'],
            "categories": []
        }

    def sub_cat(self, selector):
        return {
            "name": selector.css('a.b-menu__nav-item-link .b-menu__nav-item-link-text::text').get(),
            "url": selector.css('a.b-menu__nav-item-link').attrib['href']
        }
