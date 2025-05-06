from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field
from .common import MissingAPIKeyError

load_dotenv()

class GoogleSearchSettings(BaseSettings):
    GOOGLE_SEARCH_API_KEY: str = Field(..., env="GOOGLE_SEARCH_API_KEY")
    GOOGLE_CX_ID: str = Field(..., env="GOOGLE_CX_ID")
    GOOGLE_ENDPOINT: str = "https://www.googleapis.com/customsearch/v1"

    @property
    def api_info(self):
        if not (self.GOOGLE_SEARCH_API_KEY and self.GOOGLE_CX_ID):
            raise MissingAPIKeyError(missing_keys="GOOGLE_API_KEY or GOOGLE_CX_ID")
        return self.GOOGLE_SEARCH_API_KEY, self.GOOGLE_CX_ID, self.GOOGLE_ENDPOINT

googlesettings = GoogleSearchSettings()
