class TimeSlot:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def overlaps(self, other):
        return self.start < other.end and self.end > other.start