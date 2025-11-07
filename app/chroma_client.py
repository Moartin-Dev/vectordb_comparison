# chroma_client.py
from typing import List, Optional
import os
import chromadb  # kommt aus chromadb-client (Public API)
from chromadb.config import Settings

_client = None
_collection = None

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "api_specs")

def init_chroma(host: str = "chroma", port: int = 8000):
    global _client, _collection

    # Wichtig: v2-Client + Telemetrie aus
    settings = Settings(anonymized_telemetry=False)
    _client = chromadb.HttpClient(host=host, port=port, settings=settings)

    # get_or_create_collection ist gleich geblieben in v2-Client
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "OpenAPI specs for RAG benchmarking"},
    )

def upsert_source(source: str, chunks: List[str], embeddings: List[List[float]]):
    assert _collection is not None
    ids = [f"{source}::{i}" for i in range(len(chunks))]
    metadatas = [{"source": source, "chunk": i} for i in range(len(chunks))]
    _collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

def query(embedding: List[float], k: int = 5, where: Optional[dict] = None):
    assert _collection is not None
    return _collection.query(
        query_embeddings=[embedding],
        n_results=k,
        where=where or {},
    )

def reset_collection():
    global _collection
    if _collection is not None:
        _client.delete_collection(_collection.name)
    _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
