from pathlib import Path

from app.core.logging import get_logger
from app.ingestion.extractors.ocr import OCRProcessor
from app.ingestion.extractors.text_extractor import TextExtractor

logger = get_logger(__name__)


class DocumentParser:
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.ocr = OCRProcessor()

    async def parse(self, file_path: str, mime_type: str | None = None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()
        mt = (mime_type or "").lower()

        if ext == ".pdf" or "pdf" in mt:
            return await self._parse_pdf(file_path)
        elif ext in (".docx", ".doc") or "word" in mt:
            return self._parse_docx(file_path)
        elif ext == ".txt" or "text" in mt:
            return self._parse_txt(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp") or "image" in mt:
            return await self._parse_image(file_path)
        else:
            logger.warning("unsupported_file_type", ext=ext, mime=mime_type)
            return ""

    async def _parse_pdf(self, file_path: str) -> str:
        text = ""
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                pages = []
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    pages.append(t)
                text = "\n\n".join(pages)
            if text.strip():
                logger.info("pdf_extracted_with_pdfplumber", pages=len(pages), chars=len(text))
                return self.text_extractor.extract(text)
        except ImportError:
            logger.info("pdfplumber_not_available_falling_back_to_pypdf2")
        except Exception as e:
            logger.warning("pdfplumber_extraction_failed", error=str(e))

        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            pages = []
            for page in reader.pages:
                t = page.extract_text() or ""
                pages.append(t)
            text = "\n\n".join(pages)
            logger.info("pdf_extracted_with_pypdf2", pages=len(pages), chars=len(text))
            return self.text_extractor.extract(text)
        except Exception as e:
            logger.warning("pypdf2_extraction_failed", error=str(e))

        try:
            import subprocess

            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.info("pdf_extracted_with_pdftotext", chars=len(result.stdout))
                return self.text_extractor.extract(result.stdout)
        except Exception:
            pass

        logger.warning("pdf_extraction_all_methods_failed", path=file_path)
        return ""

    def _parse_docx(self, file_path: str) -> str:
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)
            logger.info("docx_extracted", paragraphs=len(paragraphs), chars=len(text))
            return self.text_extractor.extract(text)
        except Exception as e:
            logger.warning("docx_extraction_failed", error=str(e))
            return ""

    def _parse_txt(self, file_path: str) -> str:
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                text = Path(file_path).read_text(encoding=encoding)
                logger.info("txt_extracted", encoding=encoding, chars=len(text))
                return self.text_extractor.extract(text)
            except UnicodeDecodeError:
                continue
        logger.warning("txt_extraction_failed_all_encodings", path=file_path)
        return Path(file_path).read_text(encoding="latin-1", errors="replace")

    async def _parse_image(self, file_path: str) -> str:
        text = await self.ocr.process(file_path)
        if text:
            logger.info("image_ocr_extracted", chars=len(text))
            return self.text_extractor.extract(text)
        logger.warning("image_ocr_returned_empty", path=file_path)
        return ""

    @staticmethod
    def supported_extensions() -> list[str]:
        return [".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
