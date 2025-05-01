import os
import pandas as pd

class StockBaseData:
    DATA_DIR = "./data"

    def data(self) -> dict[str, pd.DataFrame]:
        data_dict = {}
        for filename in os.listdir(self.DATA_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(self.DATA_DIR, filename)
                key = os.path.splitext(filename)[0]
                data_dict[key] = pd.read_csv(filepath, encoding="utf-8")
        return data_dict
    
stockbasedata = StockBaseData()