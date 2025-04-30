from app.core.services.KIS.stockinfo import StockInfoFetcher
import pandas as pd
from typing import Union, List

stockinfo = StockInfoFetcher()

def ticker_name_translater(stock: str):
    #TODO
    pass


def get_stockinfo(stocks: List[Union[str, int]], timeframe: str, adj_price: bool = True, option: str = "close") -> pd.DataFrame:
    for stock in stocks:
        if isinstance():
            stockinfo.get_stock_price(ticker=ticker_name_translater(stock))