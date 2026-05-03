from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from backend.infrastructure.db.repositories.event_repo import EventRepository
from backend.infrastructure.cache.redis_client import redis_client
from datetime import datetime
import json

event_repo = EventRepository()


class ScheduleService:

    def build_service(self, creds_dict):

        creds = Credentials(
            token=creds_dict["token"],
            refresh_token=creds_dict["refresh_token"],
            token_uri=creds_dict["token_uri"],
            client_id=creds_dict["client_id"],
            client_secret=creds_dict["client_secret"],
            scopes=creds_dict["scopes"]
        )

        return build("calendar", "v3", credentials=creds)

    def get_google_events(self, creds_dict):
        service = self.build_service(creds_dict)

        result = service.events().list(
            calendarId="primary",
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = result.get("items", [])

        return events

    def create_google_event(self, creds_dict, title, start, end):

        service = self.build_service(creds_dict)

        event_body = {
            "summary": title,
            "start": {"dateTime": start, "timeZone": "Europe/Kyiv"},
            "end": {"dateTime": end, "timeZone": "Europe/Kyiv"}
        }

        created_event = service.events().insert(
            calendarId="primary",
            body=event_body
        ).execute()

        return created_event