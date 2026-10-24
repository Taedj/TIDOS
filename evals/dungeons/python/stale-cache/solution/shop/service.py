from .cache import Cache
from .repository import Repository


def _normalize(code):
    return code.strip().upper()


class ProductService:
    def __init__(self, repo=None, cache=None):
        self.repo = repo or Repository()
        self.cache = cache or Cache()

    def add_product(self, code, name, price):
        key = _normalize(code)
        self.repo.save(key, name, price)
        self.cache.delete(key)

    def get_product(self, code):
        key = _normalize(code)
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        item = self.repo.find(key)
        if item is not None:
            self.cache.set(key, item)
        return item

    def update_price(self, code, price):
        key = _normalize(code)
        item = self.repo.find(key)
        if item is None:
            raise KeyError(code)
        self.repo.save(key, item["name"], price)
        self.cache.delete(key)

    def list_products(self):
        return sorted(self.repo.all(), key=lambda p: p["code"])
