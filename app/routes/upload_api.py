from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.security.rate_limits import UPLOAD_RATE_LIMIT, limiter
from app.services.upload_service import FileValidationError, upload_project_file

upload_api_bp = Blueprint("upload_api", __name__, url_prefix="/api/leads")


@upload_api_bp.post("/<lead_id>/uploads")
@limiter.limit(UPLOAD_RATE_LIMIT)
def upload_file(lead_id: str):
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    uploaded = request.files["file"]
    file_bytes = uploaded.read()

    session_factory = current_app.extensions["db_session_factory"]
    session = session_factory()
    storage = current_app.extensions["storage_service"]

    try:
        record = upload_project_file(
            session, storage, lead_id=lead_id, filename=uploaded.filename or "", file_bytes=file_bytes
        )
        session.commit()
    except FileValidationError as exc:
        session.rollback()
        return jsonify({"error": exc.error_code, "message": str(exc)}), 422
    finally:
        session.close()

    return jsonify({
        "id": record.id,
        "original_filename": record.original_filename,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
    }), 201
