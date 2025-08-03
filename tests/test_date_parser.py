import pytest
from datetime import datetime, timedelta
from utils.date_parser import parse_dutch_date, parse_event_date, extract_time_info


class TestDutchDateParser:
    def test_parse_dutch_months(self):
        """Test parsing Dutch month names"""
        test_cases = [
            ("15 januari 2024", datetime(2024, 1, 15)),
            ("3 maart 2024", datetime(2024, 3, 3)),
            ("25 december 2024", datetime(2024, 12, 25)),
            ("1 mei 2024", datetime(2024, 5, 1))
        ]
        
        for date_str, expected in test_cases:
            result = parse_dutch_date(date_str)
            assert result is not None
            assert result.date() == expected.date()
            
    def test_parse_dutch_days(self):
        """Test parsing Dutch day names"""
        # These should parse successfully (day names are replaced)
        test_cases = [
            "vrijdag 15 maart 2024",
            "zaterdag 16 maart 2024",
            "zondag 17 maart 2024"
        ]
        
        for date_str in test_cases:
            result = parse_dutch_date(date_str)
            assert result is not None
            
    def test_parse_dutch_date_case_insensitive(self):
        """Test that Dutch parsing is case insensitive"""
        date1 = parse_dutch_date("15 JANUARI 2024")
        date2 = parse_dutch_date("15 januari 2024")
        
        assert date1 is not None
        assert date2 is not None
        assert date1.date() == date2.date()


class TestEventDateParser:
    def test_parse_standard_formats(self):
        """Test parsing standard date formats"""
        test_cases = [
            ("March 15, 2024", datetime(2024, 3, 15)),
            ("15/03/2024", datetime(2024, 3, 15)),
            ("2024-03-15", datetime(2024, 3, 15)),
            ("15 March 2024", datetime(2024, 3, 15))
        ]
        
        for date_str, expected in test_cases:
            result = parse_event_date(date_str)
            assert result.date() == expected.date()
            
    def test_parse_future_dates_without_year(self):
        """Test that dates without year are assumed to be in the future"""
        reference = datetime(2024, 3, 1)
        
        # Date in the past without year should become next year
        result = parse_event_date("15 February", reference)
        assert result.year == 2025
        assert result.month == 2
        assert result.day == 15
        
        # Date in the future without year should stay current year
        result = parse_event_date("15 April", reference)
        assert result.year == 2024
        assert result.month == 4
        assert result.day == 15
        
    def test_parse_relative_dates(self):
        """Test parsing relative date expressions"""
        reference = datetime(2024, 3, 15, 12, 0)
        
        # Today
        result = parse_event_date("today", reference)
        assert result.date() == reference.date()
        
        result = parse_event_date("vandaag", reference)  # Dutch
        assert result.date() == reference.date()
        
        # Tomorrow
        result = parse_event_date("tomorrow", reference)
        assert result.date() == (reference + timedelta(days=1)).date()
        
        result = parse_event_date("morgen", reference)  # Dutch
        assert result.date() == (reference + timedelta(days=1)).date()
        
    def test_parse_weekend_relative(self):
        """Test parsing 'this weekend' relative to different days"""
        # Monday - should return Friday
        reference = datetime(2024, 3, 11)  # Monday
        result = parse_event_date("this weekend", reference)
        assert result.weekday() == 4  # Friday
        assert result.day == 15
        
        # Friday afternoon - should return next Friday
        reference = datetime(2024, 3, 15, 19, 0)  # Friday 7pm
        result = parse_event_date("this weekend", reference)
        assert result.weekday() == 4  # Friday
        assert result.day == 22
        
    def test_fallback_to_reference_date(self):
        """Test fallback when date cannot be parsed"""
        reference = datetime(2024, 3, 15)
        
        result = parse_event_date("gibberish date", reference)
        assert result == reference


class TestTimeExtraction:
    def test_extract_24_hour_format(self):
        """Test extracting 24-hour time format"""
        test_cases = [
            ("Event starts at 23:00 - 06:00", {"start_time": "23:00", "end_time": "06:00"}),
            ("Doors: 22:30 - 05:00", {"start_time": "22:30", "end_time": "05:00"}),
            ("23:00-06:00 hrs", {"start_time": "23:00", "end_time": "06:00"}),
            ("Open from 2300 - 0600 hours", {"start_time": "23:00", "end_time": "06:00"})
        ]
        
        for text, expected in test_cases:
            result = extract_time_info(text)
            assert result == expected
            
    def test_extract_12_hour_format(self):
        """Test extracting 12-hour AM/PM format"""
        test_cases = [
            ("Party from 11pm - 6am", {"start_time": "23:00", "end_time": "06:00"}),
            ("Opens at 10PM - 5AM", {"start_time": "22:00", "end_time": "05:00"}),
            ("12am - 8am", {"start_time": "00:00", "end_time": "08:00"}),
            ("12pm - 11pm", {"start_time": "12:00", "end_time": "23:00"})
        ]
        
        for text, expected in test_cases:
            result = extract_time_info(text)
            assert result == expected
            
    def test_no_time_found(self):
        """Test when no time information is found"""
        test_cases = [
            "Event this Friday",
            "Techno party all night",
            "Starting soon"
        ]
        
        for text in test_cases:
            result = extract_time_info(text)
            assert result is None
            
    def test_dutch_time_format(self):
        """Test Dutch time format with 'uur'"""
        text = "Van 23:00 uur - 06:00 uur"
        result = extract_time_info(text)
        
        assert result == {"start_time": "23:00", "end_time": "06:00"}