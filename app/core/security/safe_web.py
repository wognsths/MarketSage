import logging
import os
from urllib.parse import urlparse
import re
import httpx
import base64
from typing import Optional

logger = logging.getLogger(__name__)

# --- Basic Configuration ---
SAFE_DOMAINS = [
    "samsung.com", "naver.com", "fn-guide.com", "dart.fss.or.kr"
]

BLACKLIST_EXTENSIONS = [".exe", ".bat", ".js", ".zip", ".sh"]
DANGEROUS_CONTENT_TYPES = ["application/javascript", "application/x-msdownload", "application/x-sh"]

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", None)
VIRUSTOTAL_URL = "https://www.virustotal.com/api/v3/urls"

# --- URL Checking Utilities ---

def is_https_url(url: str) -> bool:
    """Check if the URL uses HTTPS."""
    return url.startswith("https://")

def is_domain_safe(url: str, whitelist: list[str] = SAFE_DOMAINS) -> bool:
    """Check if the URL's domain is in the whitelist."""
    parsed = urlparse(url)
    return any(domain in parsed.netloc for domain in whitelist)

def has_dangerous_extension(url: str) -> bool:
    """Check if the URL ends with a dangerous file extension."""
    return any(url.lower().endswith(ext) for ext in BLACKLIST_EXTENSIONS)

def has_dangerous_content_type(content_type: str) -> bool:
    """Check if the content type is flagged as dangerous."""
    return any(typ in content_type.lower() for typ in DANGEROUS_CONTENT_TYPES)

def is_url_safe_basic(url: str) -> bool:
    """Basic safety check: HTTPS and file extension."""
    if not is_https_url(url):
        logger.warning(f"❌ [Basic] URL is not HTTPS: {url}")
        return False
    if has_dangerous_extension(url):
        logger.warning(f"❌ [Basic] URL has dangerous extension: {url}")
        return False
    return True

def filter_safe_urls(urls: list[str]) -> list[str]:
    """Filter a list of URLs to keep only the safe ones."""
    return [url for url in urls if is_url_safe_basic(url) and is_domain_safe(url)]

def sanitize_filename(name: str) -> str:
    """Sanitize a filename by replacing forbidden characters."""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name[:200]

# --- VirusTotal Check ---

async def check_url_virustotal(url: str) -> Optional[bool]:
    """
    Check URL reputation using VirusTotal.
    - Returns True if clean, False if malicious, None if skipped (no API key).
    """
    if not VIRUSTOTAL_API_KEY:
        logger.info("[VT] API Key not set. Skipping VirusTotal check.")
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            encoded_url = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            headers = {"x-apikey": VIRUSTOTAL_API_KEY}
            resp = await client.get(f"{VIRUSTOTAL_URL}/{encoded_url}", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            stats = data["data"]["attributes"]["last_analysis_stats"]

            if stats["malicious"] == 0 and stats["suspicious"] == 0:
                return True
            else:
                logger.warning(f"[VT] Malicious or suspicious: {url}")
                return False
    except Exception as e:
        logger.warning(f"[VT] Error while checking {url}: {e}")
        return None

# --- Comprehensive Safety Check ---

async def is_url_globally_safe(url: str) -> bool:
    """
    Perform a comprehensive safety check for a given URL.
    - Always checks HTTPS, extension, and domain.
    - VirusTotal is checked only if API key is configured.
    """
    basic_safe = is_url_safe_basic(url)
    domain_safe = is_domain_safe(url)

    if not (basic_safe and domain_safe):
        return False

    vt_result = await check_url_virustotal(url)
    if vt_result is False:
        return False  # Clearly unsafe
    # vt_result is None → VT check skipped, rely on basic checks
    return True
