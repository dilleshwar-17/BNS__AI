from app.graph.neo4j import _get_driver
from app.logging import get_logger

logger = get_logger(__name__)


class Neo4jIntegration:
    async def heartbeat(self) -> bool:
        try:
            driver = await _get_driver()
            async with driver.session(database="neo4j") as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False

    async def node_count(self) -> int:
        try:
            driver = await _get_driver()
            async with driver.session(database="neo4j") as session:
                result = await session.run("MATCH (n) RETURN count(n) AS c")
                record = await result.single()
                return record["c"] if record else 0
        except Exception:
            return 0
