import asyncio

from app.logging import get_logger

logger = get_logger(__name__)


async def main():
    logger.info("building_embeddings")
    from app.ingestion.chroma.vector_store import initialize_vector_store

    await initialize_vector_store()
    logger.info("embeddings_built")


if __name__ == "__main__":
    asyncio.run(main())
