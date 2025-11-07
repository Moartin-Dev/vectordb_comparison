from pydantic import BaseModel, Field
from typing import Optional

class IngestRequest(BaseModel):
    source: str = Field(..., description="z.B. URL oder Dateiname")
    text: Optional[str] = None
    url: Optional[str] = None
    backend: str = Field("both", pattern="^(pg|chroma|both)$")
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None

class QueryRequest(BaseModel):
    text: str
    k: int = 5
