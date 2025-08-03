import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import responses
import requests

from scrapers.base_scraper import BaseScraper
from models.event import Event


class TestBaseScraper:
    @pytest.fixture
    def mock_scraper(self):
        """Create a concrete implementation of BaseScraper for testing"""
        class MockScraper(BaseScraper):
            def scrape_events(self):
                return []
                
        return MockScraper("Test Venue", "https://test.com")
        
    def test_initialization(self, mock_scraper):
        """Test scraper initialization"""
        assert mock_scraper.venue_name == "Test Venue"
        assert mock_scraper.venue_url == "https://test.com"
        assert isinstance(mock_scraper.session, requests.Session)
        assert "User-Agent" in mock_scraper.session.headers
        
    @responses.activate
    def test_fetch_page_success(self, mock_scraper):
        """Test successful page fetching"""
        test_html = "<html><body><h1>Test Page</h1></body></html>"
        responses.add(
            responses.GET,
            "https://test.com/page",
            body=test_html,
            status=200
        )
        
        soup = mock_scraper.fetch_page("https://test.com/page")
        
        assert soup is not None
        assert soup.find("h1").text == "Test Page"
        assert len(responses.calls) == 1
        
    @responses.activate
    def test_fetch_page_retry_on_failure(self, mock_scraper):
        """Test retry logic on failed requests"""
        # First two attempts fail, third succeeds
        responses.add(
            responses.GET,
            "https://test.com/page",
            status=500
        )
        responses.add(
            responses.GET,
            "https://test.com/page",
            status=500
        )
        responses.add(
            responses.GET,
            "https://test.com/page",
            body="<html><body>Success</body></html>",
            status=200
        )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            soup = mock_scraper.fetch_page("https://test.com/page")
            
        assert soup is not None
        assert len(responses.calls) == 3
        
    @responses.activate
    def test_fetch_page_max_retries_exceeded(self, mock_scraper):
        """Test that fetch returns None after max retries"""
        # All attempts fail
        for _ in range(3):
            responses.add(
                responses.GET,
                "https://test.com/page",
                status=500
            )
            
        with patch('time.sleep'):  # Mock sleep to speed up test
            soup = mock_scraper.fetch_page("https://test.com/page")
            
        assert soup is None
        assert len(responses.calls) == 3
        
    def test_filter_techno_events_by_name(self, mock_scraper):
        """Test filtering events by techno keywords in name"""
        events = [
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Techno Night",
                date=datetime.now()
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Jazz Evening",
                date=datetime.now()
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Underground Rave",
                date=datetime.now()
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Classical Concert",
                date=datetime.now()
            )
        ]
        
        filtered = mock_scraper.filter_techno_events(events)
        
        assert len(filtered) == 2
        assert filtered[0].name == "Techno Night"
        assert filtered[1].name == "Underground Rave"
        
    def test_filter_techno_events_by_description(self, mock_scraper):
        """Test filtering events by techno keywords in description"""
        events = [
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Friday Night",
                date=datetime.now(),
                description="Amazing techno party"
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Saturday Session",
                date=datetime.now(),
                description="Rock and roll all night"
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Sunday Vibes",
                date=datetime.now(),
                description="Minimal electronic music"
            )
        ]
        
        filtered = mock_scraper.filter_techno_events(events)
        
        assert len(filtered) == 2
        assert filtered[0].name == "Friday Night"
        assert filtered[1].name == "Sunday Vibes"
        
    def test_filter_techno_events_by_artists(self, mock_scraper):
        """Test filtering events by techno keywords in artist names"""
        events = [
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Music Night",
                date=datetime.now(),
                artists=["Techno DJ", "House Master"]
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Live Show",
                date=datetime.now(),
                artists=["Rock Band"]
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Club Night",
                date=datetime.now(),
                artists=["Acid Professor", "Minimal Expert"]
            )
        ]
        
        filtered = mock_scraper.filter_techno_events(events)
        
        assert len(filtered) == 2
        assert filtered[0].name == "Music Night"
        assert filtered[1].name == "Club Night"
        
    def test_filter_techno_events_case_insensitive(self, mock_scraper):
        """Test that filtering is case insensitive"""
        events = [
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="TECHNO NIGHT",
                date=datetime.now()
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="TeCHnO pArTy",
                date=datetime.now()
            ),
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="jazz night",
                date=datetime.now()
            )
        ]
        
        filtered = mock_scraper.filter_techno_events(events)
        
        assert len(filtered) == 2
        assert all("jazz" not in event.name.lower() for event in filtered)