class DocumentParser:
    def parse(self, content: str, doc_type: str) -> dict:
        return {"content": content, "type": doc_type, "sections": self._extract_sections(content)}

    def _extract_sections(self, content: str) -> list[dict]:
        sections = []
        current = {"title": "", "content": []}
        for line in content.split("\n"):
            line = line.strip()
            if line.isupper() and len(line) > 3:
                if current["title"]:
                    sections.append(current)
                current = {"title": line, "content": []}
            else:
                current["content"].append(line)
        if current["title"]:
            sections.append(current)
        return sections
