from app.logging import get_logger

logger = get_logger(__name__)


class HTMLLoader:
    async def load(self, path: str) -> str:
        try:
            from bs4 import BeautifulSoup

            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
                return soup.get_text(separator="\n")
        except ImportError:
            logger.warning("beautifulsoup4 not installed")
            return ""
