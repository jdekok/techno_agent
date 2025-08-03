import re
from datetime import datetime, timedelta
from typing import Optional
from dateutil import parser as dateutil_parser
import logging

logger = logging.getLogger(__name__)


def parse_dutch_date(date_str: str) -> Optional[datetime]:
    """Parse Dutch date formats commonly used by Amsterdam venues"""
    
    # Dutch month names
    dutch_months = {
        'januari': 1, 'februari': 2, 'maart': 3, 'april': 4,
        'mei': 5, 'juni': 6, 'juli': 7, 'augustus': 8,
        'september': 9, 'oktober': 10, 'november': 11, 'december': 12
    }
    
    # Dutch day names (for reference)
    dutch_days = {
        'maandag': 'Monday', 'dinsdag': 'Tuesday', 'woensdag': 'Wednesday',
        'donderdag': 'Thursday', 'vrijdag': 'Friday', 'zaterdag': 'Saturday',
        'zondag': 'Sunday'
    }
    
    # Clean the string
    date_str = date_str.strip().lower()
    
    # Replace Dutch month names with English
    for dutch, english_num in dutch_months.items():
        if dutch in date_str:
            # Replace with English month name for parsing
            english_month = datetime(2000, english_num, 1).strftime('%B').lower()
            date_str = date_str.replace(dutch, english_month)
            
    # Replace Dutch day names
    for dutch, english in dutch_days.items():
        date_str = date_str.replace(dutch, english.lower())
        
    try:
        return dateutil_parser.parse(date_str, fuzzy=True)
    except:
        return None


def parse_event_date(date_str: str, reference_date: Optional[datetime] = None) -> datetime:
    """
    Parse various date formats used by event venues
    
    Args:
        date_str: The date string to parse
        reference_date: Reference date for relative parsing (defaults to now)
        
    Returns:
        Parsed datetime object
    """
    if not reference_date:
        reference_date = datetime.now()
        
    # Clean the input
    date_str = date_str.strip()
    
    # Try standard parsing first
    try:
        parsed = dateutil_parser.parse(date_str, fuzzy=True)
        
        # If the parsed date is in the past and doesn't have a year specified,
        # assume it's for next year
        if parsed < reference_date:
            # Check if year was explicitly mentioned
            if not re.search(r'\b\d{4}\b', date_str):
                parsed = parsed.replace(year=reference_date.year + 1)
                
        return parsed
        
    except:
        pass
        
    # Try Dutch date parsing
    dutch_parsed = parse_dutch_date(date_str)
    if dutch_parsed:
        # Same future date logic
        if dutch_parsed < reference_date and not re.search(r'\b\d{4}\b', date_str):
            dutch_parsed = dutch_parsed.replace(year=reference_date.year + 1)
        return dutch_parsed
        
    # Handle relative dates
    relative_patterns = {
        r'today|vandaag': 0,
        r'tomorrow|morgen': 1,
        r'overmorrow|overmorgen': 2,
        r'this\s+weekend|dit\s+weekend': None,  # Special handling
    }
    
    for pattern, days_offset in relative_patterns.items():
        if re.search(pattern, date_str.lower()):
            if days_offset is not None:
                return reference_date + timedelta(days=days_offset)
            elif 'weekend' in pattern:
                # Find next weekend (Friday)
                days_until_friday = (4 - reference_date.weekday()) % 7
                if days_until_friday == 0 and reference_date.hour >= 18:
                    days_until_friday = 7
                return reference_date + timedelta(days=days_until_friday)
                
    # Last resort: return reference date
    logger.warning(f"Could not parse date: {date_str}, using reference date")
    return reference_date


def extract_time_info(text: str) -> Optional[dict]:
    """Extract time information from event text"""
    time_info = {}
    
    # Pattern for time ranges like "23:00 - 06:00" or "11pm - 6am"
    time_pattern = r'(\d{1,2}):?(\d{2})?\s*(?:hrs?|hours?|uur)?\s*[-–]\s*(\d{1,2}):?(\d{2})?\s*(?:hrs?|hours?|uur)?'
    am_pm_pattern = r'(\d{1,2})\s*([ap]m)\s*[-–]\s*(\d{1,2})\s*([ap]m)'
    
    # Search for 24-hour format
    match = re.search(time_pattern, text, re.I)
    if match:
        start_hour = int(match.group(1))
        start_min = int(match.group(2)) if match.group(2) else 0
        end_hour = int(match.group(3))
        end_min = int(match.group(4)) if match.group(4) else 0
        
        time_info['start_time'] = f"{start_hour:02d}:{start_min:02d}"
        time_info['end_time'] = f"{end_hour:02d}:{end_min:02d}"
        return time_info
        
    # Search for AM/PM format
    match = re.search(am_pm_pattern, text, re.I)
    if match:
        start_hour = int(match.group(1))
        start_period = match.group(2).lower()
        end_hour = int(match.group(3))
        end_period = match.group(4).lower()
        
        # Convert to 24-hour format
        if start_period == 'pm' and start_hour != 12:
            start_hour += 12
        elif start_period == 'am' and start_hour == 12:
            start_hour = 0
            
        if end_period == 'pm' and end_hour != 12:
            end_hour += 12
        elif end_period == 'am' and end_hour == 12:
            end_hour = 0
            
        time_info['start_time'] = f"{start_hour:02d}:00"
        time_info['end_time'] = f"{end_hour:02d}:00"
        return time_info
        
    return None