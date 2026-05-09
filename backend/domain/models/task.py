class Task:
    STATUS_PLANNED = "planned"
    STATUS_DONE = "done"
    STATUS_MISSED = "missed"

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"

    def __init__(
        self,
        id,
        user_id,
        title,
        description=None,
        event_id=None,
        subject_id=None,
        status="planned",
        priority="medium",
        due_date=None,
        completed_at=None,
        missed_at=None,
        created_at=None,
        updated_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.subject_id = subject_id

        self.title = title
        self.description = description

        self.status = status
        self.priority = priority

        self.due_date = due_date
        self.completed_at = completed_at
        self.missed_at = missed_at

        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def is_done(self):
        return self.status == self.STATUS_DONE

    @property
    def is_missed(self):
        return self.status == self.STATUS_MISSED

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "subject_id": self.subject_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": (
                self.due_date.isoformat()
                if hasattr(self.due_date, "isoformat")
                else self.due_date
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if hasattr(self.completed_at, "isoformat")
                else self.completed_at
            ),
            "missed_at": (
                self.missed_at.isoformat()
                if hasattr(self.missed_at, "isoformat")
                else self.missed_at
            ),
            "created_at": (
                self.created_at.isoformat()
                if hasattr(self.created_at, "isoformat")
                else self.created_at
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if hasattr(self.updated_at, "isoformat")
                else self.updated_at
            ),
        }