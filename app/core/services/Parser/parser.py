from pydantic import BaseModel
from typing import Optional, Tuple, List
import requests
import json
from bs4 import BeautifulSoup  # for parsing HTML
from app.core.settings.upstage import upstagesettings

class DocumentContent(BaseModel):
    html: str
    markdown: Optional[str] = None
    text: Optional[str] = None

class ParsedDocument(BaseModel):
    paragraphs: List[str]
    tables: List[List[List[str]]]  # Table: list of rows -> list of cells

class UPSTAGEparser:
    def __init__(self):
        self.API_KEY, self.API_ENDPOINT = upstagesettings.api_info
        self.HEADERS = {
            "Authorization": f"Bearer {self.API_KEY}"
        }

    def extract(self, file, force_ocr: bool = True) -> Tuple[Optional[DocumentContent], Optional[Exception]]:
        """
        Extract structured content (HTML/Markdown/Text) from a PDF file using Upstage Document Parse API.
        """
        files = {
            "document": ("document.pdf", file.read(), "application/pdf")
        }
        data = {
            "ocr": "force" if force_ocr else "auto",
            "coordinates": "true",
            "chart_recognition": "true",
            "output_formats": json.dumps(["html", "markdown", "text"]),
            "model": "document-parse",
            "base64_encoding": json.dumps([])
        }

        try:
            response = requests.post(
                url=self.API_ENDPOINT,
                headers=self.HEADERS,
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            content = result.get("content", {})
            return DocumentContent(
                html=content.get("html", "").strip(),
                markdown=content.get("markdown", "").strip(),
                text=content.get("text", "").strip()
            ), None

        except Exception as e:
            return None, e