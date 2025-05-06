import asyncio, gzip, hashlib, json, logging, shutil, aiofiles, aiosqlite
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .crawler import smart_fetch, extract_pdf_links
from .websearch import GoogleSearchAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_DIR = Path("history/websearch").resolve()
DB_PATH = HISTORY_DIR / "search_history.db"
LOG_RETENTION_DAYS = 30

def _ensure_history_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

async def _rotate_old_logs():
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for p in HISTORY_DIR.glob("*.jsonl"):
        if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
            gz = p.with_suffix(".jsonl.gz")
            try:
                with p.open("rb") as s, gzip.open(gz, "wb") as d:
                    shutil.copyfileobj(s, d)
                p.unlink()
                logger.info(f"[Rotate] {p.name} -> {gz.name}")
            except Exception as e:
                logger.warning(f"[Rotate FAIL] {p} {e}")

async def _append_history(record: Dict[str, Any]):
    _ensure_history_dir()
    await _rotate_old_logs()
    fn = HISTORY_DIR / (datetime.now().strftime("%Y-%m-%d") + ".jsonl")
    async with aiofiles.open(fn, "a", encoding="utf-8") as f:
        await f.write(json.dumps(record, ensure_ascii=False) + "\n")

async def _ensure_db():
    _ensure_history_dir()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS searches(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT, query TEXT, params TEXT
            );
            CREATE TABLE IF NOT EXISTS results(
              search_id INTEGER,
              title TEXT, url TEXT, snippet TEXT,
              content TEXT, pdfs_json TEXT, status TEXT, hash TEXT UNIQUE,
              FOREIGN KEY(search_id) REFERENCES searches(id)
            );
            """
        )
        await db.commit()

async def _insert_db(rec: Dict[str, Any]):
    await _ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys=ON")
        cur = await db.execute(
            "INSERT INTO searches(ts,query,params) VALUES (?,?,?)",
            (rec["timestamp"], rec["query"], json.dumps(rec["params"], ensure_ascii=False)),
        )
        sid = cur.lastrowid
        rows = [
            (
                sid,
                r["title"],
                r["url"],
                r["snippet"],
                r["content"],
                json.dumps(r["pdfs"], ensure_ascii=False),
                r["status"],
                r["hash"],
            )
            for r in rec["results"]
        ]
        await db.executemany(
            "INSERT OR IGNORE INTO results VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
        await db.commit()

async def search_and_collect(
    query: str,
    top_k: int = 5,
    mkt: str = "ko-KR",
    min_chars: int = 300,
    save_pdfs: bool = True,
    log_history: bool = True,
    save_db: bool = True,
    pdf_limit: int = 5,
) -> List[Dict]:
    google = GoogleSearchAPI()
    hits = (await google.web_search(query, mkt=mkt))[:top_k]

    pages = await asyncio.gather(*[smart_fetch(h.url) for h in hits], return_exceptions=True)

    combined = []
    for h, page in zip(hits, pages):
        status, text = "ok", ""
        pdfs: List[str] = []
        if isinstance(page, Exception):
            status = "error"
        else:
            text = page.strip()
            if len(text) < min_chars:
                status, text = "too_short", ""
        if save_pdfs and status == "ok":
            pdfs = await extract_pdf_links(url=h.url, auto_download=True, limit=pdf_limit)
        combined.append(
            {
                "title": h.title,
                "url": h.url,
                "snippet": h.snippet,
                "content": text,
                "pdfs": pdfs,
                "status": status,
                "hash": hashlib.sha1(text.encode()).hexdigest() if text else None,
            }
        )

    rec = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "query": query,
        "params": {"top_k": top_k, "mkt": mkt, "min_chars": min_chars, "save_pdfs": save_pdfs, "pdf_limit": pdf_limit},
        "results": combined,
    }
    if log_history:
        await _append_history(rec)
    if save_db:
        await _insert_db(rec)
    return combined
