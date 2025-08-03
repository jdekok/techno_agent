#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.event import Event
from scrapers.shelter import ShelterScraper
from scrapers.radion import RadionScraper
from scrapers.lofi import LofiScraper
from utils.email_sender import send_email, save_events_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TechnoEventAggregator:
    def __init__(self):
        self.scrapers = [
            ShelterScraper(),
            RadionScraper(),
            LofiScraper(),
        ]
        
    def scrape_all_venues(self) -> List[Event]:
        """Scrape events from all configured venues"""
        all_events = []
        
        for scraper in self.scrapers:
            logger.info(f"Scraping {scraper.venue_name}...")
            try:
                events = scraper.scrape_events()
                logger.info(f"Found {len(events)} events from {scraper.venue_name}")
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Error scraping {scraper.venue_name}: {e}")
                
        return all_events
        
    def filter_upcoming_events(self, events: List[Event], days: int = 7) -> List[Event]:
        """Filter events to only include those in the next N days"""
        cutoff_date = datetime.now() + timedelta(days=days)
        upcoming = [e for e in events if datetime.now() <= e.date <= cutoff_date]
        return sorted(upcoming, key=lambda e: e.date)
        
    def deduplicate_events(self, events: List[Event]) -> List[Event]:
        """Remove duplicate events based on venue, name, and date"""
        seen = set()
        unique_events = []
        
        for event in events:
            event_key = (event.venue, event.name.lower(), event.date.date())
            if event_key not in seen:
                seen.add(event_key)
                unique_events.append(event)
                
        return unique_events


def main():
    parser = argparse.ArgumentParser(description='Amsterdam Techno Event Aggregator')
    parser.add_argument('--email', help='Email address to send results to')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look ahead (default: 7)')
    parser.add_argument('--output', choices=['email', 'json', 'both'], default='json',
                       help='Output format (default: json)')
    parser.add_argument('--json-file', default='events.json', help='JSON output filename')
    
    args = parser.parse_args()
    
    # Initialize aggregator
    aggregator = TechnoEventAggregator()
    
    # Scrape all venues
    logger.info("Starting techno event aggregation...")
    all_events = aggregator.scrape_all_venues()
    
    # Deduplicate
    unique_events = aggregator.deduplicate_events(all_events)
    logger.info(f"Total unique events found: {len(unique_events)}")
    
    # Filter to upcoming events
    upcoming_events = aggregator.filter_upcoming_events(unique_events, days=args.days)
    logger.info(f"Upcoming events in next {args.days} days: {len(upcoming_events)}")
    
    # Output results
    if args.output in ['json', 'both']:
        save_events_json(upcoming_events, args.json_file)
        logger.info(f"Saved events to {args.json_file}")
        
    if args.output in ['email', 'both'] and args.email:
        # Check if running in GitHub Actions
        if os.getenv('GITHUB_ACTIONS'):
            logger.info("Running in GitHub Actions, using secrets for SMTP")
            
        success = send_email(upcoming_events, args.email)
        if success:
            logger.info(f"Email sent to {args.email}")
        else:
            logger.error("Failed to send email")
            
    # Print summary
    print(f"\n{'='*50}")
    print(f"TECHNO EVENTS SUMMARY - Next {args.days} days")
    print(f"{'='*50}")
    
    for event in upcoming_events[:10]:  # Show first 10
        print(f"\n📅 {event.date.strftime('%a %b %d, %H:%M')}")
        print(f"📍 {event.venue}: {event.name}")
        if event.artists:
            print(f"🎧 {', '.join(event.artists[:3])}")
            
    if len(upcoming_events) > 10:
        print(f"\n... and {len(upcoming_events) - 10} more events")
        
    print(f"\n{'='*50}")
    
    # Exit with appropriate code
    sys.exit(0 if upcoming_events else 1)


if __name__ == "__main__":
    main()