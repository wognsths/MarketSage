import httpx
from app.core.settings.bingsearch import bingsettings
from app.core.models.models import SearchResult
from typing import Literal, List


class BingAPI:
    def __init__(self):
        self.BING_API_KEY, self.BING_ENDPOINT = bingsettings.api_info
        self.HEADERS = {"Ocp-Apim-Subscription-Key": self.BING_API_KEY}

    async def web_search(self, query: str, mkt: str = "en-US") -> List[SearchResult]:
        url = f"{self.BING_ENDPOINT}/v7.0/search"
        params = {"q": query, "mkt": mkt}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.HEADERS, params=params)
                response.raise_for_status()
                return self._parse_result(response.json(), type="web")
        except httpx.HTTPStatusError as e:
            print(f"[Web Search Error] Status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"[Web Search Request Failed] {e}")
        return []

    async def news_search(self, query: str, mkt: str = "en-US") -> List[SearchResult]:
        url = f"{self.BING_ENDPOINT}/v7.0/news/search"
        params = {"q": query, "mkt": mkt}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.HEADERS, params=params)
                response.raise_for_status()
                return self._parse_result(response.json(), type="news")
        except httpx.HTTPStatusError as e:
            print(f"[News Search Error] Status {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"[News Search Request Failed] {e}")
        return []

    def _parse_result(self, data: dict, type: Literal["web", "news"]) -> List[SearchResult]:
        results = []

        if type == "web" and "webPages" in data:
            for item in data["webPages"]["value"]:
                results.append(SearchResult(
                    type="web",
                    title=item["name"],
                    url=item["url"],
                    snippet=item["snippet"],
                ))

        elif type == "news" and "value" in data:
            for item in data["value"]:
                results.append(SearchResult(
                    type="news",
                    title=item["name"],
                    url=item["url"],
                    snippet=item.get("description", ""),
                    provider=item.get("provider", [{}])[0].get("name", None)
                ))

        return results
