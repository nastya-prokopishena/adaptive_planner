class Event:
    def __init__(self, id, title, start, end, description=None):
        self.id = id
        self.title = title
        self.start = start
        self.end = end
        self.description = description