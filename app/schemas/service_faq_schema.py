"""Validation schema for per-service FAQ knowledge files.

Every file under app/data/faqs/services/<service_key>.json must validate
against ServiceFaqFile before it is loaded by KnowledgeService. This is the
single authoritative schema for service FAQ content — do not duplicate these
rules elsewhere.
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# --- Content-safety patterns -------------------------------------------------

_SCRIPT_PATTERN = re.compile(r"<\s*script|javascript:|on\w+\s*=", re.IGNORECASE)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")

# Phrases that would smuggle an unverified guarantee into an FAQ answer.
_FIXED_PRICE_PATTERN = re.compile(
    r"costs?\s+exactly|flat\s+rate|guaranteed\s+price", re.IGNORECASE
)
_GUARANTEED_DATE_PATTERN = re.compile(
    r"guarantee[d]?\s+(completion|to\s+finish|delivery)|will\s+be\s+done\s+by",
    re.IGNORECASE,
)
_LICENSE_CLAIM_PATTERN = re.compile(
    r"we\s+are\s+(fully\s+)?licensed|our\s+license\s+number", re.IGNORECASE
)
_WARRANTY_CLAIM_PATTERN = re.compile(
    r"we\s+(offer|provide|guarantee)\s+a?\s*(\d+[- ]?(year|month))?\s*warranty",
    re.IGNORECASE,
)

ALLOWED_INTENTS = {
    "service_availability",
    "project_scope",
    "installation_or_repair",
    "pricing",
    "timeline",
    "materials",
    "customer_supplied_materials",
    "property_condition",
    "photo_upload",
    "service_area",
    "appointment_or_callback",
    "safety",
    "licensing_warranty",
    "next_step",
}

ALLOWED_FOLLOW_UPS = {
    "offer_estimate_flow",
    "ask_project_details",
    "start_photo_upload_flow",
    "start_service_area_check",
    "offer_callback_flow",
    "none",
}


def _reject_unsafe_text(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty.")
    if _SCRIPT_PATTERN.search(value):
        raise ValueError(f"{field_name} contains disallowed script/executable content.")
    if _HTML_TAG_PATTERN.search(value):
        raise ValueError(f"{field_name} must not contain HTML markup.")
    return value.strip()


class ServiceFaqItem(BaseModel):
    id: str = Field(..., min_length=3, max_length=64)
    question: str
    answer: str
    keywords: list[str] = Field(default_factory=list)
    intent: str
    follow_up_action: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        return _reject_unsafe_text(v, "question")

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        v = _reject_unsafe_text(v, "answer")
        if _FIXED_PRICE_PATTERN.search(v):
            raise ValueError("answer must not contain an unverified fixed price.")
        if _GUARANTEED_DATE_PATTERN.search(v):
            raise ValueError("answer must not guarantee a completion date.")
        if _LICENSE_CLAIM_PATTERN.search(v):
            raise ValueError("answer must not assert unverified licensing claims.")
        if _WARRANTY_CLAIM_PATTERN.search(v):
            raise ValueError("answer must not assert unverified warranty claims.")
        return v

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v: str) -> str:
        if v not in ALLOWED_INTENTS:
            raise ValueError(f"Unsupported intent '{v}'.")
        return v

    @field_validator("follow_up_action")
    @classmethod
    def validate_follow_up(cls, v: str) -> str:
        if v not in ALLOWED_FOLLOW_UPS:
            raise ValueError(f"Unsupported follow_up_action '{v}'.")
        return v


class ServiceFaqFile(BaseModel):
    service_key: str = Field(..., min_length=2, max_length=64)
    display_name: str
    category: str
    enabled: bool
    aliases: list[str] = Field(default_factory=list)
    summary: str
    restricted_claims: list[str] = Field(default_factory=list)
    faqs: list[ServiceFaqItem]
    lead_questions: list[str] = Field(default_factory=list)

    @field_validator("service_key")
    @classmethod
    def validate_key_format(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", v):
            raise ValueError(
                "service_key must be lowercase snake_case, e.g. 'kitchen_remodeling'."
            )
        return v

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        return _reject_unsafe_text(v, "summary")

    @field_validator("faqs")
    @classmethod
    def validate_unique_ids(cls, faqs: list[ServiceFaqItem]) -> list[ServiceFaqItem]:
        if not faqs:
            raise ValueError("faqs must contain at least one entry.")
        seen: set[str] = set()
        for item in faqs:
            if item.id in seen:
                raise ValueError(f"Duplicate FAQ id '{item.id}' within the same file.")
            seen.add(item.id)
        return faqs

    @model_validator(mode="after")
    def validate_key_ownership(self) -> "ServiceFaqFile":
        """A service file must own only its own service_key.

        Every FAQ id must be prefixed with the file's own service_key
        (hyphenated form) so one file cannot silently claim another
        service's identifiers.
        """
        expected_prefix = self.service_key.replace("_", "-")
        for item in self.faqs:
            if not item.id.startswith(expected_prefix):
                raise ValueError(
                    f"FAQ id '{item.id}' does not belong to service_key "
                    f"'{self.service_key}' (expected prefix '{expected_prefix}')."
                )
        return self


class ServiceFaqIndexEntry(BaseModel):
    display_name: str
    category: str
    file: str
    enabled: bool


class ServiceFaqIndex(BaseModel):
    version: str
    services: dict[str, ServiceFaqIndexEntry]

    @field_validator("services")
    @classmethod
    def validate_key_matches_registry(
        cls, services: dict[str, ServiceFaqIndexEntry]
    ) -> dict[str, ServiceFaqIndexEntry]:
        if not services:
            raise ValueError("service_faq_index.json must register at least one service.")
        return services
