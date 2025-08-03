import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
import json
import os

from utils.email_sender import (
    format_events_html, format_events_text, send_email, save_events_json
)
from models.event import Event


class TestEmailFormatting:
    @pytest.fixture
    def sample_events(self):
        """Create sample events for testing"""
        return [
            Event(
                venue="Shelter",
                venue_url="https://shelter.nl",
                name="Techno Night",
                date=datetime(2024, 3, 15, 23, 0),
                url="https://shelter.nl/event/1",
                artists=["DJ One", "DJ Two"]
            ),
            Event(
                venue="Radion",
                venue_url="https://radion.nl",
                name="Underground Session",
                date=datetime(2024, 3, 16, 22, 0),
                artists=["Artist A", "Artist B", "Artist C"]
            ),
            Event(
                venue="Shelter",
                venue_url="https://shelter.nl",
                name="Late Night Rave",
                date=datetime(2024, 3, 17, 23, 30)
            )
        ]
        
    def test_format_events_html(self, sample_events):
        """Test HTML formatting of events"""
        html = format_events_html(sample_events)
        
        # Check basic structure
        assert "<html>" in html
        assert "Amsterdam Techno Events This Week" in html
        
        # Check venues are included
        assert "Shelter" in html
        assert "Radion" in html
        
        # Check event details
        assert "Techno Night" in html
        assert "Underground Session" in html
        assert "DJ One, DJ Two" in html
        
        # Check dates are formatted
        assert "Friday, March 15 at 23:00" in html
        assert "Saturday, March 16 at 22:00" in html
        
        # Check links
        assert 'href="https://shelter.nl/event/1"' in html
        
    def test_format_events_text(self, sample_events):
        """Test plain text formatting of events"""
        text = format_events_text(sample_events)
        
        # Check header
        assert "AMSTERDAM TECHNO EVENTS THIS WEEK" in text
        
        # Check venues
        assert "SHELTER" in text
        assert "RADION" in text
        
        # Check events
        assert "Techno Night" in text
        assert "Underground Session" in text
        
        # Check formatted dates
        assert "Friday, March 15 at 23:00" in text
        
        # Check artists
        assert "Artists: DJ One, DJ Two" in text
        
        # Check links
        assert "Link: https://shelter.nl/event/1" in text
        
    def test_format_events_with_many_artists(self):
        """Test formatting when event has many artists"""
        events = [
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Big Festival",
                date=datetime.now(),
                artists=[f"Artist {i}" for i in range(10)]
            )
        ]
        
        html = format_events_html(events)
        text = format_events_text(events)
        
        # Should show first 5 artists + count of remaining
        assert "Artist 0, Artist 1, Artist 2, Artist 3, Artist 4 +5 more" in html
        assert "Artist 0, Artist 1, Artist 2, Artist 3, Artist 4 +5 more" in text
        
    def test_events_sorted_by_date(self, sample_events):
        """Test that events are sorted by date"""
        # Shuffle events
        import random
        shuffled = sample_events.copy()
        random.shuffle(shuffled)
        
        text = format_events_text(shuffled)
        
        # Find positions of event names in the text
        pos_15 = text.find("March 15")
        pos_16 = text.find("March 16")
        pos_17 = text.find("March 17")
        
        # Events should appear in chronological order
        assert pos_15 < pos_16 < pos_17


class TestEmailSending:
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        # Setup mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        events = [
            Event(
                venue="Test",
                venue_url="https://test.com",
                name="Test Event",
                date=datetime.now()
            )
        ]
        
        smtp_config = {
            'server': 'smtp.test.com',
            'port': 587,
            'username': 'test@test.com',
            'password': 'testpass',
            'from_email': 'from@test.com'
        }
        
        result = send_email(events, 'recipient@test.com', smtp_config)
        
        assert result is True
        mock_smtp.assert_called_once_with('smtp.test.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'testpass')
        mock_server.send_message.assert_called_once()
        
    @patch('smtplib.SMTP')
    def test_send_email_from_env_vars(self, mock_smtp):
        """Test email sending using environment variables"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        events = [Event(venue="Test", venue_url="https://test.com", 
                       name="Test", date=datetime.now())]
        
        with patch.dict(os.environ, {
            'SMTP_SERVER': 'smtp.env.com',
            'SMTP_PORT': '465',
            'SMTP_USERNAME': 'env@test.com',
            'SMTP_PASSWORD': 'envpass'
        }):
            result = send_email(events, 'recipient@test.com')
            
        assert result is True
        mock_smtp.assert_called_once_with('smtp.env.com', 465)
        
    def test_send_email_missing_credentials(self):
        """Test email sending with missing credentials"""
        events = [Event(venue="Test", venue_url="https://test.com",
                       name="Test", date=datetime.now())]
        
        with patch.dict(os.environ, {}, clear=True):
            result = send_email(events, 'recipient@test.com')
            
        assert result is False
        
    @patch('smtplib.SMTP')
    def test_send_email_smtp_error(self, mock_smtp):
        """Test email sending when SMTP fails"""
        mock_smtp.side_effect = Exception("SMTP Error")
        
        events = [Event(venue="Test", venue_url="https://test.com",
                       name="Test", date=datetime.now())]
        
        smtp_config = {
            'server': 'smtp.test.com',
            'port': 587,
            'username': 'test@test.com',
            'password': 'testpass'
        }
        
        result = send_email(events, 'recipient@test.com', smtp_config)
        
        assert result is False


class TestEventSaving:
    def test_save_events_json(self):
        """Test saving events to JSON file"""
        events = [
            Event(
                venue="Test Venue",
                venue_url="https://test.com",
                name="Test Event",
                date=datetime(2024, 3, 15, 23, 0),
                artists=["Artist 1"]
            )
        ]
        
        m = mock_open()
        with patch('builtins.open', m):
            save_events_json(events, "test.json")
            
        # Check file was opened for writing
        m.assert_called_once_with("test.json", 'w', encoding='utf-8')
        
        # Get what was written
        handle = m()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
        
        # Parse and verify JSON
        data = json.loads(written_content)
        assert len(data) == 1
        assert data[0]['venue'] == "Test Venue"
        assert data[0]['name'] == "Test Event"
        assert data[0]['artists'] == ["Artist 1"]
        
    def test_save_events_json_with_special_chars(self):
        """Test saving events with special characters"""
        events = [
            Event(
                venue="Café Test",
                venue_url="https://test.com",
                name="Techno Night × Special Guest",
                date=datetime.now(),
                description="Amsterdam's finest underground party"
            )
        ]
        
        m = mock_open()
        with patch('builtins.open', m):
            save_events_json(events, "test.json")
            
        written_content = ''.join(call.args[0] for call in m().write.call_args_list)
        data = json.loads(written_content)
        
        # Special characters should be preserved
        assert "Café" in data[0]['venue']
        assert "×" in data[0]['name']
        assert "'" in data[0]['description']