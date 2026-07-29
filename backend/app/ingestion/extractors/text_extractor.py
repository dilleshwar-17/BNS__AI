import re


class TextExtractor:
    def extract(self, raw: str) -> str:
        text = raw.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()
        return text

    def extract_preserve_structure(self, raw: str) -> str:
        return raw.strip()

    def normalize_whitespace(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def remove_non_legal_chars(self, text: str) -> str:
        allowed = r"[^\w\s\.\,\;\:\-\(\)\[\]\{\}\/\#\'\"\n\u0900-\u097F]"
        return re.sub(allowed, "", text)
