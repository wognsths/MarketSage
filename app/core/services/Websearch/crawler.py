import logging, os, asyncio, httpx
from typing import Optional, List
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urljoin
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PDF_DIR = "./pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

JS_HEAVY_DOMAINS = ["tradingview.com", "fnguide.com", "irgo.co.kr", "naver.com", "daum.net"]
SPA_MARKERS = [("div", {"id": "app"}), ("div", {"id": "root"}), ("div", {"data-reactroot": True}), ("html", {"ng-app": True})]

def is_js_heavy(url: str) -> bool:
    return any(d in url for d in JS_HEAVY_DOMAINS)

def looks_like_spa(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    return any(soup.find(tag, attrs=a) for tag, a in SPA_MARKERS)

async def fetch_page_text(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            r.raise_for_status()
            if looks_like_spa(r.text):
                return None
            return BeautifulSoup(r.text, "html.parser").get_text("\n", strip=True)
    except Exception as e:
        logger.warning(f"[BS4] {url} {e}")
        return None

async def fetch_readable_text(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            r.raise_for_status()
            if looks_like_spa(r.text):
                return None
            return Document(r.text).summary(html=False)
    except Exception as e:
        logger.warning(f"[Readability] {url} {e}")
        return None

async def fetch_js_rendered_text(url: str) -> Optional[str]:
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            pge = await b.new_page()
            await pge.goto(url, timeout=20000)
            html = await pge.content()
            await b.close()
            return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    except Exception as e:
        logger.warning(f"[Playwright] {url} {e}")
        return None

async def download_pdf(url: str, name: Optional[str] = None) -> str:
    try:
        name = name or url.split("/")[-1].split("?")[0]
        path = os.path.join(PDF_DIR, name)
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(url)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        logger.info(f"[PDF] {path}")
        return path
    except Exception as e:
        logger.warning(f"[PDF DL] {url} {e}")
        return ""

async def _extract_pdf_links_static(url: str) -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            return [urljoin(str(r.url), a["href"]) for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf")]
    except Exception:
        return []

async def _extract_pdf_links_js(url: str) -> List[str]:
    links = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            pg = await b.new_page()
            await pg.goto(url, timeout=20000)
            for a in await pg.query_selector_all("a[href$='.pdf']"):
                href = await a.get_attribute("href")
                if href:
                    links.append(urljoin(url, href))
            await b.close()
    except Exception as e:
        logger.warning(f"[PDF JS] {url} {e}")
    return list(dict.fromkeys(links))

async def extract_pdf_links(url: str, *, auto_download: bool = True, limit: int = 5) -> List[str]:
    links = await _extract_pdf_links_static(url)
    if not links:
        links = await _extract_pdf_links_js(url)
    if not auto_download:
        return links
    paths = []
    for l in links[:limit]:
        pth = await download_pdf(l)
        if pth:
            paths.append(pth)
    return paths

async def smart_fetch(url: str) -> str:
    if is_js_heavy(url):
        t = await fetch_js_rendered_text(url)
        if t and len(t.strip()) > 300:
            return t
    for fn in (fetch_readable_text, fetch_page_text):
        t = await fn(url)
        if t and len(t.strip()) > 300:
            return t
    t = await fetch_js_rendered_text(url)
    return t if t else "[No content extracted]"
