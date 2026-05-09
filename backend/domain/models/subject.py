class Subject:
    def __init__(
        self,
        id,
        user_id,
        name,
        teacher=None,
        description=None,
        color=None,
        created_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.teacher = teacher
        self.description = description
        self.color = color
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "teacher": self.teacher,
            "description": self.description,
            "color": self.color,
            "created_at": (
                self.created_at.isoformat()
                if hasattr(self.created_at, "isoformat")
                else self.created_at
            ),
        }