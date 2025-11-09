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

def get_directory_size(path: str) -> float:
    """
    Berechnet die Größe eines Verzeichnisses rekursiv in MB.

    Args:
        path: Pfad zum Verzeichnis

    Returns:
        Größe in MB (float)
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                # Ignoriere Symlinks und nicht-existierende Dateien
                if os.path.exists(filepath) and not os.path.islink(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        print(f"Error calculating ChromaDB directory size: {e}")
        return 0.0

    return total_size / (1024 * 1024)  # Bytes zu MB

def get_filesystem_size() -> float:
    """
    Gibt die aktuelle Dateisystemgröße des ChromaDB-Verzeichnisses zurück.
    Wird für Differenzberechnungen verwendet (Größe nach - Größe vor Ingest).

    Returns:
        Größe in MB (float)
    """
    chroma_data_path = "/chroma-data"
    if os.path.exists(chroma_data_path):
        return get_directory_size(chroma_data_path)
    else:
        print(f"Warning: ChromaDB data path not found: {chroma_data_path}")
        return 0.0

def get_collection_size_mb() -> float:
    """
    Berechnet die tatsächliche Größe der ChromaDB-Collection basierend auf
    Anzahl Dokumente und Embedding-Dimensionen.

    Berechnung:
    - Embeddings: count × 384 dims × 4 bytes (float32) = count × 1,536 bytes
    - Text-Dokumente: ~1,200 bytes (durchschnittliche Chunk-Größe)
    - Metadaten (source, chunk_id): ~100 bytes
    - SQLite Indizes und Overhead: ~30% zusätzlich

    Insgesamt: count × (1,536 + 1,200 + 100) × 1.3 = count × ~3,700 bytes

    Returns:
        Größe in MB
    """
    assert _collection is not None
    count = _collection.count()

    if count == 0:
        return 0.0

    # Embedding-Größe: 384 dimensions × 4 bytes (float32)
    embedding_size_bytes = 384 * 4  # 1,536 bytes

    # Durchschnittliche Text-Größe pro Chunk (CHUNK_SIZE ist 1200 chars)
    text_size_bytes = 1200  # ~1,200 bytes UTF-8

    # Metadaten (source string, chunk_id int)
    metadata_size_bytes = 100

    # Basis-Größe
    base_size_bytes = count * (embedding_size_bytes + text_size_bytes + metadata_size_bytes)

    # SQLite Indizes und Overhead (~30%)
    total_size_bytes = base_size_bytes * 1.3

    # Konvertiere zu MB
    return total_size_bytes / (1024 * 1024)

def get_stats():
    """Gibt Statistiken über die ChromaDB-Collection zurück"""
    assert _collection is not None
    count = _collection.count()
    size_mb = get_collection_size_mb()

    return {
        "document_count": count,
        "size_mb": round(size_mb, 2)
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
