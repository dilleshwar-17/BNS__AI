from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_HAS_TESSERACT = False
try:
    import pytesseract

    _HAS_TESSERACT = True
except ImportError:
    pass


class OCRProcessor:
    def __init__(self, lang: str = "eng"):
        self.lang = lang

    async def process(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            logger.warning("ocr_image_not_found", path=image_path)
            return ""

        ext = path.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"):
            logger.warning("ocr_unsupported_format", ext=ext)
            return ""

        return await self._run_ocr(image_path)

    async def process_batch(self, image_paths: list[str]) -> str:
        texts = []
        for p in image_paths:
            text = await self.process(p)
            if text:
                texts.append(text)
        return "\n\n".join(texts)

    async def _run_ocr(self, image_path: str) -> str:
        if not _HAS_TESSERACT:
            logger.info("ocr_unavailable_pytesseract_not_installed")
            return ""

        try:
            from PIL import Image

            image = Image.open(image_path)
            text = await self._run_tesseract(image)
            return text.strip()
        except Exception as e:
            logger.warning("ocr_failed", path=image_path, error=str(e))
            return ""

    async def _run_tesseract(self, image) -> str:
        try:
            import pytesseract as ts

            return ts.image_to_string(image, lang=self.lang)
        except Exception as e:
            logger.warning("tesseract_call_failed", error=str(e))
            return ""

    @staticmethod
    def is_available() -> bool:
        return _HAS_TESSERACT
