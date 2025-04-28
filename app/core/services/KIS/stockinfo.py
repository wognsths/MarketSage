from app.core.services.KIS.broker import create_broker
import pandas as pd

class StockInfoFetcher:
    """
    A utility class to fetch stock price information using the KIS (Korea Investment & Securities) API.
    """

    def __init__(self, mock: bool = False):
        """
        Initialize the StockInfoFetcher.

        Args:
            mock (bool, optional): Whether to use a mock environment. Defaults to False.
        """
        self.broker = create_broker(mock=mock)

    def get_stock_price_today(self, ticker: str | int) -> dict:
        """
        Fetch the current market price for the given ticker code (today).

        Args:
            ticker (str | int): 
                Stock ticker code (e.g., "005930" for Samsung Electronics).

        Returns:
            dict: 
                Current day's stock price information.
        """
        response = self.broker.fetch_price(str(ticker))
        item = response.get("output", {})

        parsed = {
            "ticker": ticker,
            "date": pd.to_datetime(item.get('stck_bsop_date'), format="%Y%m%d"),
            "open": item.get('stck_oprc'),
            "high": item.get('stck_hgpr'),
            "low": item.get('stck_lwpr'),
            "close": item.get('stck_prpr'),
            "volume": item.get('acml_vol')
        }

        return parsed

    def get_stock_price(self, ticker: str | int, timeframe: str, adj_price: bool = True) -> dict:
        """
        Fetch historical market price data for the given ticker code.

        Args:
            ticker (str | int): 
                Stock ticker code (e.g., "005930" for Samsung Electronics).
            timeframe (str): 
                Time granularity: 'D' (daily), 'W' (weekly), 'M' (monthly).
            adj_price (bool, optional): 
                Whether to reflect adjusted prices. Defaults to True.
                
                (Adjusted prices refer to past stock prices that have been corrected to align 
                with the current price following events such as stock splits, reverse splits, 
                and other corporate actions.)

        Returns:
            dict: 
                Historical stock price data:
                - D: Last 30 trading days
                - W: Last 30 trading weeks
                - M: Last 30 trading months
        """
        response = self.broker.fetch_ohlcv(
            symbol=str(ticker),
            timeframe=timeframe,
            adj_price=adj_price
        )
        data = []
        for item in response.get("output2", []):
            dt = pd.to_datetime(item['stck_bsop_date'], format="%Y%m%d")

            parsed_item = {
                "ticker": ticker,
                "datetime": dt,
                "open": item.get('stck_oprc'),
                "high": item.get('stck_hgpr'),
                "low": item.get('stck_lwpr'),
                "close": item.get('stck_clpr'),
                "volume": item.get('acml_vol')
            }
            data.append(parsed_item)

        data = sorted(data, key=lambda x: x["datetime"])
        return data

    def get_stock_price_minute(self, ticker: str | int) -> dict:
        """
        Fetch today's 1-minute interval OHLCV (Open, High, Low, Close, Volume) data for the given ticker code.

        Args:
            ticker (str | int): 
                Stock ticker code (e.g., "005930" for Samsung Electronics).

        Returns:
            dict: 
                Today's 1-minute interval OHLCV stock price data.
        """
        response = self.broker.fetch_today_1m_ohlcv(ticker=str(ticker))
        data = []
        
        for item in response.get("output2", []):
            dt = item['stck_bsop_date'] + ' ' + item['stck_cntg_hour']
            dt_formatted = pd.to_datetime(dt, format="%Y%m%d %H%M%S")

            parsed_item = {
                "ticker": ticker,
                "datetime": dt_formatted,
                "open": item.get('stck_oprc'),
                "high": item.get('stck_hgpr'),
                "low": item.get('stck_lwpr'),
                "close": item.get('stck_prpr'),
                "volume": item.get('cntg_vol')
            }
            data.append(parsed_item)
        data = sorted(data, key=lambda x: x["datetime"])

        return data
