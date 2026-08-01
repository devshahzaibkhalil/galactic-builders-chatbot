"""Coordinates file-upload validation, storage, and the UploadedFile record.

Routes call only this — never file_validator or StorageService directly —
so the validate-then-store ordering can't be skipped by accident.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.uploaded_file import UploadedFile
from app.services.storage_service import StorageService
from app.validators.file_validator import validate_upload


class FileValidationError(ValueError):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


def upload_project_file(
    session: Session,
    storage: StorageService,
    *,
    lead_id: str,
    filename: str,
    file_bytes: bytes,
) -> UploadedFile:
    result = validate_upload(filename, file_bytes)
    if not result["valid"]:
        raise FileValidationError(result["error_code"], result["message"])

    extension = filename.rsplit(".", 1)[-1].lower()
    storage_name = storage.generate_storage_name(extension)
    storage.save(storage_name, file_bytes)

    record = UploadedFile(
        lead_id=lead_id,
        storage_name=storage_name,
        original_filename=filename,
        mime_type=result["normalized_value"],
        size_bytes=len(file_bytes),
    )
    session.add(record)
    session.flush()
    return record
