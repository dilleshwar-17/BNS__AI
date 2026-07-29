from app.ingestion.chroma.client import get_chroma_client
from app.logging import get_logger

logger = get_logger(__name__)


class CollectionManager:
    def __init__(self):
        self.client = get_chroma_client()

    def get_or_create(self, name: str):
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(name)

    def list_collections(self) -> list[str]:
        return [c.name for c in self.client.list_collections()]

    def delete(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception as e:
            logger.warning("collection_delete_failed", name=name, error=str(e))
