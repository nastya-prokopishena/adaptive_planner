import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.oauth2.credentials

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarAdapter:

    def __init__(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.client_secrets_file = os.path.abspath(
            os.path.join(BASE_DIR, "../credentials.json")
        )

        self.redirect_uri = "http://127.0.0.1:5000/callback"

    def create_flow(self):
        return Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri
        )

    def build_service(self, credentials_dict):
        credentials = google.oauth2.credentials.Credentials(**credentials_dict)
        return build('calendar', 'v3', credentials=credentials)

    # ⬇️ ДОДАЙ ЦЕЙ МЕТОД
    def create_event(self, credentials_dict, summary, start_time, end_time):
        service = self.build_service(credentials_dict)

        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Kyiv',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Kyiv',
            },
        }

        return service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

    def get_events(self, credentials_dict):
        service = self.build_service(credentials_dict)

        events_result = service.events().list(
            calendarId='primary',
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    def update_event(self, creds_dict, event_id, start, end):
        creds = Credentials(**creds_dict)
        service = build("calendar", "v3", credentials=creds)

        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        event["start"]["dateTime"] = start
        event["end"]["dateTime"] = end

        updated_event = service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event
        ).execute()

        return updated_event