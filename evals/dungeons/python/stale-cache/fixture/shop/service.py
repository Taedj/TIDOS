from .cache import Cache
from .repository import Repository


class ProductService:
    def __init__(self, repo=None, cache=None):
        self.repo = repo or Repository()
        self.cache = cache or Cache()

    def add_product(self, code, name, price):
        self.repo.save(code, name, price)

    def get_product(self, code):
        key = code.strip()
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        item = self.repo.find(code)
        if item is not None:
            self.cache.set(key, item)
        return item

    def update_price(self, code, price):
        item = self.repo.find(code)
        if item is None:
            raise KeyError(code)
        self.repo.save(code, item["name"], price)
        self.cache.delete(code)

    def list_products(self):
        return sorted(self.repo.all(), key=lambda p: p["code"])
