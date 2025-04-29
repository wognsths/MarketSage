import unittest
import os
import io
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.core.services.Parser.parser import UPSTAGEparser
from app.core.models.models import DocumentContent, ParsedDocument
from test.utils import get_credentials, setup_logger

class TestParser(unittest.TestCase):
    def setUp(self):
        # Setup logger for this test
        self.logger = setup_logger("test_parser")
        self.logger.info("Setting up TestParser")
        
        # Get credentials directly from settings
        self.credentials = get_credentials('upstage')
        self.credentials_available = bool(self.credentials)
        
        # Create parser with default or settings credentials
        self.parser = UPSTAGEparser()
        
        # Override credentials if available
        if self.credentials_available:
            if 'api_key' in self.credentials and 'api_endpoint' in self.credentials:
                # Explicitly set parser's values with values from upstagesettings
                # (parser might already have same values from init, but setting for test clarity)
                self.parser.API_KEY = self.credentials['api_key']
                self.parser.API_ENDPOINT = self.credentials['api_endpoint']
                self.parser.HEADERS = {"Authorization": f"Bearer {self.parser.API_KEY}"}
                self.logger.info("Using credentials from settings")
            
        # Create test directory and files
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_dir, exist_ok=True)
            
        # Create test text file
        self.text_file_path = os.path.join(self.test_dir, "sample.txt")
        with open(self.text_file_path, "w") as f:
            f.write("This is a test document.\nIt has multiple lines.\nThird line with information.")
        
        # Create test HTML file
        self.html_file_path = os.path.join(self.test_dir, "sample.html")
        with open(self.html_file_path, "w") as f:
            f.write("""
            <html>
            <body>
                <p>First paragraph with important content.</p>
                <p>Second paragraph with details.</p>
                <table>
                    <tr><th>Header 1</th><th>Header 2</th></tr>
                    <tr><td>Data 1</td><td>Data 2</td></tr>
                    <tr><td>Data 3</td><td>Data 4</td></tr>
                </table>
            </body>
            </html>
            """)
        
    def tearDown(self):
        # Clean up test files
        if os.path.exists(self.text_file_path):
            os.remove(self.text_file_path)
        if os.path.exists(self.html_file_path):
            os.remove(self.html_file_path)
        self.logger.info("Test cleanup complete")
        
    def test_parser_initialization(self):
        self.logger.info("Testing parser initialization")
        self.assertIsNotNone(self.parser)
        self.assertIsNotNone(self.parser.API_KEY)
        self.assertIsNotNone(self.parser.API_ENDPOINT)
        self.assertIn("Authorization", self.parser.HEADERS)
    
    # Mock tests
    @patch('app.core.services.Parser.parser.requests.post')
    def test_pdf_extract_mocked(self, mock_post):
        self.logger.info("Testing PDF extraction with mock")
        # Setup mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": {
                "html": "<p>Test PDF content</p>",
                "markdown": "Test PDF content",
                "text": "Test PDF content"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create dummy PDF file in memory
        dummy_pdf = io.BytesIO(b"%PDF-1.5 dummy content")
        
        # Test PDF extraction
        content, error = self.parser._pdf_extract(dummy_pdf, force_ocr=True)
        
        # Verify results
        self.assertIsNone(error)
        self.assertIsInstance(content, DocumentContent)
        self.assertEqual(content.text, "Test PDF content")
        self.assertEqual(content.html, "<p>Test PDF content</p>")
        self.assertEqual(content.markdown, "Test PDF content")
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["headers"], self.parser.HEADERS)
        self.logger.info("PDF extraction mock test successful")
    
    @patch('app.core.services.Parser.parser.requests.post')
    def test_image_extract_mocked(self, mock_post):
        self.logger.info("Testing image extraction with mock")
        # Setup mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": {
                "html": "<p>Test image content</p>",
                "markdown": "Test image content",
                "text": "Test image content"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create dummy image file in memory
        dummy_image = io.BytesIO(b"dummy image content")
        
        # Test image extraction
        content, error = self.parser._image_extract(dummy_image, mime_type="image/jpeg", force_ocr=True)
        
        # Verify results
        self.assertIsNone(error)
        self.assertIsInstance(content, DocumentContent)
        self.assertEqual(content.text, "Test image content")
        
        # Verify API call
        mock_post.assert_called_once()
        self.logger.info("Image extraction mock test successful")
    
    @patch('app.core.services.Parser.parser.requests.post')
    def test_extract_pdf_mocked(self, mock_post):
        self.logger.info("Testing extract method with mock")
        # Setup mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": {
                "html": "<p>Test content</p>",
                "markdown": "Test content",
                "text": "Test content"
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create dummy PDF file in memory
        dummy_file = io.BytesIO(b"%PDF-1.5 dummy content")
        
        # Test extract method
        content, error = self.parser.extract(dummy_file, "document.pdf")
        
        # Verify results
        self.assertIsNone(error)
        self.assertIsInstance(content, DocumentContent)
        self.assertEqual(content.text, "Test content")
        self.logger.info("Extract method mock test successful")
    
    def test_parse_html(self):
        self.logger.info("Testing HTML parsing")
        # Read sample HTML file
        with open(self.html_file_path, 'r') as f:
            html_content = f.read()
        
        # Parse HTML content
        parsed_doc = self.parser.parse(html_content)
        
        # Verify parsing results
        self.assertIsInstance(parsed_doc, ParsedDocument)
        self.assertEqual(len(parsed_doc.paragraphs), 2)
        self.assertEqual(parsed_doc.paragraphs[0], "First paragraph with important content.")
        self.assertEqual(len(parsed_doc.tables), 1)
        self.assertEqual(parsed_doc.tables[0][0][0], "Header 1")
        self.assertEqual(parsed_doc.tables[0][1][1], "Data 2")
        self.logger.info("HTML parsing test successful")
    
    def test_get_mime_type(self):
        self.logger.info("Testing mime type detection")
        from app.core.services.Parser.parser import get_mime_type
        
        # Test various file extensions
        self.assertEqual(get_mime_type("document.pdf"), "application/pdf")
        self.assertEqual(get_mime_type("image.jpg"), "image/jpeg")
        self.assertEqual(get_mime_type("document.docx"), 
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertIsNone(get_mime_type("unknown.xyz"))
        self.logger.info("Mime type detection test successful")
    
    def test_is_document_file(self):
        self.logger.info("Testing document file detection")
        from app.core.services.Parser.parser import is_document_file
        
        # Test document detection
        self.assertTrue(is_document_file("document.pdf"))
        self.assertTrue(is_document_file("document.docx"))
        self.assertTrue(is_document_file("document.hwp"))
        self.assertFalse(is_document_file("image.jpg"))
        self.assertFalse(is_document_file("unknown.txt"))
        self.logger.info("Document file detection test successful")
    
    # Real service tests
    def test_real_extract_and_parse(self):
        """Test actual extraction and parsing with the UPSTAGE API"""
        self.logger.info("Testing real extraction with UPSTAGE API")
        if not self.credentials_available:
            self.logger.warning("UPSTAGE API credentials not available, skipping real service test")
            self.skipTest("UPSTAGE API credentials not available for real service test")
        
        try:
            # Setup test PDF file path
            test_pdf_path = os.path.join(self.test_dir, "test_document.pdf")
            
            # Skip if no real PDF file exists
            if not os.path.exists(test_pdf_path):
                self.logger.warning("No test PDF available, skipping real API test")
                self.skipTest("No test PDF available for real API testing")
            
            with open(test_pdf_path, 'rb') as file:
                # Extract content from PDF
                self.logger.info("Calling UPSTAGE API to extract PDF content")
                content, error = self.parser.extract(file, "test_document.pdf", force_ocr=True)
                
                # Check extraction success
                if error:
                    self.logger.error(f"API extraction failed: {error}")
                    self.fail(f"API extraction failed: {error}")
                
                self.assertIsNotNone(content)
                self.assertTrue(isinstance(content, DocumentContent))
                self.assertTrue(len(content.html) > 0)
                self.logger.info("API extraction successful")
                
                # Parse extracted HTML
                self.logger.info("Parsing extracted HTML content")
                parsed_doc = self.parser.parse(content.html)
                
                self.assertIsNotNone(parsed_doc)
                self.assertTrue(isinstance(parsed_doc, ParsedDocument))
                self.assertTrue(len(parsed_doc.paragraphs) > 0)
                self.logger.info(f"Parsed document has {len(parsed_doc.paragraphs)} paragraphs and {len(parsed_doc.tables)} tables")
                
        except Exception as e:
            self.logger.error(f"Real extraction test failed: {str(e)}")
            self.fail(f"Real extraction test failed: {str(e)}")
    
if __name__ == '__main__':
    unittest.main() 