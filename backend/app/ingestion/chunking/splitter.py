class TextSplitter:
    def split_by_sections(self, text: str) -> list[dict]:
        import re

        sections = re.split(r"(CHAPTER\s+\d+|Section\s+\d+)", text)
        chunks = []
        for i in range(1, len(sections), 2):
            chunks.append(
                {"section": sections[i].strip(), "content": sections[i + 1].strip() if i + 1 < len(sections) else ""}
            )
        return chunks
