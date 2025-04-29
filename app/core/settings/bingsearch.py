from pydantic_settings import BaseSettings
from pydantic import Field
from app.common.types import MissingAPIKeyError

class BINGSEARCHsettings(BaseSettings):
    BING_API_KEY: str = Field(..., env="BING_API_KEY")
    BING_ENDPOINT: str = "https://api.bing.microsoft.com"

    @property
    def api_info(self) -> str:
        if not self.BING_API_KEY:
            raise MissingAPIKeyError(missing_keys=self.BING_API_KEY)

        return self.BING_API_KEY, self.BING_ENDPOINT

bingsettings = BINGSEARCHsettings()