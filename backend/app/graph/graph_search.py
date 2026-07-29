from app.graph.neo4j import _get_driver
from app.logging import get_logger

logger = get_logger(__name__)


class GraphSearch:
    async def search(self, query: str, limit: int = 5) -> list[dict]:
        driver = await _get_driver()
        results = []
        async with driver.session(database="neo4j") as session:
            cypher = """
                MATCH (n)
                WHERE toLower(n.text) CONTAINS toLower($query)
                   OR toLower(n.title) CONTAINS toLower($query)
                RETURN n, labels(n) AS labels
                LIMIT $limit
            """
            result = await session.run(cypher, query=query, limit=limit)
            async for record in result:
                results.append(
                    {
                        "text": record.get("n", {}).get("text", ""),
                        "labels": record.get("labels", []),
                    }
                )
        return results

    async def get_related(self, node_id: str, rel_type: str | None = None) -> list[dict]:
        driver = await _get_driver()
        async with driver.session(database="neo4j") as session:
            rel_filter = f":{rel_type}" if rel_type else ""
            cypher = f"""
                MATCH (a {{id: $id}})-[r{rel_filter}]->(b)
                RETURN b, type(r) AS rel_type
                LIMIT 20
            """
            result = await session.run(cypher, id=node_id)
            related = []
            async for record in result:
                related.append({"node": record.get("b", {}), "relation": record.get("rel_type", "")})
            return related
