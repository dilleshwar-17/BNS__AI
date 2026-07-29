from app.graph.neo4j import _get_driver
from app.logging import get_logger

logger = get_logger(__name__)


class GraphBuilder:
    async def build_from_text(self, text: str, source: str = ""):
        driver = await _get_driver()
        async with driver.session(database="neo4j") as session:
            await session.run(
                "MERGE (d:Document {source: $source}) SET d.text = $text",
                source=source,
                text=text[:1000],
            )
            logger.info("graph_node_created", source=source)

    async def create_relationship(self, source_id: str, target_id: str, rel_type: str):
        driver = await _get_driver()
        async with driver.session(database="neo4j") as session:
            cypher = f"""
                MATCH (a {{id: $source_id}})
                MATCH (b {{id: $target_id}})
                MERGE (a)-[:{rel_type}]->(b)
            """
            await session.run(cypher, source_id=source_id, target_id=target_id)

    async def get_stats(self) -> dict:
        driver = await _get_driver()
        async with driver.session(database="neo4j") as session:
            result = await session.run("MATCH (n) RETURN count(n) AS count, labels(n) AS labels LIMIT 1")
            record = await result.single()
            return {"nodes": record["count"] if record else 0}
