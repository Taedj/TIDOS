class Repository:
    def __init__(self):
        self._items = {}

    def save(self, code, name, price):
        self._items[code] = {"code": code, "name": name, "price": price}

    def find(self, code):
        return self._items.get(code)

    def all(self):
        return list(self._items.values())
