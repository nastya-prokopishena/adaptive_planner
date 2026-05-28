from abc import ABC, abstractmethod


class CalendarProvider(ABC):
    @abstractmethod
    def create_flow(self):
        pass

    @abstractmethod
    def get_events(self, credentials_dict, single_events=False):
        pass

    @abstractmethod
    def create_event(
        self,
        credentials_dict,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        pass

    @abstractmethod
    def update_event(
        self,
        credentials_dict,
        event_id,
        title,
        start,
        end,
        recurrence_rule=None,
    ):
        pass

    @abstractmethod
    def delete_event(self, credentials_dict, event_id):
        pass
