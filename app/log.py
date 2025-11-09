import logging
from config import LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("uvicorn")

# Deaktiviere httpx INFO-Logs (zu verbose während Embedding)
logging.getLogger("httpx").setLevel(logging.WARNING)

__all__ = ["logger"]
