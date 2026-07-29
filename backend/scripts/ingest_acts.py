import asyncio

from app.logging import get_logger

logger = get_logger(__name__)


async def main():
    logger.info("starting_act_ingestion")
    from app.ingestion.pipeline import run_ingestion

    results = await run_ingestion()
    logger.info("ingestion_complete", results=results)


if __name__ == "__main__":
    asyncio.run(main())
