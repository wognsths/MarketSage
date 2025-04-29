import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

SUSPICIOUS_TAGS = [
    "/JavaScript",
    "/JS",
    "/Launch",
    "/EmbeddedFile",
    "/AA",
    "/OpenAction",
    "/SubmitForm"
]

def scan_pdf_keywords(filepath: str) -> bool:
    try:
        filepath = Path(filepath)
        with open(filepath, "rb") as f:
            content = f.read().decode("latin-1", errors="ignore")
            for tag in SUSPICIOUS_TAGS:
                if tag in content:
                    logger.warning(f"[PDFID] Suspicious tag found: {tag} in {filepath.name}")
                    return False
        return True
    except Exception as e:
        logger.warning(f"[PDF Scan Error] {filepath}: {e}")
        return False
