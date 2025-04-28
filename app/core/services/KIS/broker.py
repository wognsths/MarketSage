import mojito
from app.core.settings.koreainvest import kissettings

def create_broker(mock: bool = False) -> mojito.KoreaInvestment:
    broker = mojito.KoreaInvestment(
        **kissettings.api_info,
        mock=mock
    )
    return broker