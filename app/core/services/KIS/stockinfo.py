from app.core.services.KIS.broker import create_broker
from app.core.models.models import StockPrice
from datetime import datetime
import pandas as pd
from typing import Union, List


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

    def get_stock_price_today(self, ticker: Union[str, int]) -> StockPrice:
        """
        Fetch the current market price for the given ticker code (today).
        """
        response = self.broker.fetch_price(str(ticker))
        item = response.get("output", {})

        return StockPrice(
            ticker=str(ticker),
            datetime=pd.to_datetime(item.get('stck_bsop_date'), format="%Y%m%d"),
            open=item.get('stck_oprc'),
            high=item.get('stck_hgpr'),
            low=item.get('stck_lwpr'),
            close=item.get('stck_prpr'),
            volume=item.get('acml_vol')
        )

    def get_stock_price(self, ticker: Union[str, int], timeframe: str, adj_price: bool = True) -> List[StockPrice]:
        """
        Fetch historical OHLCV market price data for the given ticker code.
        """
        response = self.broker.fetch_ohlcv(
            symbol=str(ticker),
            timeframe=timeframe,
            adj_price=adj_price
        )

        data = []
        for item in response.get("output2", []):
            dt = pd.to_datetime(item['stck_bsop_date'], format="%Y%m%d")

            data.append(StockPrice(
                ticker=str(ticker),
                datetime=dt,
                open=item.get('stck_oprc'),
                high=item.get('stck_hgpr'),
                low=item.get('stck_lwpr'),
                close=item.get('stck_clpr'),
                volume=item.get('acml_vol')
            ))

        return sorted(data, key=lambda x: x.datetime)

    def get_stock_price_minute(self, ticker: Union[str, int]) -> List[StockPrice]:
        """
        Fetch today's 1-minute interval OHLCV (Open, High, Low, Close, Volume) data for the given ticker code.
        """
        response = self.broker.fetch_today_1m_ohlcv(str(ticker))
        data = []

        for item in response.get("output2", []):
            dt = item['stck_bsop_date'] + ' ' + item['stck_cntg_hour']
            dt_formatted = pd.to_datetime(dt, format="%Y%m%d %H%M%S")

            data.append(StockPrice(
                ticker=str(ticker),
                datetime=dt_formatted,
                open=item.get('stck_oprc'),
                high=item.get('stck_hgpr'),
                low=item.get('stck_lwpr'),
                close=item.get('stck_prpr'),
                volume=item.get('cntg_vol')
            ))

        return sorted(data, key=lambda x: x.datetime)