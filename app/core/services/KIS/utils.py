from app.core.services.KIS.stockinfo import StockInfoFetcher
import pandas as pd
from typing import Union, List, Dict
from app.core.settings.basedata import stockbasedata
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load static stock mapping (e.g., 'kospi', 'sp500')
stock_info_map: Dict[str, pd.DataFrame] = stockbasedata.data()


def ticker_name_translater(
    names: Union[str, List[str]],
    market: str
) -> Dict[str, List[str]]:
    """
    Translate stock names to tickers for a given market.

    Args:
        names: Single name or list of stock names.
        market: Market key (e.g., 'kospi', 'sp500').

    Returns:
        Dict with keys 'ticker' and 'stock', each a list of matched values.
    """
    df = stock_info_map.get(market.lower())
    if df is None:
        raise ValueError(f"Market '{market}' not found in static data")

    if isinstance(names, str):
        names = [names]

    ticker_list: List[str] = []
    name_list: List[str] = []

    for name in names:
        matched = df[df["name"] == name]
        if matched.empty:
            logger.warning(
                f"[ticker_name_translater] '{name}' not found in market '{market}'"
            )
            continue
        ticker_list.append(str(matched["ticker"].iloc[0]))
        name_list.append(str(matched["name"].iloc[0]))

    return {"ticker": ticker_list, "stock": name_list}


def get_stockinfo(
    stocks: List[Union[str, int]],
    timeframe: str,
    adj_price: bool = True,
    option: str = "close",
    market: str = "KOSPI"
) -> pd.DataFrame:
    """
    Fetch time series for multiple stocks and merge into a single DataFrame.

    Args:
        stocks: List of tickers or stock names.
        timeframe: Time granularity (e.g., '1d', '1m').
        adj_price: Whether to return adjusted prices.
        option: Which price field to include ('open','high','low','close','volume').
        market: Market key corresponding to static data.

    Returns:
        DataFrame indexed by datetime, columns are tickers, values are specified price field,
        with outer join to preserve missing/halts as NaN.
    """
    market_key = market.lower()
    df_market = stock_info_map.get(market_key)
    if df_market is None:
        raise ValueError(
            f"Market '{market}' not in static data: {list(stock_info_map.keys())}"
        )

    fetcher = StockInfoFetcher(mock=False)
    price_frames: List[pd.DataFrame] = []
    errors: List[str] = []

    for s in stocks:
        key = str(s).strip()
        # Determine ticker
        if key in df_market["ticker"].astype(str).values:
            ticker = key
        elif key in df_market["name"].values:
            res = ticker_name_translater(key, market_key)
            if not res["ticker"]:
                errors.append(key)
                continue
            ticker = res["ticker"][0]
        else:
            logger.warning(
                f"[get_stockinfo] '{key}' not found in market '{market_key}'"
            )
            errors.append(key)
            continue

        # Fetch OHLCV and convert to DataFrame
        try:
            stock_prices = fetcher.get_stock_price(ticker, timeframe, adj_price)
            df = pd.DataFrame([p.dict() for p in stock_prices])
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
            df = df[[option]].rename(columns={option: ticker})
            price_frames.append(df)
        except Exception as exc:
            logger.warning(
                f"[get_stockinfo] Fetch failed for '{ticker}': {exc}"
            )
            errors.append(ticker)

    if not price_frames:
        logger.error(
            "No valid price frames fetched; returning empty DataFrame"
        )
        return pd.DataFrame()

    # Outer join on datetime index to include NaN for missing data
    result_df = pd.concat(
        price_frames, axis=1, join="outer"
    ).sort_index()
    if errors:
        logger.info(f"Issues encountered for: {errors}")

    return result_df
