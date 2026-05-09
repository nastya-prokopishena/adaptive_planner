class TimeSlot:
    def __init__(self, start, end):
        if not start or not end:
            raise ValueError("Start and end time are required")

        if end <= start:
            raise ValueError("End time must be later than start time")

        self.start = start
        self.end = end

    def overlaps(self, other):
        return self.start < other.end and self.end > other.start