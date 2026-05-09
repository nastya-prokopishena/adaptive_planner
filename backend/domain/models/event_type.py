class EventType:
    def __init__(
        self,
        id,
        user_id,
        name,
        color=None,
        is_default=False,
        created_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.color = color
        self.is_default = is_default
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "color": self.color,
            "is_default": self.is_default,
            "created_at": (
                self.created_at.isoformat()
                if hasattr(self.created_at, "isoformat")
                else self.created_at
            ),
        }