import httpx
import asyncio
from typing import List
from config import OLLAMA_URL, EMBEDDING_MODEL, EMBED_DIM
from utils import l2_normalize
from log import logger

# Batch-Größe für Embeddings (Balance zwischen Durchsatz und Memory)
BATCH_SIZE = 32

async def ollama_embed(texts: List[str], max_retries: int = 5) -> List[List[float]]:
    """
    Erstellt Embeddings für eine Liste von Texten in Batches.
    Sendet mehrere Texte pro Request für bessere Performance.
    """
    if not texts:
        return []

    all_embeddings = []

    async with httpx.AsyncClient(timeout=180) as client:
        # Verarbeite Texte in Batches
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(texts))
            batch = texts[batch_start:batch_end]

            retries = 0
            while retries < max_retries:
                try:
                    url = f"{OLLAMA_URL}/api/embed"
                    payload = {
                        "model": EMBEDDING_MODEL,
                        "input": batch,  # Ollama unterstützt Liste von Strings
                        "keep_alive": "10m",
                        "options": {
                            "num_ctx": 512  # Erhöht von default 256 auf 512 für längere Texte
                        }
                    }

                    r = await client.post(url, json=payload)

                    if r.status_code != 200:
                        logger.error(f"Response body: {r.text[:500]}")

                    r.raise_for_status()
                    embeddings = r.json().get("embeddings", [])

                    # Validiere Anzahl und Dimensionen
                    if len(embeddings) != len(batch):
                        raise RuntimeError(f"Expected {len(batch)} embeddings, got {len(embeddings)}")

                    for vec in embeddings:
                        if not vec or len(vec) != EMBED_DIM:
                            raise RuntimeError(f"Unexpected embedding dim {len(vec) if vec else 0}, expected {EMBED_DIM}")
                        all_embeddings.append(l2_normalize(vec))

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
                    logger.error(f"Unexpected error during batch embedding: {type(e).__name__}: {str(e)}")
                    raise

    return all_embeddings
