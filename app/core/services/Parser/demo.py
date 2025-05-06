import asyncio
from .pipeline import parse_target

if __name__ == "__main__":
    asyncio.run(parse_target("2024_1Q_conference_kor.pdf"))