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
    query_params = {
        "query_embeddings": [embedding],
        "n_results": k,
    }
    if where:
        query_params["where"] = where
    return _collection.query(**query_params)

def get_stats():
    """Gibt Statistiken über die ChromaDB-Collection zurück"""
    assert _collection is not None
    count = _collection.count()

    # ChromaDB Größe ist schwierig zu messen ohne Dateisystem-Zugriff
    # Schätzung basierend auf Dokumentenanzahl (grobe Näherung)
    # Für genauere Messung müsste man das Datenverzeichnis checken
    estimated_size_mb = count * 0.05  # Sehr grobe Schätzung: 50KB pro Dokument

    return {
        "document_count": count,
        "size_mb": round(estimated_size_mb, 2)
    }

def reset_collection():
    """Löscht alle Dokumente aus der Collection"""
    global _collection
    if _collection is not None:
        _client.delete_collection(_collection.name)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "OpenAPI specs for RAG benchmarking"}
    )
