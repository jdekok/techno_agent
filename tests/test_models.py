import pytest
from datetime import datetime
from models.event import Event


class TestEventModel:
    def test_event_creation(self):
        """Test basic event creation"""
        event = Event(
            venue="Test Venue",
            venue_url="https://test.com",
            name="Test Event",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        assert event.venue == "Test Venue"
        assert event.venue_url == "https://test.com"
        assert event.name == "Test Event"
        assert event.date == datetime(2024, 3, 15, 23, 0)
        assert event.url is None
        assert event.artists == []
        assert event.price is None
        assert event.description is None
        
    def test_event_with_full_data(self):
        """Test event creation with all fields"""
        event = Event(
            venue="Shelter",
            venue_url="https://shelteramsterdam.nl",
            name="Techno Night",
            date=datetime(2024, 3, 15, 23, 0),
            url="https://shelteramsterdam.nl/event/techno-night",
            artists=["DJ One", "DJ Two"],
            price="€15",
            description="Underground techno event"
        )
        
        assert event.artists == ["DJ One", "DJ Two"]
        assert event.price == "€15"
        assert event.description == "Underground techno event"
        
    def test_event_hash(self):
        """Test event hashing for deduplication"""
        event1 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="Techno Night",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        event2 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="Techno Night",
            date=datetime(2024, 3, 15, 22, 0)  # Different time, same date
        )
        
        event3 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="Different Event",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        # Same venue, name, and date should have same hash
        assert hash(event1) == hash(event2)
        
        # Different name should have different hash
        assert hash(event1) != hash(event3)
        
    def test_event_equality(self):
        """Test event equality comparison"""
        event1 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="Techno Night",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        event2 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="Techno Night",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        event3 = Event(
            venue="Radion",
            venue_url="https://test.com",
            name="Techno Night",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        assert event1 == event2
        assert event1 != event3
        assert event1 != "not an event"
        
    def test_event_json_serialization(self):
        """Test JSON serialization of events"""
        event = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="Techno Night",
            date=datetime(2024, 3, 15, 23, 0),
            artists=["DJ One"]
        )
        
        json_data = event.dict()
        
        assert json_data["venue"] == "Shelter"
        assert json_data["name"] == "Techno Night"
        assert isinstance(json_data["date"], str)  # Should be ISO format
        assert json_data["artists"] == ["DJ One"]
        
    def test_event_case_insensitive_equality(self):
        """Test that event names are compared case-insensitively"""
        event1 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="TECHNO NIGHT",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        event2 = Event(
            venue="Shelter",
            venue_url="https://test.com",
            name="techno night",
            date=datetime(2024, 3, 15, 23, 0)
        )
        
        assert event1 == event2
        assert hash(event1) == hash(event2)