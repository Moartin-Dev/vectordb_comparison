import httpx
from typing import List
from config import OLLAMA_URL, EMBEDDING_MODEL, EMBED_DIM
from utils import l2_normalize

async def ollama_embed(texts: List[str]) -> List[List[float]]:
    out = []
    async with httpx.AsyncClient(timeout=120) as client:
        for t in texts:
            r = await client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": t})
            r.raise_for_status()
            vec = r.json().get("embedding")
            if not vec or len(vec) != EMBED_DIM:
                raise RuntimeError(f"Unexpected embedding dim {len(vec) if vec else 0}, expected {EMBED_DIM}")
            out.append(l2_normalize(vec))
    return out
