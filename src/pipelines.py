# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class DuplicatesPipeline:
    def __init__(self):
        self.author_ids_seen = set()

    def process_item(self, item, spider):
        if item['products_url'] in self.author_ids_seen:
            raise DropItem("Duplicate item found: %s" % item)
        else:
            self.author_ids_seen.add(item['products_url'])
            return item
