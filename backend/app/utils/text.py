import re


class TextUtils:
    @staticmethod
    def clean(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def extract_sections(text: str) -> list[str]:
        return re.findall(r"(?i)section\s+(\d+[A-Za-z]?(?:-\d+)?)", text)

    @staticmethod
    def word_count(text: str) -> int:
        return len(text.split())
