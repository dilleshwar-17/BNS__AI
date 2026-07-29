from app.logging import get_logger

logger = get_logger(__name__)


class ImageLoader:
    async def load(self, path: str) -> str:
        try:
            import pytesseract
            from PIL import Image

            text = pytesseract.image_to_string(Image.open(path))
            return text
        except ImportError:
            logger.warning("pytesseract not installed")
            return ""
        except Exception as e:
            logger.error("ocr_failed", error=str(e))
            return ""
