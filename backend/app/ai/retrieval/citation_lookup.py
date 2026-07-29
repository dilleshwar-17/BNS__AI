import re


class CitationLookup:
    def __init__(self):
        self.pattern = re.compile(r"(?i)((?:AIR|SCC|SCR|BLR|ALT|MLJ|CriLJ)\s+\d{4}\s+\w+\s+\d+)|([\w\s]+v\.\s+[\w\s]+)")

    def extract(self, text: str) -> list[str]:
        return list(set(m.group(0).strip() for m in self.pattern.finditer(text)))

    async def lookup(self, citation: str) -> dict:
        return {"citation": citation, "status": "referenced", "verified": False}
