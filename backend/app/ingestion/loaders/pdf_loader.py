from app.logging import get_logger

logger = get_logger(__name__)


class PDFLoader:
    async def load(self, path: str) -> str:
        try:
            import PyPDF2

            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("PyPDF2 not installed")
            return ""
        except Exception as e:
            logger.error("pdf_load_failed", error=str(e))
            return ""
