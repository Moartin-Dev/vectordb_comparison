from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from log import logger
from config import (
    OLLAMA_URL, CHROMA_URL, PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD_FILE,
    CHROMA_WAIT_MAX, CHROMA_WAIT_INT, OLLAMA_WAIT_MAX, OLLAMA_WAIT_INT, PG_WAIT_MAX, PG_WAIT_INT
)
from waiters import wait_for_http_ok, wait_for_postgres
from db_pg import init_pg_schema
from chroma_client import init_chroma
from routers import router as api_router
from benchmark_streaming import router as benchmark_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warten bis Services wirklich ansprechbar sind
    await wait_for_http_ok("Chroma", f"{CHROMA_URL}/api/v2/heartbeat", CHROMA_WAIT_MAX, CHROMA_WAIT_INT, expect_status=200)
    await wait_for_http_ok("Ollama", f"{OLLAMA_URL}/api/tags", OLLAMA_WAIT_MAX, OLLAMA_WAIT_INT, expect_status=200)
    await wait_for_postgres(PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD_FILE, PG_WAIT_MAX, PG_WAIT_INT)

    # Init
    init_pg_schema()
    init_chroma()

    # Warmup: Load embedding model
    from embeddings import ollama_embed
    try:
        await ollama_embed(["warmup"])
        logger.info("✅  Embedding model warmed up")
    except Exception as e:
        logger.warning(f"⚠️  Embedding warmup failed: {e}")

    logger.info("🚀  Dependencies ready; schema & collection initialized.")
    yield
    logger.info("👋  API shutting down.")

app = FastAPI(title="WAB Benchmark API", lifespan=lifespan)

# CORS für Frontend (Angular)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://frontend:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(benchmark_router)


