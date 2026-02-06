# app/schemas/event.py
from pydantic import BaseModel, Field
from typing import List

class EventSchema(BaseModel):
    event_name: str = Field(description="The official name of the event")
    date: str = Field(description="The event date in format 'Day, Mon DD, YYYY' (e.g., 'Sat, Feb 7, 2026'). MUST be a future date only. Do NOT include any past events.")
    location: str = Field(description="Physical location or 'Online'")
    url: str = Field(description="URL link to the event page")
    speakers: List[str] = Field(description="List of confirmed speaker names")
    is_online: bool = Field(description="True if the event is virtual")

class SpeakerEventsResponse(BaseModel):
    speaker_name: str = Field(description="The name of the speaker being searched for")
    upcoming_events: List[EventSchema] = Field(description="List of future events where this person is speaking")