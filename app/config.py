import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Services
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gte-base")

PG_HOST = os.getenv("PG_HOST", "pgvector")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "postgres")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD_FILE = os.getenv("PG_PASSWORD_FILE", "/run/secrets/postgres_password")

# Wait config
CHROMA_WAIT_MAX = int(os.getenv("CHROMA_WAIT_MAX_SECONDS", "180"))
CHROMA_WAIT_INT = float(os.getenv("CHROMA_WAIT_INTERVAL_SECONDS", "2"))
OLLAMA_WAIT_MAX = int(os.getenv("OLLAMA_WAIT_MAX_SECONDS", "180"))
OLLAMA_WAIT_INT = float(os.getenv("OLLAMA_WAIT_INTERVAL_SECONDS", "2"))
PG_WAIT_MAX     = int(os.getenv("PG_WAIT_MAX_SECONDS", "120"))
PG_WAIT_INT     = float(os.getenv("PG_WAIT_INTERVAL_SECONDS", "2"))

# Vector & collections
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "apispecs")

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# PG HNSW index (matched to ChromaDB defaults for fair comparison)
PG_HNSW_M = int(os.getenv("PG_HNSW_M", "16"))  # max connections per layer (ChromaDB: max_neighbors=16)
PG_HNSW_EF_CONSTRUCTION = int(os.getenv("PG_HNSW_EF_CONSTRUCTION", "100"))  # build quality (ChromaDB: ef_construction=100)
PG_HNSW_EF_SEARCH = int(os.getenv("PG_HNSW_EF_SEARCH", "100"))  # query quality (ChromaDB: ef_search=100)
