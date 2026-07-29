import hashlib


class EmbeddingCache:
    def __init__(self):
        self._cache: dict[str, list[float]] = {}

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> list[float] | None:
        return self._cache.get(self._key(text))

    def set(self, text: str, embedding: list[float]):
        self._cache[self._key(text)] = embedding

    def clear(self):
        self._cache.clear()
