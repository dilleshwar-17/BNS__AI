import hashlib
import re

from app.core.logging import get_logger

logger = get_logger(__name__)


def _make_chunk_id(prefix: str, index: int, source: str = "") -> str:
    raw = f"{prefix}_{index}_{source}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class FixedSizeChunker:
    def chunk(self, text: str, chunk_size: int = 500, overlap: int = 50, source: str = "") -> list[dict]:
        chunks = []
        start = 0
        text_len = len(text)
        index = 0

        while start < text_len:
            end = min(start + chunk_size, text_len)
            if end < text_len:
                next_space = text.rfind(" ", start + chunk_size - 50, end)
                if next_space > start:
                    end = next_space + 1

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    {
                        "id": _make_chunk_id("fixed", index, source),
                        "text": chunk_text,
                        "metadata": {
                            "chunk_index": index,
                            "chunk_size": len(chunk_text),
                            "strategy": "fixed",
                        },
                    }
                )
                index += 1

            start = end - overlap if end < text_len else text_len

        return chunks


class RecursiveChunker:
    def __init__(self, max_chunk_size: int = 800, min_chunk_size: int = 100):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, source: str = "") -> list[dict]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks = []
        current = []
        current_len = 0
        index = 0

        for para in paragraphs:
            para_len = len(para)
            if para_len > self.max_chunk_size:
                if current:
                    chunk_text = "\n\n".join(current)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(self._make_chunk(chunk_text, index, source, "recursive"))
                        index += 1
                    current = []
                    current_len = 0

                sub_chunks = self._split_long_paragraph(para, source, index)
                chunks.extend(sub_chunks)
                index += len(sub_chunks)
                continue

            if current_len + para_len > self.max_chunk_size and current:
                chunk_text = "\n\n".join(current)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(self._make_chunk(chunk_text, index, source, "recursive"))
                    index += 1
                current = [para]
                current_len = para_len
            else:
                current.append(para)
                current_len += para_len

        if current:
            chunk_text = "\n\n".join(current)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(self._make_chunk(chunk_text, index, source, "recursive"))

        return chunks

    def _split_long_paragraph(self, para: str, source: str, base_index: int) -> list[dict]:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        chunks = []
        current = []
        current_len = 0
        idx = 0

        for sent in sentences:
            if current_len + len(sent) > self.max_chunk_size and current:
                chunk_text = " ".join(current)
                chunks.append(self._make_chunk(chunk_text, base_index + idx, source, "recursive_sentence"))
                idx += 1
                current = [sent]
                current_len = len(sent)
            else:
                current.append(sent)
                current_len += len(sent)

        if current:
            chunk_text = " ".join(current)
            chunks.append(self._make_chunk(chunk_text, base_index + idx, source, "recursive_sentence"))

        return chunks

    def _make_chunk(self, text: str, index: int, source: str, strategy: str) -> dict:
        return {
            "id": _make_chunk_id("rec", index, source),
            "text": text,
            "metadata": {
                "chunk_index": index,
                "chunk_size": len(text),
                "strategy": strategy,
            },
        }


class SectionChunker:
    SECTION_PATTERNS = [
        re.compile(r"^(CHAPTER\s+[A-Z0-9][A-Z\s\-]+)$", re.MULTILINE),
        re.compile(r"^(Section\s+\d+[A-Z]?\.)", re.MULTILINE),
        re.compile(r"^(PART\s+[A-Z0-9][A-Z\s\-]+)$", re.MULTILINE),
        re.compile(r"^(SCHEDULE\s+[A-Z0-9])", re.MULTILINE),
    ]

    def chunk(self, text: str, source: str = "") -> list[dict]:
        lines = text.split("\n")
        chunks = []
        current_section = "Preamble"
        current_lines = []
        index = 0

        for line in lines:
            stripped = line.strip()
            section_header = self._detect_section_header(stripped)
            if section_header:
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(
                            {
                                "id": _make_chunk_id("sec", index, source),
                                "text": chunk_text,
                                "metadata": {
                                    "chunk_index": index,
                                    "chunk_size": len(chunk_text),
                                    "section": current_section,
                                    "strategy": "section",
                                },
                            }
                        )
                        index += 1
                current_section = section_header
                current_lines = [stripped]
            else:
                if stripped:
                    current_lines.append(line)

        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(
                    {
                        "id": _make_chunk_id("sec", index, source),
                        "text": chunk_text,
                        "metadata": {
                            "chunk_index": index,
                            "chunk_size": len(chunk_text),
                            "section": current_section,
                            "strategy": "section",
                        },
                    }
                )

        return chunks

    def _detect_section_header(self, line: str) -> str | None:
        for pattern in self.SECTION_PATTERNS:
            m = pattern.match(line)
            if m:
                return m.group(1).strip()
        return None


class Chunker:
    def __init__(self, strategy: str = "fixed"):
        self.strategy = strategy
        self.fixed_chunker = FixedSizeChunker()
        self.recursive_chunker = RecursiveChunker()
        self.section_chunker = SectionChunker()

    def chunk(self, text: str, chunk_size: int = 500, overlap: int = 50, source: str = "") -> list[dict]:
        if self.strategy == "recursive":
            return self.recursive_chunker.chunk(text, source=source)
        elif self.strategy == "section":
            return self.section_chunker.chunk(text, source=source)
        else:
            return self.fixed_chunker.chunk(text, chunk_size=chunk_size, overlap=overlap, source=source)
