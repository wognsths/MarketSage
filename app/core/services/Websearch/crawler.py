import logging
import os
from typing import Optional, List
from bs4 import BeautifulSoup
from readability import Document
from playwright.async_api import async_playwright
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory to save downloaded PDFs
PDF_DIR = "./pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# Domains known to require JavaScript rendering
JS_HEAVY_DOMAINS = [
    "tradingview.com", "fnguide.com", "irgo.co.kr", "naver.com", "daum.net"
]

# Heuristics to detect Single Page Application (SPA) patterns
SPA_MARKERS = [
    ("div", {"id": "app"}),
    ("div", {"id": "root"}),
    ("div", {"data-reactroot": True}),
    ("html", {"ng-app": True}),
]

# Determine if a URL is likely to require JS rendering
def is_js_heavy(url: str) -> bool:
    return any(domain in url for domain in JS_HEAVY_DOMAINS)

# Check HTML content for SPA markers
def looks_like_spa(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    for tag, attrs in SPA_MARKERS:
        if soup.find(tag, attrs=attrs):
            return True
    return False

# Basic text extraction using BeautifulSoup
async def fetch_page_text(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            if looks_like_spa(resp.text):
                logger.info(f"Detected SPA structure in {url}")
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.warning(f"[BS4 Fetch Error] {url}: {e}")
        return None

# Readable content extraction using Readability algorithm
async def fetch_readable_text(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            if looks_like_spa(resp.text):
                logger.info(f"Detected SPA structure in {url}")
                return None
            doc = Document(resp.text)
            return doc.summary(html=False)
    except Exception as e:
        logger.warning(f"[Readability Fetch Error] {url}: {e}")
        return None

# JavaScript-rendered page fetching via Playwright
async def fetch_js_rendered_text(url: str) -> Optional[str]:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=15000)
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                return soup.get_text(separator="\n", strip=True)
            finally:
                await browser.close()
    except Exception as e:
        logger.warning(f"[Playwright Error] {url}: {e}")
        return None

# Extract PDF file links from a webpage
async def extract_pdf_links(url: str) -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            pdfs = [link["href"] for link in soup.find_all("a", href=True) if link["href"].endswith(".pdf")]
            # Convert to absolute URLs if needed
            base_url = str(resp.url)
            full_links = [link if link.startswith("http") else base_url.rstrip("/") + "/" + link.lstrip("/") for link in pdfs]
            return full_links
    except Exception as e:
        logger.warning(f"[PDF Extraction Error] {url}: {e}")
        return []

# Download a PDF and save it to local storage
async def download_pdf(pdf_url: str, filename: Optional[str] = None) -> str:
    try:
        filename = filename or pdf_url.split("/")[-1]
        save_path = os.path.join(PDF_DIR, filename)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(resp.content)
        logger.info(f"PDF downloaded: {save_path}")
        return save_path
    except Exception as e:
        logger.warning(f"[PDF Download Error] {pdf_url}: {e}")
        return ""

# Main function to intelligently fetch page text using various strategies
async def smart_fetch(url: str) -> str:
    logger.info(f"▶ Start fetching: {url}")

    # First try Playwright for known JS-heavy domains
    if is_js_heavy(url):
        logger.info("Known JS-heavy domain. Trying Playwright first...")
        result = await fetch_js_rendered_text(url)
        if result and len(result.strip()) > 300:
            return result

    # Fallback to lightweight text-based methods
    for method in [fetch_readable_text, fetch_page_text]:
        result = await method(url)
        if result and len(result.strip()) > 300:
            return result

    # Final fallback to Playwright
    logger.info("Switching to Playwright as fallback...")
    result = await fetch_js_rendered_text(url)
    if result and len(result.strip()) > 300:
        return result

    logger.error(f"Failed to extract text from {url}")
    return "[No content extracted]"
