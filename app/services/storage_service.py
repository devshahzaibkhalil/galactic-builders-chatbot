"""Low-level file storage. No validation logic here — upload_service.py
validates first and only passes already-accepted bytes to save().

Local filesystem storage for this phase; swap the implementation (e.g. S3)
without touching upload_service.py's interface.
"""
from __future__ import annotations

import secrets
from pathlib import Path


class StorageService:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def generate_storage_name(self, extension: str) -> str:
        return f"{secrets.token_hex(16)}.{extension.lower()}"

    def save(self, storage_name: str, file_bytes: bytes) -> Path:
        # storage_name is always server-generated (see generate_storage_name),
        # never derived from user input, so no path-traversal characters can
        # reach this join.
        destination = self.root / storage_name
        destination.write_bytes(file_bytes)
        return destination

    def delete(self, storage_name: str) -> None:
        path = self.root / storage_name
        if path.exists():
            path.unlink()
