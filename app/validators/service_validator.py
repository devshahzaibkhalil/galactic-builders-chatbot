"""Validates a service_key against the actual enabled service catalog
(via KnowledgeService), rather than a hardcoded list — so a disabled
service is correctly rejected too, without this module needing to know
the service list itself.
"""
from __future__ import annotations

from app.services.knowledge_service import KnowledgeService
from app.validators.validation_result import ValidationResult, fail, ok


def validate_service_key(raw_value: str, knowledge_service: KnowledgeService) -> ValidationResult:
    if not raw_value or not raw_value.strip():
        return fail("service_required", "Please choose a service.")

    normalized = raw_value.strip().lower().replace(" ", "_").replace("-", "_")

    if not knowledge_service.is_service_enabled(normalized):
        return fail(
            "service_not_available",
            "That service isn't currently available. Please choose from the listed services "
            "or describe your project so the team can review it.",
        )

    return ok(normalized)
