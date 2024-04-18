from loguru import logger
import requests
import json

from redis import Redis

logger.add("logs/file_{time}.log", level='ERROR')


class MetaSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(MetaSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ApiRequests:
    def __init__(self, url: str, method: str, headers: dict = None):
        self.url = url
        self.method = method
        self.headers = headers if headers else {'Content-Type': 'application/json', 'accept': 'text/plain'}

    def send(self, url: str, json_data: json):
        response = requests.request(self.method, self.url + url, data=json_data, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        if data.get('hasErrors', False):
            logger.error('Ошибка отправки данных\n\n{errors}', errors=data.get('errors', {}))
            return False
        else:
            return True


class RedisCache(metaclass=MetaSingleton):
    """
    Кеширование данных
    """
    connection = None

    def __init__(self, host: str, password: str = None, port: int = 6379):
        self.host = host
        self.password = password
        self.port = port

    def connect(self, db: int = 0):
        if self.connection is None:
            self.connection = Redis(host=self.host, port=self.port, db=db, password=self.password)
        return self.connection

    def cache(self, name, key: str, data: json):
        name_key = f'{name}:{key}'
        if self.connection is None:
            self.connect()
        if response := self.connection.get(name_key):
            if response.decode('utf-8') == data:
                return False
            else:
                return True
        return True

    def set(self, name, key: str, data):
        name_key = f'{name}:{key}'
        if self.connection is None:
            self.connect()
        self.connection.set(name_key, data)
