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
    """
    Extrahiert strukturierten Text aus OpenAPI-Spezifikation für RAG.
    Unterstützt OpenAPI 2.x und 3.x (YAML/JSON).

    Extrahiert:
    - Info (title, description)
    - Paths mit Operations (summary, description, parameters)
    - Schemas/Definitions (properties, descriptions)
    - Request/Response Bodies
    """
    try:
        # Versuche zuerst als JSON zu parsen (schneller und robuster)
        import json
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            # Falls JSON fehlschlägt, versuche YAML mit UnsafeLoader
            # (UnsafeLoader kann mehr YAML-Features parsen, auch wenn sie nicht standard sind)
            try:
                data = yaml.load(raw, Loader=yaml.UnsafeLoader)
            except Exception:
                # Als letzter Versuch: FullLoader
                data = yaml.load(raw, Loader=yaml.FullLoader)

        parts = []

        if not isinstance(data, dict):
            return raw

        # 1. Info-Bereich
        info = data.get("info", {})
        if isinstance(info, dict):
            parts += [str(info.get("title", "")), str(info.get("description", ""))]

        # 2. Paths mit Operations
        paths = data.get("paths", {})
        if isinstance(paths, dict):
            for path, ops in paths.items():
                parts.append(f"Path: {path}")
                if isinstance(ops, dict):
                    for method, spec in ops.items():
                        if not isinstance(spec, dict):
                            continue
                        parts.append(f"Method: {method}")

                        # Operation summary, description, tags
                        for k in ("summary", "description"):
                            if k in spec and spec[k]:
                                parts.append(str(spec[k]))
                        tags = spec.get("tags")
                        if isinstance(tags, list):
                            parts += [str(t) for t in tags]

                        # Parameters (OpenAPI 2.x und 3.x)
                        params = spec.get("parameters", [])
                        if isinstance(params, list):
                            for param in params:
                                if isinstance(param, dict):
                                    p_name = param.get("name", "")
                                    p_desc = param.get("description", "")
                                    if p_name:
                                        parts.append(f"Parameter: {p_name}")
                                    if p_desc:
                                        parts.append(str(p_desc))

                        # Request Body (OpenAPI 3.x)
                        req_body = spec.get("requestBody", {})
                        if isinstance(req_body, dict):
                            rb_desc = req_body.get("description", "")
                            if rb_desc:
                                parts.append(f"Request: {rb_desc}")

                        # Responses
                        responses = spec.get("responses", {})
                        if isinstance(responses, dict):
                            for status_code, resp in responses.items():
                                if isinstance(resp, dict):
                                    r_desc = resp.get("description", "")
                                    if r_desc:
                                        parts.append(f"Response {status_code}: {r_desc}")

        # 3. Schemas/Components (OpenAPI 3.x)
        components = data.get("components", {})
        if isinstance(components, dict):
            schemas = components.get("schemas", {})
            _extract_schemas(schemas, parts)

        # 4. Definitions (OpenAPI 2.x)
        definitions = data.get("definitions", {})
        if isinstance(definitions, dict):
            _extract_schemas(definitions, parts)

        txt = "\n".join([x for x in parts if x and x.strip()])
        return txt if txt.strip() else raw
    except Exception:
        return raw


def _extract_schemas(schemas: dict, parts: List[str]) -> None:
    """
    Hilfsfunktion: Extrahiert Text aus Schema-Definitionen.
    Sammelt Namen, Descriptions und Property-Informationen.
    """
    if not isinstance(schemas, dict):
        return

    for schema_name, schema_def in schemas.items():
        if not isinstance(schema_def, dict):
            continue

        parts.append(f"Schema: {schema_name}")

        # Schema description
        s_desc = schema_def.get("description", "")
        if s_desc:
            parts.append(str(s_desc))

        # Properties
        properties = schema_def.get("properties", {})
        if isinstance(properties, dict):
            for prop_name, prop_def in properties.items():
                if isinstance(prop_def, dict):
                    prop_desc = prop_def.get("description", "")
                    prop_type = prop_def.get("type", "")
                    prop_info = f"Property: {prop_name}"
                    if prop_type:
                        prop_info += f" ({prop_type})"
                    parts.append(prop_info)
                    if prop_desc:
                        parts.append(str(prop_desc))
