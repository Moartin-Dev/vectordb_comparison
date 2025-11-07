import time, asyncio, httpx, psycopg
from psycopg.rows import tuple_row
from log import logger
from utils import read_secret

async def wait_for_http_ok(name: str, url: str, max_seconds: int, interval: float, expect_status: int = 200):
    logger.info("➡️  [%s] Warte auf %s ... (Timeout=%ss, Intervall=%ss)", name, url, max_seconds, interval)
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
            if tries % max(1, int(10/interval)) == 0:
                logger.info("⏳  [%s] noch nicht bereit ... (tries=%d, last_err=%s)", name, tries, last_err)
            await asyncio.sleep(interval)
    logger.error("❌  [%s] Timeout: %s", name, last_err)
    raise TimeoutError(f"Timeout waiting for {name} at {url} (last_err={last_err})")

async def wait_for_postgres(host: str, port: int, db: str, user: str, password_file: str,
                            max_seconds: int, interval: float):
    logger.info("➡️  [Postgres] Verbinde zu %s:%s/%s als %s ...", host, port, db, user)
    password = read_secret(password_file)
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
                    cur.fetchone()
                    dt = (time.monotonic() - t0) * 1000
                    logger.info("✅  [Postgres] bereit nach %.0f ms (tries=%d)", dt, tries)
                    return
        except Exception as e:
            last_err = repr(e)
        if tries % max(1, int(10/interval)) == 0:
            logger.info("⏳  [Postgres] noch nicht bereit ... (tries=%d, last_err=%s)", tries, last_err)
        await asyncio.sleep(interval)
    logger.error("❌  [Postgres] Timeout: %s", last_err)
    raise TimeoutError(f"Timeout waiting for Postgres ({host}:{port}) (last_err={last_err})")
