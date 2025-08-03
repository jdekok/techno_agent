import re
from datetime import datetime
from typing import List, Optional
from models.event import Event
from scrapers.base_scraper import BaseScraper
from dateutil import parser as date_parser


class LofiScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            venue_name="Lofi",
            venue_url="https://lofi.amsterdam"
        )
        
    def scrape_events(self) -> List[Event]:
        """Scrape events from Lofi Amsterdam"""
        events = []
        
        # Try the events page
        events_url = f"{self.venue_url}/events/"
        soup = self.fetch_page(events_url)
        if not soup:
            self.logger.error("Failed to fetch Lofi events page")
            return events
            
        # Look for event containers - common patterns
        event_containers = (
            soup.find_all('article', class_=re.compile(r'event')) or
            soup.find_all('div', class_=re.compile(r'event-item|event-card')) or
            soup.find_all('li', class_=re.compile(r'event'))
        )
        
        self.logger.info(f"Found {len(event_containers)} potential event containers")
        
        # If we found containers, parse them
        if event_containers:
            for container in event_containers[:20]:  # Process up to 20 events
                event = self._parse_event_container(container)
                if event:
                    events.append(event)
        else:
            # Fallback: look for event links
            event_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if '/event/' in href or '/events/' in href and href != events_url:
                    event_links.append(link)
                    
            self.logger.info(f"Found {len(event_links)} event links as fallback")
            
            for link in event_links[:15]:
                event_url = link.get('href')
                if not event_url.startswith('http'):
                    event_url = self.venue_url + event_url
                    
                # Try to extract basic info from the link
                event = self._parse_event_link(link, event_url)
                if event:
                    events.append(event)
                    
        # Filter for techno events
        techno_events = self.filter_techno_events(events)
        self.logger.info(f"Found {len(techno_events)} techno events out of {len(events)} total")
        
        return techno_events
        
    def _parse_event_container(self, container) -> Optional[Event]:
        """Parse event information from a container element"""
        try:
            # Extract event name
            name_elem = None
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
                name_elem = container.find(tag)
                if name_elem:
                    break
                    
            if not name_elem:
                name_elem = container.find(class_=re.compile(r'title|name|event-name'))
                
            event_name = name_elem.text.strip() if name_elem else ""
            
            # Extract date - Lofi often uses various formats
            date_str = None
            date_patterns = [
                r'(\d{1,2}\s+\w+\s+\d{4})',  # 3 August 2025
                r'(\w+\s+\d{1,2},?\s+\d{4})', # August 3, 2025
                r'(\d{1,2}[./]\d{1,2}[./]\d{4})', # 03/08/2025
                r'(\d{1,2}\s+\w{3}\s+\d{4})',  # 3 Aug 2025
            ]
            
            # Look for date in specific elements first
            date_elem = container.find(class_=re.compile(r'date|when|time'))
            if date_elem:
                date_str = date_elem.text.strip()
            else:
                # Search the whole container text
                for pattern in date_patterns:
                    match = re.search(pattern, container.text)
                    if match:
                        date_str = match.group(1)
                        break
                        
            # Parse date
            event_date = datetime.now()
            if date_str:
                try:
                    event_date = date_parser.parse(date_str, fuzzy=True)
                    # Adjust year if date is in the past
                    if event_date < datetime.now() and event_date.year == datetime.now().year:
                        event_date = event_date.replace(year=datetime.now().year + 1)
                except:
                    self.logger.warning(f"Could not parse date: {date_str}")
                    
            # Get event URL
            link = container.find('a')
            event_url = None
            if link and link.get('href'):
                event_url = link.get('href')
                if not event_url.startswith('http'):
                    event_url = self.venue_url + event_url
                    
            # Extract venue location (Club, Courtyard, Colorfloor)
            location_elem = container.find(class_=re.compile(r'location|venue|room'))
            location = location_elem.text.strip() if location_elem else None
            
            # Extract artists - often in the event name or separate elements
            artists = []
            # Common patterns in event names
            if event_name:
                # Look for patterns like "Artist1 b2b Artist2" or "Artist1, Artist2"
                artist_patterns = [
                    r'presents?\s+(.+?)(?:\s+\||$)',
                    r'invites?\s+(.+?)(?:\s+\||$)',
                    r':\s*(.+?)(?:\s+\||$)',
                ]
                for pattern in artist_patterns:
                    match = re.search(pattern, event_name, re.I)
                    if match:
                        artist_string = match.group(1)
                        # Split by common separators
                        artist_list = re.split(r'\s*[,&]\s*|\s+b2b\s+|\s+x\s+', artist_string)
                        artists.extend([a.strip() for a in artist_list if a.strip()])
                        break
                        
            # Build description
            description_parts = []
            if location:
                description_parts.append(f"Location: {location}")
            
            # Look for age restriction
            age_match = re.search(r'(\d+)\+', container.text)
            if age_match:
                description_parts.append(f"Age: {age_match.group(0)}")
                
            description = " | ".join(description_parts) if description_parts else None
            
            return Event(
                venue=self.venue_name,
                venue_url=self.venue_url,
                name=event_name or "Unknown Event",
                date=event_date,
                url=event_url,
                artists=artists[:10],
                description=description
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing event container: {e}")
            return None
            
    def _parse_event_link(self, link, event_url: str) -> Optional[Event]:
        """Parse basic event info from a link element"""
        try:
            # Get text from the link
            link_text = link.text.strip()
            if not link_text:
                return None
                
            # Try to extract date from the link text or nearby elements
            event_date = datetime.now()
            parent = link.find_parent()
            if parent:
                date_match = re.search(
                    r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})',
                    parent.text
                )
                if date_match:
                    try:
                        event_date = date_parser.parse(date_match.group(1), fuzzy=True)
                    except:
                        pass
                        
            return Event(
                venue=self.venue_name,
                venue_url=self.venue_url,
                name=link_text[:100],  # Limit length
                date=event_date,
                url=event_url
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing event link: {e}")
            return None