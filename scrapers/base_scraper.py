import time
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from models.event import Event


class BaseScraper(ABC):
    def __init__(self, venue_name: str, venue_url: str):
        self.venue_name = venue_name
        self.venue_url = venue_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.logger = logging.getLogger(f"{__name__}.{venue_name}")
        
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Fetching {url} (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                # Rate limiting - wait 2 seconds between requests
                time.sleep(2)
                
                return BeautifulSoup(response.content, 'lxml')
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    return None
                    
    @abstractmethod
    def scrape_events(self) -> List[Event]:
        """Scrape events from the venue website"""
        pass
    
    def filter_techno_events(self, events: List[Event]) -> List[Event]:
        """Filter events to only include techno-related ones"""
        techno_keywords = [
            'techno', 'tech-house', 'minimal', 'electronic', 'acid',
            'industrial', 'rave', 'warehouse', 'underground', 'dub techno',
            'hard techno', 'ambient techno', 'detroit techno'
        ]
        
        filtered = []
        for event in events:
            # Check event name and description for techno keywords
            text_to_check = f"{event.name} {event.description or ''}".lower()
            if any(keyword in text_to_check for keyword in techno_keywords):
                filtered.append(event)
            # Also check artist names
            elif any(keyword in ' '.join(event.artists).lower() for keyword in techno_keywords):
                filtered.append(event)
                
        return filtered