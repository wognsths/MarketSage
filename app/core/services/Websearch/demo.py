import asyncio, json
from .pipeline import search_and_collect

async def demo():
    res = await search_and_collect("삼성전자 IR 자료", top_k=3)
    print(json.dumps(res, ensure_ascii=False, indent=2))

asyncio.run(demo())
