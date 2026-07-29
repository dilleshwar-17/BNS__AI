from app.ingestion.chroma.client import get_chroma_client
from app.logging import get_logger

logger = get_logger(__name__)


class ChromaIntegration:
    def __init__(self):
        self.client = get_chroma_client()

    def heartbeat(self) -> bool:
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False

    def count(self, collection: str) -> int:
        try:
            col = self.client.get_collection(collection)
            return col.count()
        except Exception:
            return 0
