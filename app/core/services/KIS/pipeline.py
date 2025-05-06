"""
app/core/services/pipeline.py
주가 시계열을 수집(get_stockinfo)한 뒤
1) SQLite  |history/stock_price/stock_price.db|
2) JSONL   |history/stock_price/YYYY-MM-DD.jsonl|
3) CSV     |history/stock_price/TS.csv|
로 저장한다.
"""
from __future__ import annotations

import json, logging, gzip, shutil, aiofiles, aiosqlite, pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union, List, Dict, Any

from .stockinfo import StockInfoFetcher                 # ← 기존 모듈
from app.core.settings.basedata import stockbasedata    # ← 정적 매핑

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ────────────────────────────────────────────── 경로/상수
HISTORY_DIR = Path("history/stock_price").resolve()
DB_PATH      = HISTORY_DIR / "stock_price.db"
LOG_RETENTION_DAYS = 30
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────── 정적 매핑 캐시
_stock_info_map: Dict[str, pd.DataFrame] = stockbasedata.data()

# ────────────────────────────────────────────── 유틸
def _rotate_logs():
    """30일 지난 JSONL → GZIP 압축"""
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for p in HISTORY_DIR.glob("*.jsonl"):
        if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
            gz = p.with_suffix(".jsonl.gz")
            try:
                with p.open("rb") as src, gzip.open(gz, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                p.unlink()
                log.info(f"[Rotate] {p.name} -> {gz.name}")
            except Exception as e:
                log.warning(f"[Rotate FAIL] {p} {e}")

async def _ensure_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS prices(
              ts TEXT,
              ticker TEXT,
              datetime TEXT,
              price REAL,
              PRIMARY KEY(ticker, datetime)
            );
            """
        )
        await db.commit()

async def _insert_db(df: pd.DataFrame):
    await _ensure_db()
    rows = [
        (datetime.now().isoformat(), col, idx.isoformat(), float(val))
        for col in df.columns
        for idx, val in df[col].dropna().items()
    ]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO prices(ts,ticker,datetime,price) VALUES (?,?,?,?)",
            rows,
        )
        await db.commit()

# ────────────────────────────────────────────── 이름→티커 변환
def _ticker_translate(names: Union[str, List[str]], market: str) -> Dict[str, List[str]]:
    df = _stock_info_map.get(market)
    if df is None:
        raise ValueError(f"Market '{market}' not found")

    if isinstance(names, str):
        names = [names]

    ticker, stock = [], []
    for n in names:
        m = df[df["name"] == n]
        if m.empty:
            log.warning(f"[translate] '{n}' not in market '{market}'")
            continue
        ticker.append(str(m["ticker"].iloc[0]))
        stock.append(str(m["name"].iloc[0]))
    return {"ticker": ticker, "stock": stock}

# ────────────────────────────────────────────── 시계열 수집
def get_stockinfo(
    stocks: List[Union[str, int]],
    timeframe: str,
    adj_price: bool = True,
    option: str = "close",
    market: str = "KOSPI",
) -> pd.DataFrame:
    market_key = market.lower()
    df_map = _stock_info_map.get(market_key)
    if df_map is None:
        raise ValueError(f"Market '{market}' not prepared")

    fetcher = StockInfoFetcher(mock=False)
    frames, errors = [], []

    for s in stocks:
        key = str(s).strip()
        # ① 티커 직접 입력
        if key in df_map["ticker"].astype(str).values:
            ticker = key
        # ② 종목명 입력
        elif key in df_map["name"].values:
            res = _ticker_translate(key, market_key)
            ticker = res["ticker"][0] if res["ticker"] else None
        else:
            errors.append(key)
            continue

        if not ticker:
            errors.append(key)
            continue
        
        # ── 가격 호출
        try:
            price_objs = fetcher.get_stock_price(ticker, timeframe, adj_price)
            df = pd.DataFrame([p.dict() for p in price_objs])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            df = df[[option]].rename(columns={option: ticker})
            frames.append(df)
        except Exception as e:
            log.warning(f"[fetch] fail '{ticker}' {e}")
            errors.append(ticker)

    if not frames:
        log.error("empty DataFrame returned")
        return pd.DataFrame()

    if errors:
        log.info(f"Issues: {errors}")

    return pd.concat(frames, axis=1, join="outer").sort_index()

# ────────────────────────────────────────────── 메인 진입
async def fetch_and_save(
    stocks: List[Union[str, int]],
    timeframe: str = "1d",
    option: str = "close",
    market: str = "KOSPI",
    adj_price: bool = True,
):
    df = get_stockinfo(
        stocks=stocks,
        timeframe=timeframe,
        adj_price=adj_price,
        option=option,
        market=market,
    )
    if df.empty:
        return None

    # 1. DB
    await _insert_db(df)

    # 2. CSV (스냅샷)
    csv_path = HISTORY_DIR / f"{datetime.now():%Y%m%d_%H%M%S}.csv"
    df.to_csv(csv_path)
    log.info(f"[CSV] {csv_path.name}")

    # 3. JSONL 히스토리
    _rotate_logs()
    hist = HISTORY_DIR / f"{datetime.now():%Y-%m-%d}.jsonl"
    async with aiofiles.open(hist, "a", encoding="utf-8") as fp:
        await fp.write(
            json.dumps(
                {
                    "ts": datetime.now().isoformat(),
                    "stocks": stocks,
                    "timeframe": timeframe,
                    "option": option,
                    "market": market,
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    return df  # 필요 시 반환
