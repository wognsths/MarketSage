from pydantic_settings import BaseSettings
from pydantic import Field
from .common import MissingAPIKeyError
from dotenv import load_dotenv

load_dotenv()

class KISsettings(BaseSettings):
    KIS_API_KEY: str = Field(..., env="KIS_API_KEY")
    KIS_API_SECRET: str = Field(..., env="KIS_API_SECRET")
    KIS_ACC_NO: str = Field(..., env="KIS_ACC_NO")

    @property
    def api_info(self) -> dict:
        missing_api_keys = [
            key for key, value in {
                "KIS_API_KEY": self.KIS_API_KEY,
                "KIS_API_SECRET": self.KIS_API_SECRET,
                "KIS_ACC_NO": self.KIS_ACC_NO
            }.items() if not value
        ]
        if missing_api_keys:
            raise MissingAPIKeyError(missing_keys=missing_api_keys)

        return {
            "api_key": self.KIS_API_KEY,
            "api_secret": self.KIS_API_SECRET,
            "acc_no": self.KIS_ACC_NO
        }

kissettings = KISsettings()
