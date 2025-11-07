from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os, httpx, time, asyncio, logging
import psycopg
from psycopg.rows import tuple_row

# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("uvicorn")  # zeigt in 'docker logs wab-api' und uvicorn-Output

# ---------- ENV ----------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gte-base")

PG_HOST = os.getenv("PG_HOST", "pgvector")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "postgres")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD_FILE = os.getenv("PG_PASSWORD_FILE", "/run/secrets/postgres_password")

CHROMA_WAIT_MAX = int(os.getenv("CHROMA_WAIT_MAX_SECONDS", "180"))
CHROMA_WAIT_INT = float(os.getenv("CHROMA_WAIT_INTERVAL_SECONDS", "2"))

OLLAMA_WAIT_MAX = int(os.getenv("OLLAMA_WAIT_MAX_SECONDS", "180"))
OLLAMA_WAIT_INT = float(os.getenv("OLLAMA_WAIT_INTERVAL_SECONDS", "2"))

PG_WAIT_MAX = int(os.getenv("PG_WAIT_MAX_SECONDS", "120"))
PG_WAIT_INT = float(os.getenv("PG_WAIT_INTERVAL_SECONDS", "2"))

# ---------- Helpers ----------
def _read_secret(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""

async def wait_for_http_ok(name: str, url: str, max_seconds: int, interval: float, expect_status: int = 200) -> None:
    """Poll a URL until expect_status or timeout; log Start/Every ~10 tries/Success/Timeout."""
    logger.info("➡️  [%s] Warte auf HTTP %s ... (Timeout=%ss, Intervall=%ss)", name, url, max_seconds, interval)
    t0 = time.monotonic()
    deadline = t0 + max_seconds
    last_err = None
    tries = 0
    async with httpx.AsyncClient(timeout=10) as client:
        while time.monotonic() < deadline:
            tries += 1
            try:
                r = await client.get(url)
                if r.status_code == expect_status:
                    dt = (time.monotonic() - t0) * 1000
                    logger.info("✅  [%s] bereit (HTTP %s) nach %.0f ms", name, r.status_code, dt)
                    return
                last_err = f"status={r.status_code} body={r.text[:160]}"
            except Exception as e:
                last_err = repr(e)
            if tries % max(1, int(10/interval)) == 0:  # ca. alle 10s
                logger.info("⏳  [%s] noch nicht bereit ... (tries=%d, last_err=%s)", name, tries, last_err)
            await asyncio.sleep(interval)
    dt = (time.monotonic() - t0)
    logger.error("❌  [%s] Timeout nach %.1fs: %s", name, dt, last_err)
    raise TimeoutError(f"Timeout waiting for {name} at {url} (last_err={last_err})")

async def wait_for_postgres(host: str, port: int, db: str, user: str, password_file: str,
                            max_seconds: int, interval: float) -> None:
    """Loop until a simple SELECT 1 succeeds; log Fortschritt."""
    logger.info("➡️  [Postgres] Verbinde zu %s:%s/%s als %s ... (Timeout=%ss, Intervall=%ss)",
                host, port, db, user, max_seconds, interval)
    password = _read_secret(password_file)
    dsn = f"host={host} port={port} dbname={db} user={user} password={password}"
    t0 = time.monotonic()
    deadline = t0 + max_seconds
    last_err = None
    tries = 0
    while time.monotonic() < deadline:
        tries += 1
        try:
            with psycopg.connect(dsn, connect_timeout=5) as conn:
                with conn.cursor(row_factory=tuple_row) as cur:
                    cur.execute("SELECT 1;")
                    _ = cur.fetchone()
                    dt = (time.monotonic() - t0) * 1000
                    logger.info("✅  [Postgres] bereit nach %.0f ms (tries=%d)", dt, tries)
                    return
        except Exception as e:
            last_err = repr(e)
        if tries % max(1, int(10/interval)) == 0:  # ca. alle 10s
            logger.info("⏳  [Postgres] noch nicht bereit ... (tries=%d, last_err=%s)", tries, last_err)
        await asyncio.sleep(interval)
    dt = (time.monotonic() - t0)
    logger.error("❌  [Postgres] Timeout nach %.1fs: %s", dt, last_err)
    raise TimeoutError(f"Timeout waiting for Postgres ({host}:{port}) (last_err={last_err})")

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) Chroma v2 Heartbeat
    await wait_for_http_ok("Chroma", f"{CHROMA_URL}/api/v2/heartbeat", CHROMA_WAIT_MAX, CHROMA_WAIT_INT, expect_status=200)
    # 2) Ollama Tags
    await wait_for_http_ok("Ollama", f"{OLLAMA_URL}/api/tags", OLLAMA_WAIT_MAX, OLLAMA_WAIT_INT, expect_status=200)
    # 3) Postgres
    await wait_for_postgres(PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD_FILE, PG_WAIT_MAX, PG_WAIT_INT)
    logger.info("🚀  Alle Abhängigkeiten sind bereit. API startet.")
    yield
    logger.info("👋  API wird beendet.")

app = FastAPI(title="WAB Benchmark API", lifespan=lifespan)

# ---------- Models / Endpoints ----------
class QueryRequest(BaseModel):
    text: str
    k: int = int(os.getenv("TOP_K", "5"))

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/embed")
async def embed(text: str):
    """Embedding via Ollama."""
    async with httpx.AsyncClient(timeout=120) as client:
        t0 = time.perf_counter()
        r = await client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": EMBEDDING_MODEL, "prompt": text})
        r.raise_for_status()
        vec = r.json().get("embedding")
        latency_ms = (time.perf_counter() - t0) * 1000
    return {"dim": len(vec) if vec else 0, "latency_ms": latency_ms}

@app.post("/query")
async def query(req: QueryRequest):
    """Placeholder – hier kommt gleich PGVector/Chroma-Query-Logik rein."""
    return {"received": req.model_dump()}
