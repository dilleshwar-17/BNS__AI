from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.settings import get_settings

settings = get_settings()

if "sqlite" in settings.database_url:
    engine = create_async_engine(
        settings.database_url, echo=False, poolclass=NullPool, connect_args={"check_same_thread": False}
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_pre_ping=settings.pool_pre_ping,
        pool_recycle=3600,
    )

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"
