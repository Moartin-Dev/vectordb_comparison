# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a vector database comparison benchmark for OpenAPI spec search, comparing pgvector and ChromaDB performance. The system uses a FastAPI backend with Ollama for embeddings, running entirely in Docker containers.

## Architecture

### Service Stack
- **pgvector**: PostgreSQL with vector extension, using **HNSW indexing** for L2 distance queries
- **ChromaDB**: Vector database with HTTP API (also uses **HNSW indexing** by default)
- **Ollama**: Local embedding model server (default: all-minilm:l6-v2 model, 384 dimensions)
- **FastAPI**: REST API exposing ingest and query endpoints
- **pgAdmin**: Database management interface

All services communicate on a shared Docker network (`benchnet`) and use Docker secrets for password management.

**Index Algorithm Choice:** Both databases use **HNSW (Hierarchical Navigable Small World)** indexing with matched parameters for a **fair scientific comparison**. HNSW is a graph-based algorithm that provides excellent recall and query performance. Using the same index type ensures we're comparing database implementations, not different indexing algorithms.

### Data Flow
1. **Ingest**: OpenAPI spec → YAML parsing → text extraction → chunking → Ollama embedding → storage in pg/chroma/both
2. **Query**: Query text → Ollama embedding → parallel search in pgvector + ChromaDB → results with latency metrics

### Key Components

**app/main.py**: FastAPI application with lifespan management that waits for all services to be ready before initializing schemas and collections.

**app/routers.py**: API endpoints
- `POST /ingest`: Accepts OpenAPI specs (text or URL), extracts content, chunks, embeds, and stores in selected backend(s)
- `POST /query`: Performs vector similarity search against both databases and returns results with timing metrics
- `POST /embed`: Test endpoint for single text embedding
- `GET /health`: Health check

**app/db_pg.py**: PostgreSQL/pgvector interface
- Creates `documents` table with vector column
- Uses **HNSW index** with L2 distance operator (`<->`)
- HNSW parameters: `m=16` (max connections), `ef_construction=100` (build quality)
- Query-time parameter: `ef_search=100` (search quality)
- Converts L2 distance to cosine similarity approximation: `1.0 - (d*d)/2.0`
- All embeddings are L2-normalized before storage

**app/chroma_client.py**: ChromaDB interface
- Manages singleton client and collection
- Uses ChromaDB v2 HTTP client API
- Stores chunks with metadata (source, chunk index)

**app/embeddings.py**: Ollama integration
- Calls Ollama API for text embeddings
- L2-normalizes all vectors before returning
- Sequential processing (one text at a time)

**app/utils.py**: Core utilities
- `extract_text_from_openapi()`: Parses YAML OpenAPI specs, extracts title, description, paths, operations, summaries
- `chunk_text()`: Sliding window chunking with configurable size and overlap
- `vector_literal()`: Formats float arrays for PostgreSQL vector literals
- `l2_normalize()`: Normalizes vectors to unit length

**app/waiters.py**: Service readiness checks that poll HTTP endpoints and PostgreSQL until they respond correctly, with configurable timeouts and intervals.

**app/config.py**: Centralized configuration from environment variables.

## Development Commands

### Starting the Stack
```bash
# Copy environment template and configure
cp .env.example .env  # Note: no .env.example exists yet, check .env directly

# Adjust passwords in ./secrets/postgres_password.txt and ./secrets/pgadmin_password.txt

# Start all services
docker compose up -d

# Load the embedding model (required before ingesting)
docker exec ollama ollama pull all-minilm:l6-v2

# Optional: Load a small chat LLM
docker exec ollama ollama pull qwen2.5:0.5b
```

### Viewing Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f pgvector
docker compose logs -f chroma
docker compose logs -f ollama
```

### Rebuilding the API
```bash
# Rebuild and restart just the API service
docker compose build api
docker compose up -d api
```

### Database Access
```bash
# Direct PostgreSQL access
docker exec -it pgvector psql -U postgres -d postgres

# pgAdmin available at configured PGADMIN_HOST_IP:PGADMIN_HOST_PORT
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Test embedding
curl -X POST http://localhost:8000/embed -H "Content-Type: application/json" -d '{"text": "test"}'

# Ingest example
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test-api",
    "text": "openapi: 3.0.0\ninfo:\n  title: Test API\n  description: A test API",
    "backend": "both"
  }'

# Query example
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "test query", "k": 5}'
```

### Stopping and Cleanup
```bash
# Stop all services
docker compose down

# Stop and remove volumes (deletes all data)
docker compose down -v
```

## Configuration

Environment variables are read from `.env` file. Key settings:

- **Embedding**: `EMBEDDING_MODEL` (default: all-minilm:l6-v2), `EMBED_DIM` (default: 384)
- **Chunking**: `CHUNK_SIZE` (default: 1200), `CHUNK_OVERLAP` (default: 150)
- **pgvector HNSW**:
  - `PG_HNSW_M` (default: 16) - max connections per layer, matched to ChromaDB's `max_neighbors`
  - `PG_HNSW_EF_CONSTRUCTION` (default: 100) - index build quality, matched to ChromaDB's `ef_construction`
  - `PG_HNSW_EF_SEARCH` (default: 100) - query search quality, matched to ChromaDB's `ef_search`
- **Service URLs**: Auto-configured for Docker network, expose ports configured via `*_HOST_IP` and `*_HOST_PORT`
- **Wait timeouts**: `*_WAIT_MAX_SECONDS` and `*_WAIT_INTERVAL_SECONDS` for each service

Passwords are stored in `./secrets/` directory as plain text files (excluded from git).

## Important Implementation Details

### Vector Normalization
All embeddings are L2-normalized before storage. This allows approximate cosine similarity calculation from L2 distance without storing raw vectors separately.

### Score Conversion
- **pgvector**: Returns L2 distance, converted to similarity via `1.0 - (d*d)/2.0`
- **ChromaDB**: Returns L2 distance by default, converted to similarity via `1.0 - distance`

### Chunking Strategy
Uses sliding window with overlap to avoid splitting semantic units. Default 1200 chars with 150 char overlap provides context continuity.

### Service Startup Order
The FastAPI app's lifespan handler explicitly waits for all dependencies (ChromaDB, Ollama, PostgreSQL) to be healthy before initializing schemas/collections. This prevents race conditions during `docker compose up`.

### Schema Initialization
- **pgvector**: Creates extension, table, and HNSW index if they don't exist (idempotent)
- **ChromaDB**: Uses `get_or_create_collection()` for idempotent initialization

### HNSW Parameter Matching

For a fair comparison, both databases use identical HNSW parameters:

| Parameter | pgvector | ChromaDB | Default Value | Purpose |
|-----------|----------|----------|---------------|---------|
| Max connections | `m` | `max_neighbors` | 16 | Graph connectivity |
| Build quality | `ef_construction` | `ef_construction` | 100 | Index build accuracy |
| Search quality | `ef_search` | `ef_search` | 100 | Query-time recall |

**Why HNSW?** Both ChromaDB and pgvector support HNSW indexing. Using the same algorithm ensures that performance differences reflect database implementation characteristics (storage engine, query optimization, etc.) rather than different indexing strategies. HNSW provides excellent recall with sub-linear query time complexity, making it ideal for high-dimensional vector search.

### Error Handling
- Embedding dimension mismatches raise RuntimeError
- Missing text/URL in ingest returns 400
- HTTP errors from external services propagate as FastAPI exceptions

---

## Benchmark System

### Zweck
Vollständiges Benchmark-System für Performance-Analyse im Rahmen der wissenschaftlichen Arbeit (WAB). Vergleicht PgVector vs. ChromaDB mit verschiedenen OpenAPI-Spezifikationen.

### Komponenten
- **`benchmark/api_specs_list.json`**: Kuratierte Liste von OpenAPI-Specs (small/medium/large)
- **`benchmark/benchmark.py`**: Automatisiertes Benchmark-Skript
- **`benchmark/visualize.py`**: Visualisierungs-Tool für Ergebnisse
- **`benchmark/README.md`**: Detaillierte Benchmark-Anleitung

### Neue API-Endpunkte

**GET `/stats`**
```json
{
  "pg_document_count": 42,
  "pg_size_mb": 15.3,
  "chroma_document_count": 42,
  "chroma_size_mb": 8.7
}
```

**POST `/reset`**
```json
{
  "status": "success",
  "message": "Both databases have been reset"
}
```

### Gemessene Metriken

**Ingest:**
- `embed_ms` - Embedding-Erstellungszeit (Ollama)
- `pg_write_ms` - PgVector Schreibzeit
- `chroma_write_ms` - ChromaDB Schreibzeit
- `num_chunks` - Anzahl erzeugter Chunks

**Query:**
- `query_embed_ms` - Query-Embedding-Zeit
- `pg_query_ms` - PgVector Suchzeit
- `chroma_query_ms` - ChromaDB Suchzeit
- Result counts und Scores

**Storage:**
- `db_size_pg_mb` - PgVector Datenbankgröße
- `db_size_chroma_mb` - ChromaDB Größe (geschätzt)

### Schnellstart

```bash
# Benchmark-Tools installieren
cd benchmark
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Kleiner Test (3 Runs, nur small APIs)
python benchmark.py --runs 3 --categories small

# Vollständiger Benchmark (10 Runs, alle Kategorien)
python benchmark.py --runs 10

# Ergebnisse visualisieren
python visualize.py benchmark_results.csv --output-dir plots
```

### Output
- **CSV**: `benchmark_results.csv` mit allen Rohdaten
- **Plots**:
  - Ingest/Query Performance Comparison
  - Category-based Analysis
  - Database Size Comparison
  - Statistical Summary (Tabelle + CSV)

### Wissenschaftliche Verwendung
- Mindestens 10-20 Runs pro Spec für statistische Signifikanz
- Plots im `plots/` Verzeichnis mit 300 DPI (publikationsreif)
- `statistical_summary.csv` für Tabellen in der Arbeit
- Alle Metriken mit Standardabweichung
