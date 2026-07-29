class MetadataExtractor:
    def extract(self, text: str, source: str = "") -> dict:
        return {"source": source, "char_count": len(text), "word_count": len(text.split()), "language": "en"}
