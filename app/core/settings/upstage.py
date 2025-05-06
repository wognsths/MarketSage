from pydantic_settings import BaseSettings
from pydantic import Field
from .common import MissingAPIKeyError
from dotenv import load_dotenv

load_dotenv()

class UPSTAGEsettings(BaseSettings):
    UPSTAGE_API_KEY: str = Field(..., env="UPSTAGE_API_KEY")
    API_ENDPOINT: str = "https://api.upstage.ai/v1/document-digitization"

    @property
    def api_info(self) -> str:
        if not self.UPSTAGE_API_KEY:
            raise MissingAPIKeyError(missing_keys=self.UPSTAGE_API_KEY)

        return self.UPSTAGE_API_KEY, self.API_ENDPOINT

upstagesettings = UPSTAGEsettings()