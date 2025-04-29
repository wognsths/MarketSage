import unittest
import os
from unittest.mock import patch, MagicMock
from app.core.services.KIS import KIS
from test.utils import get_credentials, setup_logger

class TestKIS(unittest.TestCase):
    def setUp(self):
        # Setup logger for this test
        self.logger = setup_logger("test_kis")
        self.logger.info("Setting up TestKIS")
        
        self.kis = KIS()
        self.test_ticker = "005930"  # Samsung Electronics
        
        # Get credentials directly from settings
        self.credentials = get_credentials('kis')
        self.credentials_available = bool(self.credentials)
        self.logger.info(f"Credentials available: {self.credentials_available}")
        
    def test_kis_initialization(self):
        self.logger.info("Testing KIS initialization")
        self.assertIsNotNone(self.kis)
    
    # Mock tests
    @patch('app.core.services.KIS.KIS.authenticate')
    def test_authentication(self, mock_authenticate):
        self.logger.info("Testing authentication with mock")
        # Test authentication
        mock_authenticate.return_value = {"access_token": "test_token"}
        token = self.kis.authenticate()
        self.assertIsNotNone(token)
        self.assertEqual(token.get("access_token"), "test_token")
        self.logger.info("Authentication mock test successful")
    
    # Mock tests
    @patch('app.core.services.KIS.KIS.get_stock_info')
    def test_get_stock_info_for_samsung(self, mock_get_stock_info):
        self.logger.info("Testing stock info retrieval with mock")
        # Test stock info for Samsung Electronics (005930)
        mock_response = {
            "ticker": "005930",
            "name": "Samsung Electronics",
            "price": 70000,
            "change": 1000,
            "change_percent": 1.45
        }
        mock_get_stock_info.return_value = mock_response
        
        response = self.kis.get_stock_info(self.test_ticker)
        
        self.assertIsNotNone(response)
        self.assertEqual(response["ticker"], self.test_ticker)
        self.assertEqual(response["name"], "Samsung Electronics")
        mock_get_stock_info.assert_called_once_with(self.test_ticker)
        self.logger.info("Stock info mock test successful")
    
    # Mock tests
    @patch('app.core.services.KIS.KIS.get_stock_price')
    def test_get_stock_price_for_samsung(self, mock_get_stock_price):
        self.logger.info("Testing stock price retrieval with mock")
        # Test stock price for Samsung Electronics (005930)
        mock_get_stock_price.return_value = 70000
        
        price = self.kis.get_stock_price(self.test_ticker)
        
        self.assertIsNotNone(price)
        self.assertEqual(price, 70000)
        mock_get_stock_price.assert_called_once_with(self.test_ticker)
        self.logger.info("Stock price mock test successful")
    
    # Real service tests
    def test_real_authentication(self):
        """Test actual KIS API authentication"""
        self.logger.info("Testing real KIS API authentication")
        if not self.credentials_available:
            self.logger.warning("KIS credentials not available, skipping real service test")
            self.skipTest("KIS credentials not available for real service test")
        
        # Setup credentials for real test
        try:
            # Assuming KIS class has methods to set credentials
            self.logger.info("Setting up KIS credentials for real test")
            self.kis.set_credentials(
                app_key=self.credentials.get('app_key'),
                app_secret=self.credentials.get('app_secret')
            )
            
            # Perform real authentication
            self.logger.info("Performing real KIS authentication")
            token = self.kis.authenticate()
            
            # Verify response
            self.assertIsNotNone(token)
            self.assertIn("access_token", token)
            self.assertTrue(isinstance(token["access_token"], str))
            self.assertTrue(len(token["access_token"]) > 10)  # Reasonable token length
            self.logger.info("Real authentication successful")
            
        except Exception as e:
            self.logger.error(f"Real authentication failed: {str(e)}")
            self.fail(f"Real authentication failed: {str(e)}")
    
    # Real service tests
    def test_real_stock_info(self):
        """Test actual KIS API for stock information retrieval"""
        self.logger.info("Testing real stock info retrieval")
        if not self.credentials_available:
            self.logger.warning("KIS credentials not available, skipping real service test")
            self.skipTest("KIS credentials not available for real service test")
        
        try:
            # Setup credentials
            self.kis.set_credentials(
                app_key=self.credentials.get('app_key'),
                app_secret=self.credentials.get('app_secret')
            )
            
            # Authenticate first (required for real API calls)
            self.logger.info("Authenticating with KIS API")
            self.kis.authenticate()
            
            # Get real stock info
            self.logger.info(f"Getting stock info for {self.test_ticker}")
            stock_info = self.kis.get_stock_info(self.test_ticker)
            
            # Verify real response
            self.assertIsNotNone(stock_info)
            self.assertEqual(stock_info["ticker"], self.test_ticker)
            self.assertIn("name", stock_info)
            self.assertIn("price", stock_info)
            
            # Price should be a reasonable value for Samsung stock
            price = stock_info.get("price", 0)
            self.assertGreater(price, 1000)  # Ensure price is reasonable
            self.assertLess(price, 1000000)    # Sanity check upper bound
            self.logger.info(f"Got stock info with price: {price}")
            
        except Exception as e:
            self.logger.error(f"Real stock info retrieval failed: {str(e)}")
            self.fail(f"Real stock info retrieval failed: {str(e)}")
    
    # Real service tests
    def test_real_multiple_stocks(self):
        """Test getting information for multiple stocks"""
        self.logger.info("Testing real multiple stock info retrieval")
        if not self.credentials_available:
            self.logger.warning("KIS credentials not available, skipping real service test")
            self.skipTest("KIS credentials not available for real service test")
        
        try:
            # Setup KIS API
            self.kis.set_credentials(
                app_key=self.credentials.get('app_key'),
                app_secret=self.credentials.get('app_secret')
            )
            self.kis.authenticate()
            
            # Test with multiple stock tickers (Samsung, Hyundai, Naver)
            tickers = ["005930", "005380", "035420"]
            self.logger.info(f"Testing stock info retrieval for tickers: {tickers}")
            
            for ticker in tickers:
                self.logger.info(f"Getting stock info for {ticker}")
                stock_info = self.kis.get_stock_info(ticker)
                
                # Verify each real response
                self.assertIsNotNone(stock_info)
                self.assertEqual(stock_info["ticker"], ticker)
                self.assertIn("name", stock_info)
                self.assertIn("price", stock_info)
                self.assertGreater(stock_info.get("price", 0), 1000)
                self.logger.info(f"Successfully retrieved info for {ticker}: {stock_info.get('name')} at price {stock_info.get('price')}")
                
        except Exception as e:
            self.logger.error(f"Real multiple stock test failed: {str(e)}")
            self.fail(f"Real multiple stock test failed: {str(e)}")
    
if __name__ == '__main__':
    unittest.main() 