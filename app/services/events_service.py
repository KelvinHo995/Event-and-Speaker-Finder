# app/services/firecrawl_service.py
import os
import asyncio
from datetime import datetime
from dateutil import parser as date_parser
from firecrawl import Firecrawl
from app.schemas.event import SpeakerEventsResponse

app_firecrawl = Firecrawl(api_key=os.getenv('FIRECRAWL_KEY'))

TARGET_DOMAINS = [
    "lu.ma",
    "meetup.com",
    "eventbrite.com",
]

def is_future_event(event):
    """
    Check if an event is in the future.
    
    Args:
        event: Event dictionary with 'date' field
        
    Returns:
        True if event is in the future or date cannot be parsed, False otherwise
    """
    try:
        event_date_str = event.get('date', '')
        if event_date_str:
            event_date = date_parser.parse(event_date_str, fuzzy=True)
            current_date = datetime.now()
            
            if event_date.date() < current_date.date():
                print(f"DEBUG: Skipping past event: {event.get('event_name')} on {event_date_str}")
                return False
        return True
    except Exception as e:
        print(f"WARNING: Could not parse date '{event.get('date', '')}': {e}")
        return True  # Benefit of doubt

def remove_duplicate_events(events):
    """
    Remove duplicate events based on event_name and date.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        List of unique events
    """
    unique_events = []
    seen = set()
    
    for event in events:
        event_key = (event.get('event_name', ''), event.get('date', ''))
        if event_key not in seen:
            seen.add(event_key)
            unique_events.append(event)
    
    return unique_events

def filter_events_by_type(events, event_filter):
    """
    Filter events by type (in-person or online).
    
    Args:
        events: List of event dictionaries
        event_filter: Filter string - 'in-person' or 'online', or None
        
    Returns:
        Filtered list of events
    """
    if not event_filter:
        return events
    
    if event_filter.lower() == 'in-person':
        filtered = [event for event in events if not event.get('is_online', False)]
    elif event_filter.lower() == 'online':
        filtered = [event for event in events if event.get('is_online', False)]
    else:
        filtered = events
    
    print(f"DEBUG: After filtering for '{event_filter}': {len(filtered)} events")
    return filtered

def parse_event_date(event):
    """
    Parse event date for sorting.
    
    Args:
        event: Event dictionary with 'date' field
        
    Returns:
        Parsed datetime object or datetime.max if parsing fails
    """
    try:
        date_str = event.get('date', '')
        return date_parser.parse(date_str, fuzzy=True)
    except:
        return datetime.max  # Put unparseable dates at the end

async def find_event_details(speaker_name: str, event_filter: str = None):
    """
    Finds upcoming events for a specific public speaker.
    
    Args:
        speaker_name: Name of the speaker to search for
        event_filter: Optional filter - 'in-person' or 'online'
    """
    # 1. Build Query: "(site:lu.ma OR ...) "Andrew Ng" speaking schedule"
    site_restriction = " OR ".join([f"site:{d}" for d in TARGET_DOMAINS])
    search_term = f"({site_restriction}) \"{speaker_name}\""

    # search_term = "firecrawl"
    print(f"DEBUG: Searching for: {search_term}")

    try:
        # Step A: Search for the speaker's schedule
        search_result = await asyncio.to_thread(
            app_firecrawl.search,
            query=search_term,
            limit=5,
        )
            
        if not search_result or not hasattr(search_result, 'web') or not search_result.web:
            return {"speaker_name": speaker_name, "upcoming_events": []}
        
        results_list = search_result.web
        if not results_list:
            return {"speaker_name": speaker_name, "upcoming_events": []}
        
        print(f"DEBUG: Found {len(results_list)} web URLs")

        # Step B: Batch scrape all web URLs to find events
        all_events = []
        urls = [result.url if hasattr(result, 'url') else result.get('url') for result in results_list]
        
        print(f"DEBUG: Starting batch scrape for {len(urls)} URLs")
        
        # Get today's date for the prompt
        today = datetime.now().strftime('%B %d, %Y')
        
        try:
            # Submit batch scrape job
            batch_results = await asyncio.to_thread(
                app_firecrawl.batch_scrape,
                urls=urls,
                formats=[{
                    'type': "json",
                    'schema': SpeakerEventsResponse.model_json_schema(),
                    'prompt': f"Today is {today}. Extract ONLY upcoming events (events on or after {today}) where {speaker_name} is listed as a speaker. {speaker_name} MUST be in the speakers list. Ignore all past events."
                }],
            )

            # Process results   
            # if batch_results and hasattr(batch_results, 'data'):
            for result in batch_results.data:
                try:
                    if result.json:
                        extracted_data = result.json
                        print(extracted_data)
                        if extracted_data and 'upcoming_events' in extracted_data:
                            all_events.extend(extracted_data['upcoming_events'])
                            url = result.metadata.url if hasattr(result, 'metadata') and hasattr(result.metadata, 'url') else 'unknown'
                            print(f"DEBUG: Found {len(extracted_data['upcoming_events'])} events from {url}")
                except Exception as e:
                    print(f"ERROR: Failed to process batch result: {e}")
                    continue
        except Exception as e:
            print(f"ERROR: Batch scrape failed: {e}")
        
        # Filter out past events
        future_events = [event for event in all_events if is_future_event(event)]
        
        # Remove duplicates
        unique_events = remove_duplicate_events(future_events)
        print(f"DEBUG: Total unique future events found: {len(unique_events)}")
        
        # Filter by event type (in-person/online)
        filtered_events = filter_events_by_type(unique_events, event_filter)
        
        # Sort by date
        filtered_events.sort(key=parse_event_date)
        print(f"DEBUG: Events sorted by date")
        
        return {
            "speaker_name": speaker_name,
            "upcoming_events": filtered_events
        }

    except Exception as e:
        print(f"Error in firecrawl_service: {e}")
        raise e