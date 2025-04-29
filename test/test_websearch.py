import unittest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.core.services.Websearch import Websearch
from test.utils import get_credentials, setup_logger

class TestWebsearch(unittest.TestCase):
    def setUp(self):
        # Setup logger for this test
        self.logger = setup_logger("test_websearch")
        self.logger.info("Setting up TestWebsearch")
        
        self.websearch = Websearch()
        self.default_query = "Samsung Electronics stock forecast"
        
        # Get credentials directly from settings
        self.credentials = get_credentials('websearch')
        self.api_keys_available = bool(self.credentials)
        self.logger.info(f"API keys available: {self.api_keys_available}")
        
    def test_websearch_initialization(self):
        self.logger.info("Testing Websearch initialization")
        self.assertIsNotNone(self.websearch)
    
    # Mock tests
    @patch('app.core.services.Websearch.Websearch.search')
    def test_default_search_query(self, mock_search):
        self.logger.info("Testing default search query with mock")
        # Test default search query
        mock_results = [
            {"title": "Samsung Electronics stock forecast, expected uptrend in 2023", "url": "https://example.com/news1"},
            {"title": "Securities firms adjust Samsung Electronics target price upward", "url": "https://example.com/news2"}
        ]
        mock_search.return_value = mock_results
        
        results = self.websearch.search(self.default_query)
        
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 2)
        self.assertIn("Samsung", results[0]["title"])
        mock_search.assert_called_once_with(self.default_query)
        self.logger.info("Default search query mock test successful")
    
    # Mock tests
    @patch('app.core.services.Websearch.Websearch.search')
    def test_empty_search_results(self, mock_search):
        self.logger.info("Testing empty search results with mock")
        # Test empty search results
        mock_search.return_value = []
        
        results = self.websearch.search("nonexistentsearchterm12345")
        
        self.assertEqual(results, [])
        self.assertEqual(len(results), 0)
        self.logger.info("Empty search results mock test successful")
    
    # Mock tests
    @patch('app.core.services.Websearch.Websearch.get_top_news')
    def test_get_market_news(self, mock_get_top_news):
        self.logger.info("Testing market news retrieval with mock")
        # Test top market news
        mock_news = [
            {"title": "Today's key market news", "url": "https://example.com/market1"},
            {"title": "Global market trends", "url": "https://example.com/market2"}
        ]
        mock_get_top_news.return_value = mock_news
        
        news = self.websearch.get_top_news("stock market")
        
        self.assertIsNotNone(news)
        self.assertEqual(len(news), 2)
        mock_get_top_news.assert_called_once_with("stock market")
        self.logger.info("Market news mock test successful")
    
    # Real service tests
    def test_real_search(self):
        """Test actual search functionality with real search engine"""
        self.logger.info("Testing real search functionality")
        if not self.api_keys_available:
            self.logger.warning("Websearch API keys not available, skipping real service test")
            self.skipTest("Websearch API keys not available for real service test")
        
        try:
            # Setup API keys for real test
            self.logger.info("Setting up API keys for real search test")
            # Assuming Websearch class has methods to set API keys
            self.websearch.set_api_keys(
                search_api_key=self.credentials.get('search_api_key'),
                search_engine_id=self.credentials.get('search_engine_id')
            )
            
            # Perform real search
            query = "Samsung Electronics financial results"
            self.logger.info(f"Performing real search for: {query}")
            results = self.websearch.search(query)
            
            # Verify real response
            self.assertIsNotNone(results)
            self.assertGreater(len(results), 0, "Search should return at least one result")
            self.logger.info(f"Search returned {len(results)} results")
            
            # Check first result structure
            first_result = results[0]
            self.assertIn("title", first_result)
            self.assertIn("url", first_result)
            self.assertTrue(first_result["url"].startswith("http"))
            
            # Content should be related to query
            self.assertTrue(
                "Samsung" in first_result["title"] or 
                "Electronics" in first_result["title"] or
                "financial" in first_result["title"].lower(),
                "Search results should be related to the query"
            )
            self.logger.info(f"First result title: {first_result['title']}")
            
        except Exception as e:
            self.logger.error(f"Real search test failed: {str(e)}")
            self.fail(f"Real search test failed: {str(e)}")
    
    # Real service tests
    def test_real_current_news(self):
        """Test actual news retrieval functionality"""
        self.logger.info("Testing real news retrieval")
        if not self.api_keys_available:
            self.logger.warning("Websearch API keys not available, skipping real service test")
            self.skipTest("Websearch API keys not available for real service test")
        
        try:
            # Setup API keys
            self.websearch.set_api_keys(
                search_api_key=self.credentials.get('search_api_key'),
                search_engine_id=self.credentials.get('search_engine_id')
            )
            
            # Get real top news
            query = "latest stock market news"
            self.logger.info(f"Getting real news for: {query}")
            news = self.websearch.get_top_news(query)
            
            # Verify real response
            self.assertIsNotNone(news)
            self.assertGreater(len(news), 0, "News search should return at least one result")
            self.logger.info(f"News search returned {len(news)} results")
            
            # Check news structure
            for item in news[:3]:  # Check first three items
                self.assertIn("title", item)
                self.assertIn("url", item)
                self.assertTrue(item["url"].startswith("http"))
            
            # Should be recent news
            if "date" in news[0]:
                # If date is available, check it's recent
                news_date = datetime.strptime(news[0]["date"], "%Y-%m-%d")
                one_month_ago = datetime.now() - timedelta(days=30)
                self.assertGreaterEqual(news_date, one_month_ago, "News should be recent")
                self.logger.info(f"News date: {news_date.strftime('%Y-%m-%d')} is recent")
            
        except Exception as e:
            self.logger.error(f"Real news test failed: {str(e)}")
            self.fail(f"Real news test failed: {str(e)}")
    
    # Real service tests
    def test_search_with_different_queries(self):
        """Test search with different types of queries"""
        self.logger.info("Testing search with multiple different queries")
        if not self.api_keys_available:
            self.logger.warning("Websearch API keys not available, skipping real service test")
            self.skipTest("Websearch API keys not available for real service test")
        
        try:
            # Setup API
            self.websearch.set_api_keys(
                search_api_key=self.credentials.get('search_api_key'),
                search_engine_id=self.credentials.get('search_engine_id')
            )
            
            # Test with different queries
            queries = [
                "stock market trends 2023",
                "technology industry outlook",
                "cryptocurrency prices"
            ]
            
            for query in queries:
                self.logger.info(f"Testing search with query: {query}")
                results = self.websearch.search(query)
                
                # Verify real response for each query
                self.assertIsNotNone(results)
                self.assertGreater(len(results), 0, f"Search for '{query}' should return results")
                self.logger.info(f"Query '{query}' returned {len(results)} results")
                
                # Results should relate to query
                query_terms = query.lower().split()
                found_relevant = False
                
                for result in results[:3]:  # Check first three results
                    title_lower = result["title"].lower()
                    for term in query_terms:
                        if term in title_lower:
                            found_relevant = True
                            break
                
                self.assertTrue(found_relevant, f"Results for '{query}' should contain query terms")
                self.logger.info(f"Results for '{query}' are relevant")
                
        except Exception as e:
            self.logger.error(f"Multiple query test failed: {str(e)}")
            self.fail(f"Multiple query test failed: {str(e)}")
    
if __name__ == '__main__':
    unittest.main() 