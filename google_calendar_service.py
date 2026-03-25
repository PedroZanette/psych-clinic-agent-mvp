from __future__ import annotations

import os
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def list_upcoming_events(calendar_id: str = "primary", max_results: int = 20):
    service = get_calendar_service()
    now = datetime.now(timezone.utc).isoformat()

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return result.get("items", [])

def get_event_by_id(calendar_id: str, event_id: str):
    service = get_calendar_service()
    return service.events().get(calendarId=calendar_id, eventId=event_id).execute()


def find_event_by_text(calendar_id: str, text: str, max_results: int = 50):
    service = get_calendar_service()
    now = datetime.now(timezone.utc).isoformat()

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
            q=text,
        )
        .execute()
    )

    events = result.get("items", [])
    return events[0] if events else None


def update_event_time(
    calendar_id: str,
    event_id: str,
    new_start_iso: str,
    new_end_iso: str,
    timezone_str: str = "America/Sao_Paulo",
):
    service = get_calendar_service()

    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    event["start"] = {
        "dateTime": new_start_iso,
        "timeZone": timezone_str,
    }
    event["end"] = {
        "dateTime": new_end_iso,
        "timeZone": timezone_str,
    }

    updated_event = (
        service.events()
        .update(calendarId=calendar_id, eventId=event_id, body=event)
        .execute()
    )

    return updated_event