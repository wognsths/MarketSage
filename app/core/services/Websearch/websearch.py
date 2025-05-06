import httpx
from app.core.settings.googlesearch import googlesettings
from app.core.models.models import SearchResult
from typing import Literal, List


class GoogleSearchAPI:
    def __init__(self):
        self.GOOGLE_API_KEY, self.CX_ID, _ = googlesettings.api_info
        self.BASE_URL = "https://www.googleapis.com/customsearch/v1"

    async def web_search(self, query: str, mkt: str = "us") -> List[SearchResult]:
        params = {
            "key": self.GOOGLE_API_KEY,
            "cx": self.CX_ID,
            "q": query,
            "gl": mkt,
            "num": 10,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                return self._parse_result(response.json(), type="web")
        except httpx.HTTPStatusError as e:
            print(f"[Web Search Error] Status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"[Web Search Request Failed] {e}")
        return []

    async def news_search(self, query: str, mkt: str = "us") -> List[SearchResult]:
        params = {
            "key": self.GOOGLE_API_KEY,
            "cx": self.CX_ID,
            "q": f"{query} site:news.google.com",
            "gl": mkt,
            "num": 10,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                return self._parse_result(response.json(), type="news")
        except httpx.HTTPStatusError as e:
            print(f"[News Search Error] Status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"[News Search Request Failed] {e}")
        return []

    def _parse_result(self, data: dict, type: Literal["web", "news"]) -> List[SearchResult]:
        results = []
        for item in data.get("items", []):
            results.append(
                SearchResult(
                    type=type,
                    title=item.get("title"),
                    url=item.get("link"),
                    snippet=item.get("snippet"),
                    provider="Google"
                )
            )
        return results
