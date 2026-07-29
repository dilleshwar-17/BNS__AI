# Deployment

## Prerequisites
- Docker & Docker Compose
- NVIDIA GPU (optional, for local LLM)

## Quick Start
```bash
docker-compose up -d
```

## Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Environment Variables
See `.env.example` for all configuration options.
