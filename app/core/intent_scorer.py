"""Scores how well a customer message matches a given service.

Pure text scoring, no I/O — intent_router.py builds the catalog from
KnowledgeService and calls into this module. Kept separate so the scoring
logic itself is trivially unit-testable without loading FAQ files.
"""
from __future__ import annotations

import re
from typing import NamedTuple, Optional, TypedDict

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


class ServiceCatalogEntry(TypedDict):
    display_name: str
    aliases: list[str]


def _tokenize(text: str) -> set[str]:
    return set(_WORD_PATTERN.findall(text.lower()))


def score_against_service(message: str, entry: ServiceCatalogEntry) -> float:
    """Returns a 0.0-1.0 confidence score for one service.

    Scoring: fraction of the service's phrase tokens (across display_name +
    aliases, deduplicated) that appear in the message, weighted toward
    multi-word alias hits so "kitchen remodeling" scores higher than a
    lone "kitchen".
    """
    message_tokens = _tokenize(message)
    if not message_tokens:
        return 0.0

    phrases = [entry["display_name"], *entry["aliases"]]
    best = 0.0
    for phrase in phrases:
        phrase_tokens = _tokenize(phrase)
        if not phrase_tokens:
            continue
        overlap = len(phrase_tokens & message_tokens)
        if overlap == 0:
            continue
        coverage = overlap / len(phrase_tokens)
        # Reward exact/near-exact phrase matches over a single shared word.
        score = coverage if len(phrase_tokens) == 1 else coverage * 1.0
        if len(phrase_tokens) > 1 and overlap == len(phrase_tokens):
            score = 1.0
        best = max(best, score)
    return best


class ServiceMatch(NamedTuple):
    service_key: str
    confidence: float


def best_service_match(
    message: str, catalog: dict[str, ServiceCatalogEntry]
) -> Optional[ServiceMatch]:
    best_match: Optional[ServiceMatch] = None
    for service_key, entry in catalog.items():
        score = score_against_service(message, entry)
        if score > 0 and (best_match is None or score > best_match.confidence):
            best_match = ServiceMatch(service_key, score)
    return best_match
