# Document Ingestion

## Pipeline
1. Upload document (PDF, DOCX, TXT)
2. Extract text
3. OCR if needed
4. Clean & normalize
5. Detect sections & citations
6. Chunk text
7. Generate embeddings
8. Store in ChromaDB
9. Update Neo4j knowledge graph

## CLI
```bash
python scripts/ingest_acts.py
python scripts/build_embeddings.py
```
