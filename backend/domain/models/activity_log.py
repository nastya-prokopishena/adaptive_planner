class TaskActivityLog:
    def __init__(
        self,
        id,
        user_id,
        task_id,
        action,
        old_status=None,
        new_status=None,
        details=None,
        created_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.task_id = task_id
        self.action = action
        self.old_status = old_status
        self.new_status = new_status
        self.details = details
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "action": self.action,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "details": self.details,
            "created_at": (
                self.created_at.isoformat()
                if hasattr(self.created_at, "isoformat")
                else self.created_at
            ),
        }