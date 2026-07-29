from typing import Any

from app.ai.agents.base_agent import BaseAgent
from app.ai.orchestrator.workflow_router import Message
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class KnowledgeGraphAgent(BaseAgent):
    def __init__(self):
        super().__init__("kg_agent", "Self-growing knowledge graph that learns new connections")
        self.subscribe_to("graph_query")
        self.subscribe_to("graph_learn")
        self.subscribe_to("graph_stats")
        self.driver = None

    async def _get_driver(self):
        from neo4j import AsyncGraphDatabase

        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
        return self.driver

    async def process(self, message: Message) -> Any:
        msg_type = message.type
        payload = message.payload

        if msg_type == "graph_query":
            return await self.query_graph(payload)
        elif msg_type == "graph_learn":
            return await self.learn_connection(payload)
        elif msg_type == "graph_stats":
            return await self.get_stats()
        return {"error": "Unknown message type"}

    async def query_graph(self, payload: dict) -> dict:
        query = payload.get("query", "")
        query_type = payload.get("type", "")
        sections = payload.get("sections", [])
        driver = await self._get_driver()

        results = []
        async with driver.session(database="neo4j") as session:
            if sections:
                cypher = """
                    MATCH (s:Section)
                    WHERE s.number IN $sections
                    OPTIONAL MATCH (q:Query)-[:REFERENCES_SECTION]->(s)
                    RETURN s.number AS section, collect(DISTINCT q.text) AS queries
                    LIMIT 10
                """
                result = await session.run(cypher, sections=[str(s) for s in sections[:5]])
                records = await result.fetch(5)
                for record in records:
                    results.append(
                        {
                            "type": "section",
                            "section": record.get("section"),
                            "related_queries": record.get("queries", [])[:3],
                        }
                    )

            if query_type:
                type_cypher = """
                    MATCH (q:Query {type: $type})
                    OPTIONAL MATCH (q)-[:REFERENCES_SECTION]->(s:Section)
                    OPTIONAL MATCH (q)-[:TAGGED_WITH]->(k:Keyword)
                    RETURN q.text AS text, q.type AS type,
                           collect(DISTINCT s.number) AS sections,
                           collect(DISTINCT k.word) AS keywords
                    LIMIT 8
                """
                result = await session.run(type_cypher, type=query_type)
                records = await result.fetch(8)
                for record in records:
                    results.append(
                        {
                            "type": "query",
                            "text": record.get("text", ""),
                            "query_type": record.get("type"),
                            "sections": record.get("sections", []),
                            "keywords": record.get("keywords", [])[:5],
                        }
                    )

            if query:
                search_cypher = """
                    MATCH (q:Query)
                    WHERE toLower(q.text) CONTAINS toLower($q_text)
                    RETURN q.text AS text, q.type AS type, q.difficulty AS diff
                    LIMIT 5
                """
                result = await session.run(search_cypher, {"q_text": query[:60]})
                records = await result.fetch(5)
                for record in records:
                    results.append(
                        {
                            "type": "match",
                            "text": record.get("text", ""),
                            "query_type": record.get("type"),
                            "difficulty": record.get("diff"),
                        }
                    )

        return {
            "query": query,
            "type": query_type,
            "results": results,
            "total": len(results),
        }

    async def learn_connection(self, payload: dict) -> dict:
        source = payload.get("source", "")
        target = payload.get("target", "")
        rel_type = payload.get("relation", "RELATED_TO")
        properties = payload.get("properties", {})

        if not source or not target:
            return {"learned": False, "error": "source and target required"}

        driver = await self._get_driver()
        async with driver.session(database="neo4j") as session:
            cypher = f"""
                MERGE (a:LearnedConcept {{name: $source}})
                MERGE (b:LearnedConcept {{name: $target}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.weight = CASE WHEN r.weight IS NULL THEN 1 ELSE r.weight + 1 END
                SET r.last_learned = timestamp()
                RETURN r.weight AS weight
            """
            result = await session.run(cypher, source=source, target=target)
            record = await result.single()

        self.long_term.learn_connection(source, target, rel_type)
        self.log("learned", source=source, target=target, relation=rel_type)

        return {
            "learned": True,
            "source": source,
            "target": target,
            "relation": rel_type,
            "weight": record["weight"] if record else 1,
        }

    async def get_stats(self) -> dict:
        driver = await self._get_driver()
        async with driver.session(database="neo4j") as session:
            node_result = await session.run("MATCH (n) RETURN count(n) AS count, labels(n) AS labels LIMIT 50")
            nodes = await node_result.fetch(50)
            rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count, type(r) AS type LIMIT 50")
            rels = await rel_result.fetch(50)

        node_labels = {}
        for n in nodes:
            for label in n.get("labels") or []:
                node_labels[label] = node_labels.get(label, 0) + 1

        rel_types = {}
        for r in rels:
            rt = r.get("type")
            if rt:
                rel_types[rt] = rel_types.get(rt, 0) + 1

        return {
            "total_nodes": sum(node_labels.values()),
            "node_labels": node_labels,
            "total_relationships": sum(rel_types.values()),
            "relationship_types": rel_types,
        }

    async def close(self):
        if self.driver:
            await self.driver.close()
            self.driver = None


kg_agent = KnowledgeGraphAgent()
