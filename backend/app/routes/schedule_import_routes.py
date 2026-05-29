from backend.app.routes.common import *

schedule_import_bp = Blueprint("schedule_import", __name__)


# ---------------------------
# SCHEDULE IMPORT
# ---------------------------


@schedule_import_bp.route("/api/schedule-import/upload", methods=["POST"])
def upload_schedule_api():
    if "file" not in request.files:
        return jsonify({"error": "Файл розкладу не передано"}), 400

    file = request.files["file"]

    if not file or not file.filename:
        return jsonify({"error": "Некоректний файл"}), 400

    group_name = request.form.get("group_name", "")
    subgroup = request.form.get("subgroup", "")

    try:
        result = schedule_import_service.build_preview_from_file(
            filename=file.filename,
            file_bytes=file.read(),
            group_name=group_name,
            subgroup=subgroup,
        )

        return jsonify(result)

    except Exception as error:
        return (
            jsonify(
                {
                    "error": "Не вдалося обробити файл розкладу через AI",
                    "details": str(error),
                }
            ),
            500,
        )


@schedule_import_bp.route("/api/schedule-import/preview", methods=["POST"])
def schedule_import_preview():
    service = ScheduleImportService()

    try:
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            uploaded_file = request.files.get("file")

            if not uploaded_file:
                return (
                    jsonify(
                        {
                            "error": "Файл не передано.",
                            "details": "Файл не передано.",
                            "events": [],
                            "total_found": 0,
                        }
                    ),
                    400,
                )

            group_name = (request.form.get("group_name") or request.form.get("group") or "").strip()

            subgroup = (request.form.get("subgroup") or "").strip()

            result = service.build_preview_from_file(
                filename=uploaded_file.filename,
                file_bytes=uploaded_file.read(),
                group_name=group_name,
                subgroup=subgroup,
            )

        else:
            payload = request.get_json(silent=True) or {}

            raw_text = payload.get("raw_text") or payload.get("text") or ""

            group_name = (payload.get("group_name") or payload.get("group") or "").strip()

            subgroup = (payload.get("subgroup") or "").strip()

            result = service.build_preview_from_text(
                raw_text=raw_text,
                group_name=group_name,
                subgroup=subgroup,
            )

        status_code = 400 if result.get("error") else 200

        return jsonify(result), status_code

    except Exception as exc:
        return (
            jsonify(
                {
                    "error": "Не вдалося сформувати preview розкладу.",
                    "details": str(exc),
                    "events": [],
                    "total_found": 0,
                }
            ),
            500,
        )
