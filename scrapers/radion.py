import re
from datetime import datetime
from typing import List, Optional
from models.event import Event
from scrapers.base_scraper import BaseScraper
from dateutil import parser as date_parser


class RadionScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            venue_name="Radion",
            venue_url="https://radion.amsterdam"
        )
        
    def scrape_events(self) -> List[Event]:
        """Scrape events from Radion Amsterdam"""
        events = []
        
        # Try the program page
        program_url = f"{self.venue_url}/program"
        soup = self.fetch_page(program_url)
        if not soup:
            self.logger.error("Failed to fetch Radion program page")
            return events
            
        # Look for event cards or listings
        # Common patterns for event containers
        event_containers = (
            soup.find_all('article', class_=re.compile(r'event|card')) or
            soup.find_all('div', class_=re.compile(r'event|card|item')) or
            soup.find_all('a', class_=re.compile(r'event|card'))
        )
        
        self.logger.info(f"Found {len(event_containers)} potential event containers")
        
        for container in event_containers[:15]:  # Limit to prevent overwhelming
            event = self._parse_event_container(container)
            if event:
                events.append(event)
                
        # If we found events through containers, filter for techno
        if events:
            techno_events = self.filter_techno_events(events)
            self.logger.info(f"Found {len(techno_events)} techno events out of {len(events)} total")
            return techno_events
            
        # Alternative: look for event links
        event_links = soup.find_all('a', href=re.compile(r'/event/|/program/'))
        self.logger.info(f"Found {len(event_links)} event links as fallback")
        
        for link in event_links[:10]:
            event_url = link.get('href')
            if not event_url.startswith('http'):
                event_url = self.venue_url + event_url
                
            event = self._scrape_event_detail(event_url)
            if event:
                events.append(event)
                
        techno_events = self.filter_techno_events(events)
        self.logger.info(f"Found {len(techno_events)} techno events")
        return techno_events
        
    def _parse_event_container(self, container) -> Optional[Event]:
        """Parse event information from a container element"""
        try:
            # Extract event name
            name_elem = (
                container.find(['h2', 'h3', 'h4']) or
                container.find(class_=re.compile(r'title|name|heading'))
            )
            event_name = name_elem.text.strip() if name_elem else None
            
            if not event_name:
                # Try to get text from the container itself
                event_name = container.text.strip()[:100]
                
            # Extract date
            date_str = None
            date_elem = (
                container.find(class_=re.compile(r'date|when|time')) or
                container.find(text=re.compile(r'\d{1,2}[\s\-/]\w+'))
            )
            
            if date_elem:
                date_str = date_elem.text if hasattr(date_elem, 'text') else str(date_elem)
            else:
                # Look for date patterns in the container text
                date_match = re.search(
                    r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}[./]\d{1,2}[./]\d{2,4})',
                    container.text
                )
                if date_match:
                    date_str = date_match.group(1)
                    
            # Parse date
            event_date = datetime.now()  # Default
            if date_str:
                try:
                    event_date = date_parser.parse(date_str, fuzzy=True)
                    # If parsed date is in the past and doesn't have year, assume next year
                    if event_date < datetime.now() and event_date.year == datetime.now().year:
                        event_date = event_date.replace(year=datetime.now().year + 1)
                except:
                    pass
                    
            # Get event URL
            link = container.find('a') if container.name != 'a' else container
            event_url = link.get('href') if link else None
            if event_url and not event_url.startswith('http'):
                event_url = self.venue_url + event_url
                
            # Extract category/type
            category_elem = container.find(class_=re.compile(r'category|type|tag'))
            description = category_elem.text.strip() if category_elem else None
            
            return Event(
                venue=self.venue_name,
                venue_url=self.venue_url,
                name=event_name,
                date=event_date,
                url=event_url,
                description=description
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing event container: {e}")
            return None
            
    def _scrape_event_detail(self, event_url: str) -> Optional[Event]:
        """Scrape detailed information from an event page"""
        soup = self.fetch_page(event_url)
        if not soup:
            return None
            
        try:
            # Extract event name
            title_elem = soup.find('h1') or soup.find('title')
            event_name = title_elem.text.strip() if title_elem else "Unknown Event"
            
            # Extract date
            date_elem = soup.find(class_=re.compile(r'date|when|time'))
            event_date = datetime.now()
            
            if date_elem:
                try:
                    event_date = date_parser.parse(date_elem.text.strip(), fuzzy=True)
                except:
                    pass
                    
            # Extract artists from lineup
            artists = []
            lineup_container = soup.find(text=re.compile(r'line[\s-]?up', re.I))
            if lineup_container:
                parent = lineup_container.find_parent()
                if parent:
                    artist_elems = parent.find_all(['li', 'p', 'div'])
                    for elem in artist_elems:
                        text = elem.text.strip()
                        if text and 10 < len(text) < 50:
                            artists.append(text)
                            
            # Get description
            desc_elem = soup.find('meta', {'name': 'description'})
            description = desc_elem.get('content') if desc_elem else None
            
            return Event(
                venue=self.venue_name,
                venue_url=self.venue_url,
                name=event_name,
                date=event_date,
                url=event_url,
                artists=artists[:10],
                description=description
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing event detail {event_url}: {e}")
            return None