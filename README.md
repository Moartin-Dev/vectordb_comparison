# vectordb_comparison
A vectordb comparison between pgvector and chromaDB for the use case of OpenAPI Spec search.

# WAB Benchmark Stack (FastAPI + pgvector + ChromaDB + Ollama)

## Quickstart

```bash
cp .env.example .env
# Passe Passwörter in ./secrets/ an
docker compose pull
docker compose up -d

# Modelle laden:
docker exec -it ollama bash -lc "ollama pull gte-base"
# Optional: kleines Chat-LLM
docker exec -it ollama bash -lc "ollama pull qwen2.5:0.5b"