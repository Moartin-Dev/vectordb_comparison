import httpx
import asyncio
from typing import List
from config import OLLAMA_URL, EMBEDDING_MODEL, EMBED_DIM
from utils import l2_normalize
from log import logger

async def ollama_embed(texts: List[str], max_retries: int = 5) -> List[List[float]]:
    out = []
    async with httpx.AsyncClient(timeout=120) as client:
        for t in texts:
            retries = 0
            while retries < max_retries:
                try:
                    url = f"{OLLAMA_URL}/api/embed"
                    payload = {
                        "model": EMBEDDING_MODEL,
                        "input": t,
                        "keep_alive": "10m"
                    }
                    logger.info(f"Sending request to {url} with model={EMBEDDING_MODEL}")

                    r = await client.post(url, json=payload)

                    logger.info(f"Response status: {r.status_code}")
                    if r.status_code != 200:
                        logger.error(f"Response body: {r.text[:500]}")

                    r.raise_for_status()
                    embeddings = r.json().get("embeddings", [])
                    vec = embeddings[0] if embeddings else None
                    if not vec or len(vec) != EMBED_DIM:
                        raise RuntimeError(f"Unexpected embedding dim {len(vec) if vec else 0}, expected {EMBED_DIM}")
                    out.append(l2_normalize(vec))
                    logger.info(f"Successfully embedded text (length={len(t)})")
                    break  # Success, exit retry loop
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404 and retries < max_retries - 1:
                        # Model is loading, wait and retry
                        wait_time = 3 ** retries  # Exponential backoff: 1s, 3s, 9s, 27s, 81s
                        logger.warning(f"Model not ready (404), retrying in {wait_time}s... ({retries + 1}/{max_retries})")
                        logger.warning(f"404 Response: {e.response.text[:200]}")
                        await asyncio.sleep(wait_time)
                        retries += 1
                    else:
                        logger.error(f"HTTP error {e.response.status_code}: {e.response.text[:500]}")
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error during embedding: {type(e).__name__}: {str(e)}")
                    raise
    return out
