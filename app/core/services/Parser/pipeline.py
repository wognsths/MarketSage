import json, logging, gzip, shutil, aiofiles, aiosqlite, asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from .parser import UPSTAGEparser, reconstruct_table
from app.core.models.models import ParsedDocument

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

HISTORY_DIR = Path("history/document_parse").resolve()
DB_PATH = HISTORY_DIR / "document_parse.db"
LOG_RETENTION_DAYS = 30
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

parser = UPSTAGEparser()


def _rotate_logs():
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for p in HISTORY_DIR.glob("*.jsonl"):
        if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
            gz = p.with_suffix(".jsonl.gz")
            try:
                with p.open("rb") as s, gzip.open(gz, "wb") as d:
                    shutil.copyfileobj(s, d)
                p.unlink()
                log.info(f"[Rotate] {p.name} -> {gz.name}")
            except Exception as e:
                log.warning(f"[Rotate FAIL] {p} {e}")


async def _ensure_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT, file TEXT UNIQUE,
              paragraphs_json TEXT, tables_json TEXT
            );
            """
        )
        await db.commit()


async def _insert_db(rec: Dict[str, Any]):
    await _ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO documents(ts,file,paragraphs_json,tables_json)
            VALUES (?,?,?,?)
            """,
            (
                rec["timestamp"],
                rec["file"],
                json.dumps(rec["paragraphs"], ensure_ascii=False),
                json.dumps(rec["tables"], ensure_ascii=False),
            ),
        )
        await db.commit()


async def _parse_one(path: Path) -> Dict[str, Any]:
    with path.open("rb") as f:
        content, err = parser.extract(f, path.name)
    if err or content is None:
        log.warning(f"[FAIL] {path.name} -> {err}")
        return {"file": str(path), "error": str(err)}

    parsed: ParsedDocument = parser.parse(content.html)

    log.info(f"Reconstructing table for file: {path.name}")
    reconstructed_table = await reconstruct_table(parsed.tables)
    rec = {
        "file": str(path),
        "paragraphs": parsed.paragraphs,
        "tables": parsed.tables,
        "reconstructed_tables": reconstructed_table,
        "timestamp": datetime.now().isoformat(),
    }

    out_json = HISTORY_DIR / f"{path.stem}.json"
    with out_json.open("w", encoding="utf-8") as fp:
        json.dump(rec, fp, ensure_ascii=False, indent=2)

    log.info(f"[OK] {path.name} -> {out_json.name}")
    return rec


async def parse_target(target: str | Path = "*", base_dir: str | Path = "pdfs"):
    """
    target:
        "*"          → base_dir 아래의 모든 *.pdf 파싱
        "sample.pdf" → 해당 파일만 파싱
        "dir/"       → 해당 폴더 안의 모든 *.pdf 파싱
    """
    base_dir = Path(base_dir)
    if target == "*":
        pdf_list = list(base_dir.glob("*.pdf"))
    else:
        t_path = Path(target)
        if t_path.is_absolute() or t_path.exists():
            pdf_list = [t_path] if t_path.is_file() else list(t_path.glob("*.pdf"))
        else:
            pdf_list = [base_dir / target]

    pdf_files = [p for p in pdf_list if p.suffix.lower() == ".pdf" and p.exists()]
    if not pdf_files:
        log.warning("No PDF files matched.")
        return

    recs: List[Dict[str, Any]] = await asyncio.gather(*[_parse_one(p) for p in pdf_files])

    await _ensure_db()
    for r in recs:
        if "error" not in r:
            await _insert_db(r)

    _rotate_logs()
    hist = HISTORY_DIR / f"{datetime.now():%Y-%m-%d}.jsonl"
    async with aiofiles.open(hist, "a", encoding="utf-8") as fp:
        for r in recs:
            await fp.write(json.dumps(r, ensure_ascii=False) + "\n")

    