from app.logging import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    async def extract_text(self, path: str) -> str:
        try:
            import PyPDF2

            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            logger.warning("PyPDF2 not available")
            return ""
