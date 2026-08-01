"""Resolves free text to a service_key (or flags ambiguity / no match).

Builds its scoring catalog from KnowledgeService so aliases/display names
never have to be duplicated here — the FAQ files remain the single source
of truth for what a service is called.
"""
from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Optional

from app.core.intent_scorer import ServiceCatalogEntry, ServiceMatch, score_against_service
from app.services.knowledge_service import KnowledgeService

HIGH_CONFIDENCE_THRESHOLD = 0.6
AMBIGUITY_GAP = 0.15


class RouteKind(str, Enum):
    EXACT_MATCH = "exact_match"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


class RouteDecision(NamedTuple):
    kind: RouteKind
    service_key: Optional[str]
    confidence: float
    candidates: list[ServiceMatch]  # populated when AMBIGUOUS


def build_catalog(knowledge_service: KnowledgeService) -> dict[str, ServiceCatalogEntry]:
    catalog: dict[str, ServiceCatalogEntry] = {}
    for service_key, service_file in knowledge_service._service_faqs.items():  # noqa: SLF001
        catalog[service_key] = {
            "display_name": service_file.display_name,
            "aliases": list(service_file.aliases),
        }
    return catalog


def route_service_intent(message: str, catalog: dict[str, ServiceCatalogEntry]) -> RouteDecision:
    scored = [
        ServiceMatch(key, score_against_service(message, entry))
        for key, entry in catalog.items()
    ]
    scored = sorted((s for s in scored if s.confidence > 0), key=lambda s: s.confidence, reverse=True)

    if not scored:
        return RouteDecision(RouteKind.NO_MATCH, None, 0.0, [])

    top = scored[0]
    if top.confidence >= HIGH_CONFIDENCE_THRESHOLD:
        runner_up = scored[1] if len(scored) > 1 else None
        if runner_up and (top.confidence - runner_up.confidence) < AMBIGUITY_GAP:
            return RouteDecision(RouteKind.AMBIGUOUS, None, top.confidence, scored[:3])
        return RouteDecision(RouteKind.EXACT_MATCH, top.service_key, top.confidence, [])

    return RouteDecision(RouteKind.NO_MATCH, None, top.confidence, [])
