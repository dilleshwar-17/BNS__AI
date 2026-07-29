import time


class SessionMemory:
    def __init__(self, ttl: int = 3600):
        self._data: dict[str, tuple] = {}
        self._ttl = ttl

    def get(self, key: str):
        if key in self._data:
            value, expiry = self._data[key]
            if time.time() < expiry:
                return value
            del self._data[key]
        return None

    def set(self, key: str, value):
        self._data[key] = (value, time.time() + self._ttl)

    def clear(self):
        self._data.clear()
