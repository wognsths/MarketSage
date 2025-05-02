from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict

class RemoteAgentAddressSettings(BaseSettings):
    REMOTE_AGENT_ADDRESS: Dict[str, str] = SettingsConfigDict(
        env_file="address.env",
        case_sensitive=True
        )

remote_agent_address_settings = RemoteAgentAddressSettings()