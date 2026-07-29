from app.logging import get_logger

logger = get_logger(__name__)


class DOCXProcessor:
    async def extract_text(self, path: str) -> str:
        try:
            from docx import Document

            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not available")
            return ""
