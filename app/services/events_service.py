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
    print(f"DEBUG: Running Hybrid Search for: {speaker_name}")

    try:
        # Step A: Define two search strategies
        
        # Strategy 1: Targeted Platform Search
        # Search specifically on known event platforms
        site_restriction = " OR ".join([f"site:{d}" for d in TARGET_DOMAINS])
        query_targeted = f"({site_restriction}) \"{speaker_name}\""
        
        # Strategy 2: Broad Discovery Search
        # Search everywhere else, excluding the known platforms
        site_exclusion = " ".join([f"-site:{d}" for d in TARGET_DOMAINS])
        query_broad = f"\"{speaker_name}\" speaker upcoming events {site_exclusion}"
        
        print(f"DEBUG: Targeted query: {query_targeted}")
        print(f"DEBUG: Broad query: {query_broad}")
        
        # Step B: Run both searches in parallel
        task_targeted = asyncio.to_thread(
            app_firecrawl.search,
            query=query_targeted,
            limit=3,
        )
        task_broad = asyncio.to_thread(
            app_firecrawl.search,
            query=query_broad,
            limit=3,
        )
        
        results_targeted, results_broad = await asyncio.gather(task_targeted, task_broad)
        
        # Step C: Combine and deduplicate URLs
        def collect_urls(result_obj):
            """Helper to safely extract URLs from search results"""
            if not result_obj:
                return []
            
            # Handle both dict and object responses
            if hasattr(result_obj, 'web'):
                web_results = result_obj.web
            elif isinstance(result_obj, dict) and 'web' in result_obj:
                web_results = result_obj['web']
            else:
                return []
            
            if not web_results:
                return []
            
            # Extract URLs from results
            urls = []
            for item in web_results:
                url = item.url if hasattr(item, 'url') else item.get('url') if isinstance(item, dict) else None
                if url:
                    urls.append(url)
            return urls
        
        all_urls = []
        all_urls.extend(collect_urls(results_targeted))
        all_urls.extend(collect_urls(results_broad))
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(all_urls))
        
        print(f"DEBUG: Targeted search found: {len(collect_urls(results_targeted))} URLs")
        print(f"DEBUG: Broad search found: {len(collect_urls(results_broad))} URLs")
        print(f"DEBUG: Combined unique URLs: {len(unique_urls)}")
        
        if not unique_urls:
            return {"speaker_name": speaker_name, "upcoming_events": []}
        
        # Step D: Batch scrape all unique URLs to find events
        all_events = []
        
        print(f"DEBUG: Starting batch scrape for {len(unique_urls)} URLs")
        
        today = datetime.now().strftime('%B %d, %Y')
        
        try:
            batch_results = await asyncio.to_thread(
                app_firecrawl.batch_scrape,
                urls=unique_urls,
                formats=[{
                    'type': "json",
                    'schema': SpeakerEventsResponse.model_json_schema(),
                    'prompt': f"Today is {today}. Extract ONLY upcoming events (events on or after {today}) where {speaker_name} is listed as a speaker. {speaker_name} MUST be in the speakers list. Ignore all past events."
                }],
            )

            for result in batch_results.data:
                try:
                    if result.json:
                        extracted_data = result.json
                        if extracted_data and 'upcoming_events' in extracted_data:
                            all_events.extend(extracted_data['upcoming_events'])
                            url = result.metadata.url if hasattr(result, 'metadata') and hasattr(result.metadata, 'url') else 'unknown'
                            print(f"DEBUG: Found {len(extracted_data['upcoming_events'])} events from {url}")
                except Exception as e:
                    print(f"ERROR: Failed to process batch result: {e}")
                    continue

        except Exception as e:
            print(f"ERROR: Batch scrape failed: {e}")
        
        future_events = [event for event in all_events if is_future_event(event)]
        
        unique_events = remove_duplicate_events(future_events)
        print(f"DEBUG: Total unique future events found: {len(unique_events)}")
        
        filtered_events = filter_events_by_type(unique_events, event_filter)
        
        filtered_events.sort(key=parse_event_date)
        print(f"DEBUG: Events sorted by date")
        
        return {
            "speaker_name": speaker_name,
            "upcoming_events": filtered_events
        }

    except Exception as e:
        print(f"Error in firecrawl_service: {e}")
        raise e