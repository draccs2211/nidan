import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import pytz

CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
IST = pytz.timezone("Asia/Kolkata")


def get_calendar_service(token_info: dict):
    """Build a Calendar service from stored OAuth token dict."""
    creds = Credentials(
        token=token_info["access_token"],
        refresh_token=token_info.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    service,
    title: str,
    start_dt: datetime,
    duration_minutes: int,
    description: str = "",
    attendees: list[str] = None,
) -> str | None:
    """Create a Google Calendar event. Returns event ID or None on failure."""
    if start_dt.tzinfo is None:
        start_dt = IST.localize(start_dt)

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},
                {"method": "popup", "minutes": 15},
            ],
        },
    }

    if attendees:
        event_body["attendees"] = [{"email": e} for e in attendees]

    try:
        event = service.events().insert(
            calendarId=CALENDAR_ID,
            body=event_body,
            sendUpdates="all",
        ).execute()
        return event.get("id")
    except Exception as e:
        print(f"[Calendar] Failed to create event: {e}")
        return None


def delete_calendar_event(service, event_id: str) -> bool:
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"[Calendar] Failed to delete event {event_id}: {e}")
        return False
