"""Checks whether a ZIP code or city is inside Galactic Builders' approved
service area. Never invents coverage for an unlisted area — an unrecognized
ZIP/city returns "unconfirmed", not "confirmed" or a guess (see spec §18:
never confirm an unconfirmed service area).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypedDict

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "service_areas.json"

ServiceAreaStatus = Literal["confirmed", "outside_area", "unconfirmed"]


class ServiceAreaResult(TypedDict):
    status: ServiceAreaStatus
    message: str


class ServiceAreaService:
    def __init__(self, data_path: Path = DEFAULT_DATA_PATH):
        data = json.loads(data_path.read_text(encoding="utf-8"))
        self.approved_zip_codes: set[str] = set(data.get("approved_zip_codes", []))
        self.approved_cities: set[str] = {c.lower() for c in data.get("approved_cities", [])}
        self.primary_city: str = data.get("primary_city", "")

    def check(self, *, zip_code: str | None = None, city: str | None = None) -> ServiceAreaResult:
        if zip_code:
            normalized_zip = zip_code.strip()[:5]
            if normalized_zip in self.approved_zip_codes:
                return {
                    "status": "confirmed",
                    "message": "Good news, that ZIP code is within the Galactic Builders service area.",
                }
            if normalized_zip.isdigit() and len(normalized_zip) == 5:
                return {
                    "status": "outside_area",
                    "message": (
                        "That ZIP code appears to be outside the standard Galactic Builders "
                        "service area. The team can confirm whether an exception is possible."
                    ),
                }

        if city and city.strip().lower() in self.approved_cities:
            return {
                "status": "confirmed",
                "message": "Good news, that city is within the Galactic Builders service area.",
            }

        return {
            "status": "unconfirmed",
            "message": (
                "The team will need a bit more detail (a ZIP code works best) to confirm "
                "whether this location is within the service area."
            ),
        }
