class Event:
    def __init__(
        self,
        id,
        title,
        start,
        end,
        description=None,
        user_id=None,
        source="local",
        google_event_id=None,
        event_type_id=None,
        subject_id=None,
        recurrence_type="none",
        recurrence_interval=1,
        recurrence_unit=None,
        recurrence_days=None,
        recurrence_end_type="never",
        recurrence_end_date=None,
        recurrence_count=None,
        recurrence_rule=None,
    ):
        self.id = id
        self.user_id = user_id

        self.title = title
        self.start = start
        self.end = end
        self.description = description

        self.source = source
        self.google_event_id = google_event_id

        self.event_type_id = event_type_id
        self.subject_id = subject_id

        self.recurrence_type = recurrence_type
        self.recurrence_interval = recurrence_interval
        self.recurrence_unit = recurrence_unit
        self.recurrence_days = recurrence_days or []
        self.recurrence_end_type = recurrence_end_type
        self.recurrence_end_date = recurrence_end_date
        self.recurrence_count = recurrence_count
        self.recurrence_rule = recurrence_rule

    @property
    def is_recurring(self):
        return self.recurrence_type != "none"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "start": self.start.isoformat() if hasattr(self.start, "isoformat") else self.start,
            "end": self.end.isoformat() if hasattr(self.end, "isoformat") else self.end,
            "description": self.description,
            "source": self.source,
            "google_event_id": self.google_event_id,
            "event_type_id": self.event_type_id,
            "subject_id": self.subject_id,
            "is_recurring": self.is_recurring,
            "recurrence": {
                "type": self.recurrence_type,
                "interval": self.recurrence_interval,
                "unit": self.recurrence_unit,
                "days": self.recurrence_days,
                "endType": self.recurrence_end_type,
                "endDate": (
                    self.recurrence_end_date.isoformat()
                    if hasattr(self.recurrence_end_date, "isoformat")
                    else self.recurrence_end_date
                ),
                "count": self.recurrence_count,
                "rule": self.recurrence_rule,
            },
        }