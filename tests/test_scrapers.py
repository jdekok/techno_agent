import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup

from scrapers.shelter import ShelterScraper
from scrapers.radion import RadionScraper
from scrapers.lofi import LofiScraper
from models.event import Event


class TestShelterScraper:
    @pytest.fixture
    def scraper(self):
        return ShelterScraper()
        
    def test_initialization(self, scraper):
        """Test Shelter scraper initialization"""
        assert scraper.venue_name == "Shelter"
        assert scraper.venue_url == "https://www.shelteramsterdam.nl"
        
    @patch.object(ShelterScraper, 'fetch_page')
    def test_scrape_events_no_events(self, mock_fetch, scraper):
        """Test scraping when no events are found"""
        mock_fetch.return_value = BeautifulSoup("<html><body></body></html>", "lxml")
        
        events = scraper.scrape_events()
        
        assert events == []
        mock_fetch.assert_called_once_with(scraper.venue_url)
        
    @patch.object(ShelterScraper, 'fetch_page')
    def test_scrape_events_with_event_links(self, mock_fetch, scraper):
        """Test scraping with event links"""
        # Mock main page
        main_html = """
        <html>
            <body>
                <a href="/event/techno-night/">Techno Night</a>
                <a href="/event/house-party/">House Party</a>
                <a href="/about">About</a>
            </body>
        </html>
        """
        
        # Mock event detail page
        event_html = """
        <html>
            <body>
                <h1>Techno Night</h1>
                <div class="date">15 March 2024</div>
                <meta name="description" content="Underground techno event">
            </body>
        </html>
        """
        
        mock_fetch.side_effect = [
            BeautifulSoup(main_html, "lxml"),
            BeautifulSoup(event_html, "lxml"),
            BeautifulSoup(event_html.replace("Techno", "House"), "lxml")
        ]
        
        events = scraper.scrape_events()
        
        assert len(events) >= 1  # At least techno event should be found
        assert any("techno" in event.name.lower() for event in events)
        
    @patch.object(ShelterScraper, 'fetch_page')
    def test_parse_event_detail(self, mock_fetch, scraper):
        """Test parsing event detail page"""
        event_html = """
        <html>
            <body>
                <h1>Techno Night with DJ Test</h1>
                <div class="date">Saturday 15.03.2024</div>
                <div class="lineup">
                    <p>DJ Test</p>
                    <p>Live Act</p>
                </div>
                <meta name="description" content="Underground techno event">
            </body>
        </html>
        """
        
        mock_fetch.return_value = BeautifulSoup(event_html, "lxml")
        
        event = scraper._scrape_event_detail("https://test.com/event/test")
        
        assert event is not None
        assert "Techno Night" in event.name
        assert event.venue == "Shelter"
        assert event.date.year >= 2024


class TestRadionScraper:
    @pytest.fixture
    def scraper(self):
        return RadionScraper()
        
    def test_initialization(self, scraper):
        """Test Radion scraper initialization"""
        assert scraper.venue_name == "Radion"
        assert scraper.venue_url == "https://radion.amsterdam"
        
    def test_parse_event_container(self, scraper):
        """Test parsing event from container element"""
        container_html = """
        <div class="event-card">
            <h3>Techno Tuesday</h3>
            <div class="date">5 March 2024</div>
            <div class="category">Club</div>
            <a href="/event/techno-tuesday">More info</a>
        </div>
        """
        
        container = BeautifulSoup(container_html, "lxml").find("div")
        event = scraper._parse_event_container(container)
        
        assert event is not None
        assert event.name == "Techno Tuesday"
        assert event.venue == "Radion"
        assert "Club" in event.description
        
    def test_parse_event_container_with_missing_data(self, scraper):
        """Test parsing event with minimal data"""
        container_html = """
        <div class="event">
            <span>Mystery Event</span>
        </div>
        """
        
        container = BeautifulSoup(container_html, "lxml").find("div")
        event = scraper._parse_event_container(container)
        
        assert event is not None
        assert "Mystery Event" in event.name


class TestLofiScraper:
    @pytest.fixture
    def scraper(self):
        return LofiScraper()
        
    def test_initialization(self, scraper):
        """Test Lofi scraper initialization"""
        assert scraper.venue_name == "Lofi"
        assert scraper.venue_url == "https://lofi.amsterdam"
        
    def test_parse_event_container_with_location(self, scraper):
        """Test parsing event with location info"""
        container_html = """
        <div class="event-item">
            <h2>Warehouse Rave</h2>
            <div class="date">16 August 2025</div>
            <div class="location">Courtyard</div>
            <span>18+</span>
        </div>
        """
        
        container = BeautifulSoup(container_html, "lxml").find("div")
        event = scraper._parse_event_container(container)
        
        assert event is not None
        assert event.name == "Warehouse Rave"
        assert "Location: Courtyard" in event.description
        assert "Age: 18+" in event.description
        
    def test_extract_artists_from_event_name(self, scraper):
        """Test extracting artist names from event title"""
        test_cases = [
            ("Dekmantel presents DJ Rush", ["DJ Rush"]),
            ("Vault Sessions invites Nina Kraviz b2b Helena Hauff", ["Nina Kraviz", "Helena Hauff"]),
            ("STRAF_WERK: Ben Klock, DVS1, Surgeon", ["Ben Klock, DVS1, Surgeon"]),
            ("Simple Event Name", [])
        ]
        
        for event_name, expected_artists in test_cases:
            container_html = f'<div class="event"><h2>{event_name}</h2></div>'
            container = BeautifulSoup(container_html, "lxml").find("div")
            event = scraper._parse_event_container(container)
            
            if expected_artists:
                assert len(event.artists) > 0
                for artist in expected_artists:
                    assert any(artist in found for found in event.artists)
                    
    @patch.object(LofiScraper, 'fetch_page')
    def test_scrape_events_fallback_to_links(self, mock_fetch, scraper):
        """Test fallback to link extraction when no containers found"""
        html = """
        <html>
            <body>
                <a href="/events/techno-night">Techno All Night Long</a>
                <a href="/events/minimal-morning">Minimal Morning</a>
                <a href="/contact">Contact</a>
            </body>
        </html>
        """
        
        mock_fetch.return_value = BeautifulSoup(html, "lxml")
        
        events = scraper.scrape_events()
        
        # Should find at least the techno event
        assert len(events) >= 1
        assert any("techno" in event.name.lower() for event in events)