import requests
import json
from bs4 import BeautifulSoup
from app.core.settings.upstage import upstagesettings
from app.core.models.models import DocumentContent, ParsedDocument

# ---- Constants ----
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = 1024 ** 2 * MAX_FILE_SIZE_MB

# ---- Helpers ----
def get_mime_type(filename: str) -> Optional[str]:
    """Return MIME type based on file extension"""
    ext = filename.lower().split('.')[-1]
    
    mapping = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "heic": "image/heic",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "hwp": "application/x-hwp",
        "hwpx": "application/vnd.hancom.hwpx"
    }
    
    return mapping.get(ext, None)

def is_document_file(filename: str) -> bool:
    """Return True if the file is considered a document"""
    ext = filename.lower().split('.')[-1]
    return ext in {"pdf", "docx", "pptx", "xlsx", "hwp", "hwpx"}

# ---- Main Parser Class ----
class UPSTAGEparser:
    def __init__(self):
        self.API_KEY, self.API_ENDPOINT = upstagesettings.api_info
        self.HEADERS = {
            "Authorization": f"Bearer {self.API_KEY}"
        }

    def _pdf_extract(self, file, force_ocr: bool = True) -> Tuple[Optional[DocumentContent], Optional[Exception]]:
        """Extract content from a PDF file"""
        files = {
            "document": ("document.pdf", file.read(), "application/pdf")
        }
        return self._call_api(files, force_ocr)

    def _image_extract(self, file, mime_type: str, force_ocr: bool = True) -> Tuple[Optional[DocumentContent], Optional[Exception]]:
        """Extract content from an image or document file"""
        files = {
            "document": ("document", file.read(), mime_type)
        }
        return self._call_api(files, force_ocr)

    def _call_api(self, files, force_ocr: bool) -> Tuple[Optional[DocumentContent], Optional[Exception]]:
        """Call the UPSTAGE document parsing API"""
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
        except requests.exceptions.RequestException as e:
            return None, Exception(f"HTTP request failed: {e}")
        except Exception as e:
            return None, e

    def extract(self, file, filename: str, force_ocr: Optional[bool] = None) -> Tuple[Optional[DocumentContent], Optional[Exception]]:
        """
        Universal extractor. Supports PDFs, images, office documents, and HWP/HWPX files.
        """
        # Step 1: Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE_BYTES:
            return None, Exception(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit ({file_size / (1024*1024):.2f}MB)")

        # Step 2: Determine MIME type
        mime_type = get_mime_type(filename)

        if mime_type is None:
            return None, Exception(f"Unsupported file format: {filename}")

        # Step 3: Set OCR mode automatically
        if force_ocr is None:
            # Disable OCR for document files, enable OCR for images
            force_ocr = not is_document_file(filename)

        # Step 4: Perform extraction
        if mime_type.startswith("application/pdf"):
            return self._pdf_extract(file, force_ocr=force_ocr)
        else:
            return self._image_extract(file, mime_type=mime_type, force_ocr=force_ocr)

    def parse(self, html_content: str) -> ParsedDocument:
        """Parse extracted HTML content into structured paragraphs and tables"""
        soup = BeautifulSoup(html_content, "html.parser")

        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]

        tables = []
        for table_tag in soup.find_all("table"):
            table = []
            for row in table_tag.find_all("tr"):
                cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                table.append(cells)
            tables.append(table)

        return ParsedDocument(
            paragraphs=paragraphs,
            tables=tables
        )
