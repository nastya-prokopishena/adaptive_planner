from types import SimpleNamespace

from backend.application.auth_service import AuthService
from backend.application.schedule_service import ScheduleService


def test_auth_hash_and_check_password():
    password = "test-password"

    hashed = AuthService.hash_password(password)

    assert hashed != password
    assert AuthService.check_password(password, hashed) is True
    assert AuthService.check_password("wrong", hashed) is False


def test_schedule_service_delegates_to_calendar_provider():
    calls = []

    class Provider:
        def get_events(self, **kwargs):
            calls.append(("get", kwargs))
            return ["event"]

        def create_event(self, **kwargs):
            calls.append(("create", kwargs))
            return {"id": "1"}

        def update_event(self, **kwargs):
            calls.append(("update", kwargs))
            return {"id": kwargs["event_id"]}

        def delete_event(self, **kwargs):
            calls.append(("delete", kwargs))
            return True

    service = ScheduleService(calendar_provider=Provider())
    creds = {"token": "x"}

    assert service.get_google_events(creds) == ["event"]
    assert service.create_google_event(creds, "T", "S", "E") == {"id": "1"}
    assert service.update_google_event(creds, "42", "T", "S", "E") == {"id": "42"}
    assert service.delete_google_event(creds, "42") is True

    assert [item[0] for item in calls] == ["get", "create", "update", "delete"]
