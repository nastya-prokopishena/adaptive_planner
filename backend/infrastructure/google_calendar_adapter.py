import os

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend.domain.interfaces.calendar_provider import CalendarProvider


SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]


class GoogleCalendarAdapter(CalendarProvider):
    def __init__(self):
        self.client_secrets_file = os.getenv(
            "GOOGLE_CLIENT_SECRET_FILE",
            "backend/infrastructure/credentials.json",
        )

        self.redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:5000/callback",
        )

    def create_flow(self):
        return Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )

    def build_service(self, credentials_dict):
        credentials = Credentials(
            token=credentials_dict.get("token"),
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri=credentials_dict.get("token_uri"),
            client_id=credentials_dict.get("client_id"),
            client_secret=credentials_dict.get("client_secret"),
            scopes=credentials_dict.get("scopes"),
        )

        return build("calendar", "v3", credentials=credentials)

    def get_events(self, credentials_dict, single_events=False):
        service = self.build_service(credentials_dict)

        params = {
            "calendarId": "primary",
            "singleEvents": single_events,
        }

        if single_events:
            params["orderBy"] = "startTime"

        result = service.events().list(**params).execute()

        return result.get("items", [])

    def create_event(
        self,
        credentials_dict,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        service = self.build_service(credentials_dict)

        event_body = {
            "summary": title,
            "start": {
                "dateTime": start,
                "timeZone": "Europe/Kyiv",
            },
            "end": {
                "dateTime": end,
                "timeZone": "Europe/Kyiv",
            },
        }

        if recurrence_rule:
            event_body["recurrence"] = [recurrence_rule]

        return service.events().insert(
            calendarId="primary",
            body=event_body,
        ).execute()

    def update_event(
        self,
        credentials_dict,
        event_id,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        service = self.build_service(credentials_dict)

        event = service.events().get(
            calendarId="primary",
            eventId=event_id,
        ).execute()

        event["summary"] = title
        event["start"] = {
            "dateTime": start,
            "timeZone": "Europe/Kyiv",
        }
        event["end"] = {
            "dateTime": end,
            "timeZone": "Europe/Kyiv",
        }

        if recurrence_rule:
            event["recurrence"] = [recurrence_rule]
        else:
            event.pop("recurrence", None)

        return service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event,
        ).execute()

    def delete_event(self, credentials_dict, event_id):
        service = self.build_service(credentials_dict)

        return service.events().delete(
            calendarId="primary",
            eventId=event_id,
        ).execute()