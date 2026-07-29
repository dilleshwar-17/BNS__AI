import re


class Helpers:
    @staticmethod
    def slugify(text: str) -> str:
        return re.sub(r"[^\w\s-]", "", text).strip().lower().replace(" ", "-")

    @staticmethod
    def truncate(text: str, max_length: int = 100) -> str:
        return text[:max_length] + "..." if len(text) > max_length else text

    @staticmethod
    def safe_int(value, default: int = 0) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
