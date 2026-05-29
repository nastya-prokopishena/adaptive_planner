from io import BytesIO

import pytest


@pytest.mark.integration
def test_schedule_preview_text_request_returns_json(client, monkeypatch):
    from backend.app.routes import schedule_import_routes

    class FakeService:
        def build_preview_from_text(self, raw_text, group_name, subgroup):
            return {
                "events": [
                    {
                        "subject": raw_text,
                        "group": group_name,
                        "subgroup": subgroup,
                    }
                ],
                "total_found": 1,
            }

    monkeypatch.setattr(schedule_import_routes, "ScheduleImportService", lambda: FakeService())

    response = client.post(
        "/api/schedule-import/preview",
        json={
            "text": "Програмування",
            "group": "ФЕП-42",
            "subgroup": "1",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["total_found"] == 1


@pytest.mark.integration
def test_schedule_preview_file_request_returns_json(client, monkeypatch):
    from backend.app.routes import schedule_import_routes

    class FakeService:
        def build_preview_from_file(self, filename, file_bytes, group_name, subgroup):
            return {
                "events": [{"subject": "Фізика"}],
                "total_found": 1,
                "filename": filename,
                "group": group_name,
            }

    monkeypatch.setattr(schedule_import_routes, "ScheduleImportService", lambda: FakeService())

    response = client.post(
        "/api/schedule-import/preview",
        data={
            "file": (BytesIO(b"schedule file"), "schedule.txt"),
            "group_name": "ФЕП-42",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["filename"] == "schedule.txt"


@pytest.mark.integration
def test_schedule_upload_rejects_missing_file(client):
    response = client.post("/api/schedule-import/upload", data={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Файл розкладу не передано"
