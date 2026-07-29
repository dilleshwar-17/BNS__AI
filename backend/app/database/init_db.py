from app.database.base import Base
from app.database.session import engine
from app.logging import get_logger

logger = get_logger(__name__)


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")
