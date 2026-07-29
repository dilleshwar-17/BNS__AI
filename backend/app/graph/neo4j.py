from app.ai.response_modes.local_fallback import OFFLINE_KNOWLEDGE_BASE
from app.core.logging import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

_driver = None


async def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import AsyncGraphDatabase

        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def initialize_knowledge_graph():
    if not settings.neo4j_uri:
        logger.info("knowledge_graph_disabled_no_uri")
        return
    try:
        driver = await _get_driver()
        async with driver.session(database="neo4j") as session:
            # Create indexes and constraints
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:LegalTopic) ON (t.id)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (t:LegalTopic) ON (t.title)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (q:Query) ON (q.id)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (s:Section) ON (s.number)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (c:Chapter) ON (c.name)")
            await session.run("CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.word)")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:LegalTopic) REQUIRE t.id IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (q:Query) REQUIRE q.id IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Section) REQUIRE s.number IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chapter) REQUIRE c.name IS UNIQUE")
            await session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.word IS UNIQUE")
            logger.info("neo4j_indexes_created")

            result = await session.run("MATCH (n:LegalTopic) RETURN count(n) AS count")
            record = await result.single()
            if record and record["count"] > 0:
                logger.info("knowledge_graph_already_populated", count=record["count"])
                return True

            for topic_id, entry in OFFLINE_KNOWLEDGE_BASE.items():
                await session.run(
                    """
                    CREATE (t:LegalTopic {
                        id: $id,
                        title: $title,
                        sections: $sections,
                        description: $description,
                        procedure: $procedure,
                        citation: $citation
                    })
                    """,
                    id=topic_id,
                    title=entry["title"],
                    sections=entry.get("sections", ""),
                    description=entry.get("description", ""),
                    procedure=entry.get("procedure", ""),
                    citation=entry.get("citation", ""),
                )

                if "bail" in entry:
                    await session.run(
                        """
                        MATCH (t:LegalTopic {id: $id})
                        CREATE (b:BailInfo {details: $details})
                        CREATE (t)-[:HAS_BAIL_INFO]->(b)
                        """,
                        id=topic_id,
                        details=entry["bail"],
                    )

                if "rights" in entry:
                    await session.run(
                        """
                        MATCH (t:LegalTopic {id: $id})
                        CREATE (r:Right {description: $details})
                        CREATE (t)-[:CONFERS_RIGHT]->(r)
                        """,
                        id=topic_id,
                        details=entry["rights"],
                    )

            await session.run(
                """
                MATCH (t1:LegalTopic), (t2:LegalTopic)
                WHERE t1.id < t2.id
                CREATE (t1)-[:RELATED_TO]->(t2)
                """
            )
            logger.info("knowledge_graph_populated")
        return True
    except Exception as e:
        logger.warning("knowledge_graph_init_failed", error=str(e))
        return False


async def query_knowledge_graph(query: str) -> str | None:
    try:
        driver = await _get_driver()
        async with driver.session(database="neo4j") as session:
            result = await session.run(
                """
                MATCH (t:LegalTopic)
                WHERE toLower(t.title) CONTAINS toLower($query)
                   OR toLower(t.description) CONTAINS toLower($query)
                   OR toLower(t.sections) CONTAINS toLower($query)
                RETURN t.title AS title, t.description AS description,
                       t.procedure AS procedure, t.citation AS citation,
                       t.sections AS sections
                LIMIT 3
                """,
                query=query,
            )
            records = await result.fetch(3)
            if not records:
                result = await session.run(
                    """
                    MATCH (t:LegalTopic)
                    RETURN t.title AS title, t.description AS description,
                           t.procedure AS procedure, t.citation AS citation,
                           t.sections AS sections
                    LIMIT 3
                    """
                )
                records = await result.fetch(3)

            if not records:
                return None

            parts = []
            for record in records:
                parts.append(
                    f"**{record['title']}**\n"
                    f"{record['description']}\n"
                    f"**Procedure:** {record['procedure']}\n"
                    f"**Citation:** {record['citation']}"
                )
            return "\n\n".join(parts)
    except Exception as e:
        logger.warning("knowledge_graph_query_failed", error=str(e))
        return None


async def close_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
