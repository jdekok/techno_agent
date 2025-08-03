import re
from datetime import datetime
from typing import List, Optional
from models.event import Event
from scrapers.base_scraper import BaseScraper
from dateutil import parser as date_parser


class ShelterScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            venue_name="Shelter",
            venue_url="https://www.shelteramsterdam.nl"
        )
        
    def scrape_events(self) -> List[Event]:
        """Scrape events from Shelter Amsterdam"""
        events = []
        
        soup = self.fetch_page(self.venue_url)
        if not soup:
            self.logger.error("Failed to fetch Shelter homepage")
            return events
            
        # Find all event links
        event_links = soup.find_all('a', href=re.compile(r'/event/[^/]+/?$'))
        self.logger.info(f"Found {len(event_links)} potential event links")
        
        # Process each event link
        for link in event_links[:10]:  # Limit to prevent overwhelming the server
            event_url = link.get('href')
            if not event_url.startswith('http'):
                event_url = self.venue_url + event_url.rstrip('/')
                
            event = self._scrape_event_detail(event_url)
            if event:
                events.append(event)
                
        # Filter for techno events
        techno_events = self.filter_techno_events(events)
        self.logger.info(f"Found {len(techno_events)} techno events out of {len(events)} total")
        
        return techno_events
        
    def _scrape_event_detail(self, event_url: str) -> Optional[Event]:
        """Scrape detailed information from an event page"""
        soup = self.fetch_page(event_url)
        if not soup:
            return None
            
        try:
            # Extract event name - usually in h1 or title
            title_elem = soup.find('h1') or soup.find('title')
            event_name = title_elem.text.strip() if title_elem else "Unknown Event"
            
            # Try to find date information
            date_str = None
            date_patterns = [
                r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',  # 02.08.2024 or 02/08/2024
                r'(\w+\s+\d{1,2}\s*,?\s*\d{4})',      # August 2, 2024
                r'(\d{1,2}\s+\w+\s+\d{4})',           # 2 August 2024
            ]
            
            # Search for date in common locations
            for pattern in date_patterns:
                date_match = re.search(pattern, soup.text)
                if date_match:
                    date_str = date_match.group(1)
                    break
                    
            # Parse the date
            if date_str:
                try:
                    event_date = date_parser.parse(date_str, fuzzy=True)
                except:
                    event_date = datetime.now()  # Default to now if parsing fails
            else:
                event_date = datetime.now()
                
            # Extract artists - look for lineup or artist mentions
            artists = []
            lineup_section = soup.find(text=re.compile(r'line[\s-]?up', re.I))
            if lineup_section:
                lineup_container = lineup_section.find_parent()
                if lineup_container:
                    # Look for artist names in lists or paragraphs
                    artist_elems = lineup_container.find_all(['li', 'p', 'span'])
                    for elem in artist_elems:
                        text = elem.text.strip()
                        if text and len(text) < 50:  # Reasonable artist name length
                            artists.append(text)
                            
            # Create event object
            return Event(
                venue=self.venue_name,
                venue_url=self.venue_url,
                name=event_name,
                date=event_date,
                url=event_url,
                artists=artists[:10],  # Limit to prevent too many false positives
                description=soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else None
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing event {event_url}: {e}")
            return None