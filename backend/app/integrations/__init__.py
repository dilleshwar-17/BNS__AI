from app.integrations.chroma import ChromaIntegration
from app.integrations.email import EmailIntegration
from app.integrations.neo4j import Neo4jIntegration
from app.integrations.ollama import close_http_clients, get_chroma_http_client, get_gemini_client, get_ollama_client
from app.integrations.redis import RedisIntegration
