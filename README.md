# BNS AI

AI-Native Legal Intelligence Platform for the Indian Judicial Ecosystem.

## Features

- **Legal Chat** - Natural language interaction with Indian legal knowledge
- **Legal Drafting** - Generate FIR, bail applications, legal notices, and more
- **Offline First** - Built-in knowledge base works without internet
- **Multi-LLM** - Ollama (local) -> Gemini (cloud) -> Offline KB fallback
- **Knowledge Graph** - Neo4j-powered legal relationships
- **Vector Search** - ChromaDB for semantic retrieval
- **Secure** - JWT auth, rate limiting, audit logging

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start with Docker
docker-compose up -d

# Or run locally (Python 3.12+ required)
pip install -e ".[dev]"
cd backend && uvicorn app.main:app --reload --port 8000
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Vanilla JS, CSS3, HTML5
- **AI**: Ollama (Mistral), Google Gemini
- **Storage**: PostgreSQL, Redis, ChromaDB, Neo4j
- **Infrastructure**: Docker, Nginx

## License

MIT
# BNS_AI_
