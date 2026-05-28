from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter


class ScheduleService:
    def __init__(self, calendar_provider=None):
        self.calendar_provider = calendar_provider or GoogleCalendarAdapter()

    def get_google_events(self, creds_dict, single_events=False):
        return self.calendar_provider.get_events(
            credentials_dict=creds_dict,
            single_events=single_events,
        )

    def create_google_event(
        self,
        creds_dict,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        return self.calendar_provider.create_event(
            credentials_dict=creds_dict,
            title=title,
            start=start,
            end=end,
            recurrence_rule=recurrence_rule,
        )

    def update_google_event(
        self,
        creds_dict,
        event_id,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        return self.calendar_provider.update_event(
            credentials_dict=creds_dict,
            event_id=event_id,
            title=title,
            start=start,
            end=end,
            recurrence_rule=recurrence_rule,
        )

    def delete_google_event(self, creds_dict, event_id):
        return self.calendar_provider.delete_event(
            credentials_dict=creds_dict,
            event_id=event_id,
        )