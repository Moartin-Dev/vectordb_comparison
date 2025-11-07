from fastapi import APIRouter, HTTPException
import httpx
from schemas import IngestRequest, QueryRequest
from config import CHUNK_SIZE, CHUNK_OVERLAP
from utils import extract_text_from_openapi, chunk_text, now_ms
from embeddings import ollama_embed
from db_pg import replace_source as pg_replace, query_topk as pg_query, get_stats as pg_get_stats, reset_database as pg_reset
from chroma_client import upsert_source as chroma_upsert, query as chroma_query, get_stats as chroma_get_stats, reset_collection as chroma_reset


router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/embed")
async def embed(text: str):
    t0 = now_ms()
    vec = (await ollama_embed([text]))[0]
    return {"dim": len(vec), "latency_ms": now_ms() - t0}

async def _http_get_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

@router.post("/ingest")
async def ingest(req: IngestRequest):
    if not req.text and not req.url:
        raise HTTPException(400, "Provide either 'text' or 'url'.")
    raw = req.text if req.text is not None else await _http_get_text(req.url)
    extracted = extract_text_from_openapi(raw)
    chunks = chunk_text(extracted, req.chunk_size or CHUNK_SIZE, req.chunk_overlap or CHUNK_OVERLAP)
    if not chunks:
        raise HTTPException(400, "No text to ingest after parsing/chunking.")

    t0 = now_ms()
    embeds = await ollama_embed(chunks)
    t_embed = now_ms() - t0

    out = {"source": req.source, "num_chunks": len(chunks), "embed_ms": t_embed}

    if req.backend in ("pg", "both"):
        t_pg = now_ms()
        pg_replace(req.source, chunks, embeds)
        out["pg_write_ms"] = now_ms() - t_pg

    if req.backend in ("chroma", "both"):
        t_c = now_ms()
        chroma_upsert(req.source, chunks, embeds)
        out["chroma_write_ms"] = now_ms() - t_c

    return out

@router.post("/query")
async def query(req: QueryRequest):
    t0 = now_ms()
    qvec = (await ollama_embed([req.text]))[0]
    t_embed = now_ms() - t0

    pg_ms0 = now_ms()
    pg_hits = pg_query(qvec, req.k)
    pg_ms = now_ms() - pg_ms0

    c_ms0 = now_ms()
    res = chroma_query(qvec, k=req.k)
    c_ms = now_ms() - c_ms0
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    chroma_hits = [
        {
            "source": m.get("source"),
            "chunk_id": m.get("chunk"),
            "content": (d or "")[:400],
            "score": 1.0 - float(dist),
        }
        for d, m, dist in zip(docs, metas, dists)
    ]

    return {
        "k": req.k,
        "embed_ms": t_embed,
        "pg_ms": pg_ms,
        "pg_results": pg_hits,
        "chroma_ms": c_ms,
        "chroma_results": chroma_hits
    }

@router.get("/stats")
async def stats():
    """Gibt Statistiken über beide Datenbanken zurück"""
    pg_stats = pg_get_stats()
    chroma_stats = chroma_get_stats()

    return {
        "pg_document_count": pg_stats["document_count"],
        "pg_size_mb": pg_stats["size_mb"],
        "chroma_document_count": chroma_stats["document_count"],
        "chroma_size_mb": chroma_stats["size_mb"]
    }

@router.post("/reset")
async def reset():
    """Setzt beide Datenbanken zurück (löscht alle Daten)"""
    pg_reset()
    chroma_reset()

    return {
        "status": "success",
        "message": "Both databases have been reset"
    }
