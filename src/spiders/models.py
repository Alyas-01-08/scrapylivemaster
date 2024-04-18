import datetime
import logging
from uuid import uuid4

from playhouse.postgres_ext import *

logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.ERROR)
db = PostgresqlDatabase(
    'root',
    user='root',
    password='pass',
    host='host',
    port='port')


class BaseModel(Model):
    """A base model that will use our Postgresql database"""

    class Meta:
        database = db


class CacheModel(BaseModel):
    """Модель для хранения кэша"""
    id = UUIDField(primary_key=True, default=uuid4)
    key = CharField(max_length=500, null=False)
    categories = CharField(max_length=50, null=False)
    value = JSONField()
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField()

    class Meta:
        table_name = 'cache'

    @classmethod
    def get_or_none(cls, *query, **filters):
        try:
            return cls.get(*query, **filters)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_key(cls, key):
        return cls.get_or_none(cls.key == key)

    @classmethod
    def get_by_categories(cls, categories):
        return cls.get_or_none(cls.categories == categories)

    @classmethod
    def set(cls, categories, key, value):
        cls.create(key=key, value=value, categories=categories, updated_at=datetime.datetime.now())

    @classmethod
    def cache(cls, key, value):
        if data := cls.get_by_key(key):
            if data.value != value:
                return True
            return False
        return True


if __name__ == '__main__':
    CacheModel.create_table()
    # d = CacheModel.get_by_key('test')
