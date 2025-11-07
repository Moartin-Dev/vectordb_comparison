import math, time, yaml
from typing import List

def now_ms() -> float:
    return time.perf_counter() * 1000.0

def l2_normalize(vec: List[float]) -> List[float]:
    s = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / s for v in vec]

def vector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in vec) + "]"

def read_secret(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    chunks, n = [], len(t)
    start = 0
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(t[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

def extract_text_from_openapi(raw: str) -> str:
    try:
        data = yaml.safe_load(raw)
        parts = []
        if isinstance(data, dict):
            info = data.get("info", {})
            if isinstance(info, dict):
                parts += [str(info.get("title", "")), str(info.get("description", ""))]
            paths = data.get("paths", {})
            if isinstance(paths, dict):
                for p, ops in paths.items():
                    parts.append(str(p))
                    if isinstance(ops, dict):
                        for m, spec in ops.items():
                            parts.append(str(m))
                            if isinstance(spec, dict):
                                for k in ("summary", "description"):
                                    if k in spec and spec[k]:
                                        parts.append(str(spec[k]))
                                tags = spec.get("tags")
                                if isinstance(tags, list):
                                    parts += [str(t) for t in tags]
        txt = "\n".join([x for x in parts if x and x.strip()])
        return txt if txt.strip() else raw
    except Exception:
        return raw
