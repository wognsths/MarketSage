import os
import pandas as pd

class BaseData:
    DATA_DIR = "./data"

    def data(self) -> dict[str, pd.DataFrame]:
        data_dict = {}
        for filename in os.listdir(self.DATA_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(self.DATA_DIR, filename)
                key = os.path.splitext(filename)[0]
                df = pd.read_csv(filepath, encoding="utf-8")

                if key.lower() in {"kospi", "kosdaq"} and "ticker" in df.columns:
                    df["ticker"] = df["ticker"].astype(str).str.zfill(6)

                data_dict[key] = df
        return data_dict

stockbasedata = BaseData()