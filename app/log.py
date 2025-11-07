import logging
from config import LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("uvicorn")

__all__ = ["logger"]
