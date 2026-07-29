from math import ceil


class Paginator:
    def __init__(self, total: int, page: int = 1, page_size: int = 20):
        self.total = total
        self.page = max(1, page)
        self.page_size = min(100, max(1, page_size))
        self.total_pages = ceil(total / self.page_size) if total > 0 else 1
        self.offset = (self.page - 1) * self.page_size
        self.has_next = self.page < self.total_pages
        self.has_prev = self.page > 1

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }
