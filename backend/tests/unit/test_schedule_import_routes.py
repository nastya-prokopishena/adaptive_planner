from io import BytesIO

from backend.app.routes import schedule_import_routes as routes


def test_upload_schedule_api_requires_file(app):
    with app.test_request_context("/api/schedule-import/upload", method="POST"):
        response, status = routes.upload_schedule_api()

    assert status == 400
    assert response.get_json()["error"] == "Файл розкладу не передано"


def test_upload_schedule_api_rejects_empty_filename(app):
    data = {"file": (BytesIO(b"content"), "")}

    with app.test_request_context(
        "/api/schedule-import/upload",
        method="POST",
        data=data,
        content_type="multipart/form-data",
    ):
        response, status = routes.upload_schedule_api()

    assert status == 400
    assert response.get_json()["error"] == "Некоректний файл"


def test_upload_schedule_api_success(app, monkeypatch):
    monkeypatch.setattr(
        routes.schedule_import_service,
        "build_preview_from_file",
        lambda **kwargs: {
            "events": [{"subject": "Фізика"}],
            "total_found": 1,
            "filename": kwargs["filename"],
            "group": kwargs["group_name"],
        },
    )

    data = {
        "file": (BytesIO(b"file-bytes"), "schedule.pdf"),
        "group_name": "ФЕП-42",
        "subgroup": "1",
    }

    with app.test_request_context(
        "/api/schedule-import/upload",
        method="POST",
        data=data,
        content_type="multipart/form-data",
    ):
        response = routes.upload_schedule_api()

    result = response.get_json()

    assert result["total_found"] == 1
    assert result["filename"] == "schedule.pdf"
    assert result["group"] == "ФЕП-42"


def test_upload_schedule_api_returns_500_on_service_error(app, monkeypatch):
    def raise_error(**kwargs):
        raise RuntimeError("AI error")

    monkeypatch.setattr(routes.schedule_import_service, "build_preview_from_file", raise_error)

    data = {"file": (BytesIO(b"file-bytes"), "schedule.pdf")}

    with app.test_request_context(
        "/api/schedule-import/upload",
        method="POST",
        data=data,
        content_type="multipart/form-data",
    ):
        response, status = routes.upload_schedule_api()

    assert status == 500
    assert response.get_json()["error"] == "Не вдалося обробити файл розкладу через AI"
    assert "AI error" in response.get_json()["details"]


def test_schedule_import_preview_json_success(app, monkeypatch):
    class FakeService:
        def build_preview_from_text(self, **kwargs):
            return {
                "events": [{"subject": "Математика"}],
                "total_found": 1,
                "group": kwargs["group_name"],
            }

    monkeypatch.setattr(routes, "ScheduleImportService", lambda: FakeService())

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        json={"raw_text": "text", "group": "ФЕП-42"},
    ):
        response, status = routes.schedule_import_preview()

    assert status == 200
    assert response.get_json()["total_found"] == 1


def test_schedule_import_preview_json_service_error_result(app, monkeypatch):
    class FakeService:
        def build_preview_from_text(self, **kwargs):
            return {
                "error": "Не знайдено розклад",
                "events": [],
                "total_found": 0,
            }

    monkeypatch.setattr(routes, "ScheduleImportService", lambda: FakeService())

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        json={"text": "bad"},
    ):
        response, status = routes.schedule_import_preview()

    assert status == 400
    assert response.get_json()["error"] == "Не знайдено розклад"


def test_schedule_import_preview_multipart_requires_file(app):
    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        data={},
        content_type="multipart/form-data",
    ):
        response, status = routes.schedule_import_preview()

    assert status == 400
    assert response.get_json()["events"] == []


def test_schedule_import_preview_multipart_success(app, monkeypatch):
    class FakeService:
        def build_preview_from_file(self, **kwargs):
            return {
                "events": [{"subject": "Фізика"}],
                "total_found": 1,
                "filename": kwargs["filename"],
                "group": kwargs["group_name"],
            }

    monkeypatch.setattr(routes, "ScheduleImportService", lambda: FakeService())

    data = {
        "file": (BytesIO(b"file-bytes"), "schedule.xlsx"),
        "group_name": "ФЕП-42",
    }

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        data=data,
        content_type="multipart/form-data",
    ):
        response, status = routes.schedule_import_preview()

    assert status == 200
    assert response.get_json()["filename"] == "schedule.xlsx"


def test_schedule_import_preview_returns_500_on_exception(app, monkeypatch):
    class FakeService:
        def build_preview_from_text(self, **kwargs):
            raise RuntimeError("broken")

    monkeypatch.setattr(routes, "ScheduleImportService", lambda: FakeService())

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        json={"raw_text": "text"},
    ):
        response, status = routes.schedule_import_preview()

    assert status == 500
    assert response.get_json()["events"] == []
    assert "broken" in response.get_json()["details"]


def test_schedule_import_preview_json_uses_text_alias(app, monkeypatch):
    class FakeService:
        def build_preview_from_text(self, **kwargs):
            return {
                "events": [],
                "total_found": 0,
                "raw_text": kwargs["raw_text"],
                "group": kwargs["group_name"],
                "subgroup": kwargs["subgroup"],
            }

    monkeypatch.setattr(routes, "ScheduleImportService", lambda: FakeService())

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        json={"text": "plain text", "group_name": "ФЕП-42", "subgroup": "2"},
    ):
        response, status = routes.schedule_import_preview()

    data = response.get_json()

    assert status == 200
    assert data["raw_text"] == "plain text"
    assert data["group"] == "ФЕП-42"
    assert data["subgroup"] == "2"


def test_schedule_import_preview_multipart_uses_group_alias(app, monkeypatch):
    class FakeService:
        def build_preview_from_file(self, **kwargs):
            return {
                "filename": kwargs["filename"],
                "group": kwargs["group_name"],
                "subgroup": kwargs["subgroup"],
                "events": [],
                "total_found": 0,
            }

    monkeypatch.setattr(routes, "ScheduleImportService", lambda: FakeService())

    with app.test_request_context(
        "/api/schedule-import/preview",
        method="POST",
        data={
            "file": (BytesIO(b"file"), "schedule.pdf"),
            "group": "ФЕП-42",
            "subgroup": "1",
        },
        content_type="multipart/form-data",
    ):
        response, status = routes.schedule_import_preview()

    data = response.get_json()

    assert status == 200
    assert data["filename"] == "schedule.pdf"
    assert data["group"] == "ФЕП-42"
    assert data["subgroup"] == "1"
