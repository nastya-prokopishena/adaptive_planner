from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class ScheduleService:
    def build_service(self, creds_dict):
        creds = Credentials(
            token=creds_dict.get("token"),
            refresh_token=creds_dict.get("refresh_token"),
            token_uri=creds_dict.get("token_uri"),
            client_id=creds_dict.get("client_id"),
            client_secret=creds_dict.get("client_secret"),
            scopes=creds_dict.get("scopes"),
        )

        return build("calendar", "v3", credentials=creds)

    def get_google_events(self, creds_dict, single_events=False):
        service = self.build_service(creds_dict)

        request_params = {
            "calendarId": "primary",
            "singleEvents": single_events,
        }

        if single_events:
            request_params["orderBy"] = "startTime"

        result = service.events().list(**request_params).execute()

        return result.get("items", [])

    def create_google_event(self, creds_dict, title, start, end, recurrence_rule=None):
        service = self.build_service(creds_dict)

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

    def update_google_event(
        self,
        creds_dict,
        event_id,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        service = self.build_service(creds_dict)

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

    def delete_google_event(self, creds_dict, event_id):
        service = self.build_service(creds_dict)

        return service.events().delete(
            calendarId="primary",
            eventId=event_id,
        ).execute()