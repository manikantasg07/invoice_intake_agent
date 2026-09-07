from decimal import Decimal
from dotenv import load_dotenv
import json
import os
import anthropic 
from anthropic import beta_tool
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential
from datetime import date


load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("API_KEY"))


@beta_tool
def create_calendar_event(
        title: str,
        start:str,
        end:str,
        attendees:list[str] | None = None,
        recurrence:dict | None = None,
)->str:
    """Create a calendar event with attendees and optional recurrence.

    Args:
        title: Event title.
        start: Start time in ISO 8601 format.
        end: End time in ISO 8601 format.
        attendees: Email addresses to invite.
        recurrence: Dict with 'frequency' (daily, weekly, monthly) and 'count'.
    """
    if attendees and len(attendees) > 10:
        raise ValueError("Too many attendees (max 10)")
    return json.dumps({"event_id": "evt_123", "status": "created", "title": title})


@beta_tool
def list_calendar_events(date: str) -> str:
    """List all calendar events on a given date.

    Args:
        date: Date in YYYY-MM-DD format.
    """
    return json.dumps({"events": [{"title": "Existing meeting", "start": "14:00", "end": "15:00"}]})

final_message = client.beta.messages.tool_runner(
    model="claude-opus-5",
    max_tokens=1024,
    system="You are a helpful assistant that can manage calendar events. and todays date is " + str(date.today()),
    tools=[create_calendar_event, list_calendar_events],
    messages=[
        {
            "role": "user",
            "content": "Schedule an all-hands with everyone tomorrow: " + ", ".join(f"user{i}@example.com" for i in range(15)),
        }
    ],
).until_done()


for block in final_message.content:
    if block.type == "text":
        print(block.text)