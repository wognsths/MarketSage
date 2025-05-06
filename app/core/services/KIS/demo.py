"""
demo.py
단일 실행 스크립트:
  python demo.py --stocks 삼성전자 005930 --tf 1d --market KOSPI
"""
import argparse, asyncio, pandas as pd
from .pipeline import fetch_and_save

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stocks", nargs="+", required=True, help="티커 또는 종목명 목록")
    ap.add_argument("--tf", default="1d", help="timeframe (e.g. 1d, 1m)")
    ap.add_argument("--opt", default="close", help="가격 필드(open/high/low/close/volume)")
    ap.add_argument("--market", default="KOSPI", help="정적 매핑 시장")
    args = ap.parse_args()

    df: pd.DataFrame = asyncio.run(
        fetch_and_save(
            stocks=args.stocks,
            timeframe=args.tf,
            option=args.opt,
            market=args.market,
        )
    )
    if len(df) > 0:
        print(df)

if __name__ == "__main__":
    main()
