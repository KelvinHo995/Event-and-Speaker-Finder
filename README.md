# Event and Speaker Finder

A Flask-based API service that searches for upcoming events featuring specific speakers across major event platforms.

## Features

- 🔍 Search events by speaker name
- 🌐 Scrapes multiple event platforms (lu.ma, meetup.com, eventbrite.com)
- 📅 Automatic filtering of past events
- 🏢 Filter by event type (in-person or online)
- ⚡ Async batch scraping with Firecrawl
- 📊 Returns structured event data (name, date, location, URL, speakers)

## Installation

1. Clone the repository

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Firecrawl API key:
   ```
   FIRECRAWL_KEY=your_api_key_here
   PORT=5000
   ```

## Usage

### Start the server

```bash
flask --app run.py run --debug
```

### API Endpoints

#### Search for events by speaker

```http
GET /events/search?name={speaker_name}&filter={filter_type}
```

**Parameters:**
- `name` (required): Speaker name to search for
- `filter` (optional): Event type filter - `in-person` or `online`

**Example:**
```http
GET /events/search?name=Nhat%20Nguyen&filter=in-person
```

**Response:**
```json
{
  "speaker_name": "Nhat Nguyen",
  "upcoming_events": [
    {
      "event_name": "HCMC Data Meetup #31",
      "date": "Sat, Feb 7, 2026",
      "location": "Foundry AI Academy, Ho Chi Minh City, VN",
      "url": "https://www.meetup.com/...",
      "speakers": ["Nhat Nguyen"],
      "is_online": false
    }
  ]
}
```

## Project Structure

```
EventAndSpeakerFinder/
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   └── events.py          # API endpoints
│   ├── schemas/
│   │   └── event.py           # Pydantic schemas
│   └── services/
│       └── events_service.py  # Core business logic
├── run.py                      # Flask app entry point
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

## How It Works

1. **Search**: Queries event platforms using Firecrawl's search API
2. **Scrape**: Batch scrapes event pages to extract structured data
3. **Filter**: Removes past events and filters by event type
4. **Sort**: Orders events chronologically
5. **Return**: Provides clean JSON response with event details

## Technologies

- **Flask**: Web framework with async support
- **Firecrawl**: Web scraping and data extraction
- **Pydantic**: Data validation and schema definition
- **python-dateutil**: Date parsing and validation

## License

MIT
