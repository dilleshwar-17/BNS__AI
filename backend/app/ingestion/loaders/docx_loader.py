from app.logging import get_logger

logger = get_logger(__name__)


class DOCXLoader:
    async def load(self, path: str) -> str:
        try:
            from docx import Document

            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            logger.warning("python-docx not installed")
            return ""
        except Exception as e:
            logger.error("docx_load_failed", error=str(e))
            return ""
