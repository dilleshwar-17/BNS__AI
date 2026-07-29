import re


class CitationExtractor:
    def __init__(self):
        self.pattern = re.compile(r"(?i)((?:Section|S\.?|Article|Art\.?)\s*\d+[A-Za-z]?(?:-\d+)?)")

    def extract(self, text: str) -> list[str]:
        return list(set(self.pattern.findall(text)))
