import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import TechnoEventAggregator, main
from models.event import Event


class TestTechnoEventAggregator:
    @pytest.fixture
    def aggregator(self):
        return TechnoEventAggregator()
        
    def test_initialization(self, aggregator):
        """Test aggregator initialization"""
        assert len(aggregator.scrapers) == 3
        assert any(s.venue_name == "Shelter" for s in aggregator.scrapers)
        assert any(s.venue_name == "Radion" for s in aggregator.scrapers)
        assert any(s.venue_name == "Lofi" for s in aggregator.scrapers)
        
    @patch('main.ShelterScraper.scrape_events')
    @patch('main.RadionScraper.scrape_events')
    @patch('main.LofiScraper.scrape_events')
    def test_scrape_all_venues(self, mock_lofi, mock_radion, mock_shelter, aggregator):
        """Test scraping from all venues"""
        # Mock scraper returns
        mock_shelter.return_value = [
            Event(venue="Shelter", venue_url="https://shelter.nl",
                  name="Event 1", date=datetime.now())
        ]
        mock_radion.return_value = [
            Event(venue="Radion", venue_url="https://radion.nl",
                  name="Event 2", date=datetime.now())
        ]
        mock_lofi.return_value = [
            Event(venue="Lofi", venue_url="https://lofi.nl",
                  name="Event 3", date=datetime.now())
        ]
        
        events = aggregator.scrape_all_venues()
        
        assert len(events) == 3
        assert any(e.venue == "Shelter" for e in events)
        assert any(e.venue == "Radion" for e in events)
        assert any(e.venue == "Lofi" for e in events)
        
        # All scrapers should be called
        mock_shelter.assert_called_once()
        mock_radion.assert_called_once()
        mock_lofi.assert_called_once()
        
    @patch('main.ShelterScraper.scrape_events')
    def test_scrape_all_venues_with_error(self, mock_shelter, aggregator):
        """Test scraping continues even if one venue fails"""
        # Make Shelter scraper fail
        mock_shelter.side_effect = Exception("Network error")
        
        # Other scrapers should work normally
        with patch('main.RadionScraper.scrape_events') as mock_radion:
            mock_radion.return_value = [
                Event(venue="Radion", venue_url="https://radion.nl",
                      name="Event", date=datetime.now())
            ]
            
            events = aggregator.scrape_all_venues()
            
        # Should still get events from working scrapers
        assert len(events) >= 1
        assert any(e.venue == "Radion" for e in events)
        
    def test_filter_upcoming_events(self, aggregator):
        """Test filtering events to upcoming ones only"""
        now = datetime.now()
        events = [
            Event(venue="Test", venue_url="https://test.com",
                  name="Past Event", date=now - timedelta(days=1)),
            Event(venue="Test", venue_url="https://test.com",
                  name="Today Event", date=now + timedelta(hours=2)),
            Event(venue="Test", venue_url="https://test.com",
                  name="Tomorrow Event", date=now + timedelta(days=1)),
            Event(venue="Test", venue_url="https://test.com",
                  name="Next Week Event", date=now + timedelta(days=6)),
            Event(venue="Test", venue_url="https://test.com",
                  name="Too Far Event", date=now + timedelta(days=8))
        ]
        
        # Filter for next 7 days
        upcoming = aggregator.filter_upcoming_events(events, days=7)
        
        assert len(upcoming) == 3
        assert "Past Event" not in [e.name for e in upcoming]
        assert "Too Far Event" not in [e.name for e in upcoming]
        assert upcoming[0].name == "Today Event"  # Should be sorted by date
        
    def test_deduplicate_events(self, aggregator):
        """Test removing duplicate events"""
        date = datetime.now()
        events = [
            Event(venue="Shelter", venue_url="https://shelter.nl",
                  name="Techno Night", date=date),
            Event(venue="Shelter", venue_url="https://shelter.nl",
                  name="TECHNO NIGHT", date=date),  # Same event, different case
            Event(venue="Shelter", venue_url="https://shelter.nl",
                  name="Techno Night", date=date + timedelta(hours=1)),  # Same date
            Event(venue="Radion", venue_url="https://radion.nl",
                  name="Techno Night", date=date),  # Different venue
            Event(venue="Shelter", venue_url="https://shelter.nl",
                  name="Techno Night", date=date + timedelta(days=1))  # Different day
        ]
        
        unique = aggregator.deduplicate_events(events)
        
        assert len(unique) == 3  # Should keep venue/day combinations


class TestMainFunction:
    @patch('sys.argv', ['main.py', '--output', 'json'])
    @patch('main.TechnoEventAggregator')
    @patch('main.save_events_json')
    def test_main_json_output(self, mock_save_json, mock_aggregator_class):
        """Test main function with JSON output"""
        # Setup mock aggregator
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        # Mock events
        events = [
            Event(venue="Test", venue_url="https://test.com",
                  name="Event 1", date=datetime.now() + timedelta(days=1))
        ]
        mock_aggregator.scrape_all_venues.return_value = events
        mock_aggregator.deduplicate_events.return_value = events
        mock_aggregator.filter_upcoming_events.return_value = events
        
        with pytest.raises(SystemExit) as exc_info:
            main()
            
        assert exc_info.value.code == 0  # Should exit successfully
        mock_save_json.assert_called_once_with(events, 'events.json')
        
    @patch('sys.argv', ['main.py', '--output', 'email', '--email', 'test@test.com'])
    @patch('main.TechnoEventAggregator')
    @patch('main.send_email')
    def test_main_email_output(self, mock_send_email, mock_aggregator_class):
        """Test main function with email output"""
        # Setup mock
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        events = [
            Event(venue="Test", venue_url="https://test.com",
                  name="Event", date=datetime.now() + timedelta(days=1))
        ]
        mock_aggregator.scrape_all_venues.return_value = events
        mock_aggregator.deduplicate_events.return_value = events
        mock_aggregator.filter_upcoming_events.return_value = events
        
        mock_send_email.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
            
        assert exc_info.value.code == 0
        mock_send_email.assert_called_once_with(events, 'test@test.com')
        
    @patch('sys.argv', ['main.py', '--days', '14'])
    @patch('main.TechnoEventAggregator')
    @patch('main.save_events_json')
    def test_main_custom_days(self, mock_save_json, mock_aggregator_class):
        """Test main function with custom days parameter"""
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        events = []
        mock_aggregator.scrape_all_venues.return_value = events
        mock_aggregator.deduplicate_events.return_value = events
        mock_aggregator.filter_upcoming_events.return_value = events
        
        with pytest.raises(SystemExit):
            main()
            
        # Check that filter was called with 14 days
        mock_aggregator.filter_upcoming_events.assert_called_with(events, days=14)
        
    @patch('sys.argv', ['main.py'])
    @patch('main.TechnoEventAggregator')
    @patch('main.save_events_json')
    def test_main_no_events_found(self, mock_save_json, mock_aggregator_class):
        """Test main function when no events are found"""
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        # Return empty events
        mock_aggregator.scrape_all_venues.return_value = []
        mock_aggregator.deduplicate_events.return_value = []
        mock_aggregator.filter_upcoming_events.return_value = []
        
        with pytest.raises(SystemExit) as exc_info:
            main()
            
        assert exc_info.value.code == 1  # Should exit with error code
        
    @patch('sys.argv', ['main.py', '--output', 'both', '--email', 'test@test.com'])
    @patch('main.TechnoEventAggregator')
    @patch('main.save_events_json')
    @patch('main.send_email')
    @patch('os.getenv')
    def test_main_github_actions_mode(self, mock_getenv, mock_send_email, 
                                     mock_save_json, mock_aggregator_class):
        """Test main function in GitHub Actions environment"""
        # Simulate GitHub Actions environment
        mock_getenv.return_value = 'true'
        
        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        
        events = [
            Event(venue="Test", venue_url="https://test.com",
                  name="Event", date=datetime.now() + timedelta(days=1))
        ]
        mock_aggregator.scrape_all_venues.return_value = events
        mock_aggregator.deduplicate_events.return_value = events
        mock_aggregator.filter_upcoming_events.return_value = events
        
        mock_send_email.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
            
        assert exc_info.value.code == 0
        
        # Should save JSON and send email
        mock_save_json.assert_called_once()
        mock_send_email.assert_called_once()
        mock_getenv.assert_called_with('GITHUB_ACTIONS')