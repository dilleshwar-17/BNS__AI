class CitationFormatter:
    def format(self, text: str) -> str:
        import re

        text = re.sub(r"(?i)(bns|bnss|bsa)\s+(\d+)", r"**\1 Section \2**", text)
        return text
