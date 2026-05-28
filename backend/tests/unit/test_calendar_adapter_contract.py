from backend.domain.interfaces.calendar_provider import CalendarProvider
from backend.infrastructure.google_calendar_adapter import GoogleCalendarAdapter


def test_google_calendar_adapter_implements_calendar_provider():
    adapter = GoogleCalendarAdapter()

    assert isinstance(adapter, CalendarProvider)
    assert hasattr(adapter, "get_events")
    assert hasattr(adapter, "create_event")
    assert hasattr(adapter, "update_event")
    assert hasattr(adapter, "delete_event")
