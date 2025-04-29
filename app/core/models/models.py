from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional, List, Dict, Any, Tuple

class StockPrice(BaseModel):
    ticker: str
    datetime: datetime
    open: str | None
    high: str | None
    low: str | None
    close: str | None
    volume: str | None

class DocumentContent(BaseModel):
    html: str
    markdown: Optional[str] = None
    text: Optional[str] = None

class ParsedDocument(BaseModel):
    paragraphs: List[str]
    tables: List[List[List[str]]]  # Table: list of rows -> list of cells

class SearchResult(BaseModel):
    type: Literal["web", "news"]
    title: str
    url: str
    snippet: str
    provider: str | None = None