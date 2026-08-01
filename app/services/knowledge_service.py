"""Loads and serves the service-specific FAQ knowledge base.

Single authoritative source for reading app/data/faqs/services/*.json.
No other module should read these files directly.

Resolution order used by get_faqs_for_query():
    1. Matched service FAQ (exact service_key)
    2. General business FAQ
    3. Process / pricing FAQ
    4. Safe fallback
    5. Unknown-query log (handled by the caller, not this service)
"""
from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.schemas.service_faq_schema import ServiceFaqFile, ServiceFaqIndex

logger = logging.getLogger("galactic.knowledge_service")
_KEYWORD_TOKEN = re.compile(r"[a-z0-9]+")

DEFAULT_FAQ_ROOT = Path(__file__).resolve().parent.parent / "data" / "faqs"


class KnowledgeLoadError(RuntimeError):
    """Raised when the knowledge base fails startup validation."""


class KnowledgeService:
    """Thread-safe loader/cache for service and general FAQ content."""

    def __init__(self, faq_root: Path = DEFAULT_FAQ_ROOT) -> None:
        self._faq_root = faq_root
        self._services_dir = faq_root / "services"
        self._lock = threading.RLock()
        self._service_faqs: dict[str, ServiceFaqFile] = {}
        self._general_faqs: dict[str, dict] = {}
        self._faq_id_owner: dict[str, str] = {}
        self._load_errors: list[str] = []

    # -- Startup / reload ------------------------------------------------

    def load(self, strict: bool = True) -> None:
        """Load and validate the index plus every enabled service file.

        strict=True raises KnowledgeLoadError if the index itself is
        missing/invalid (fatal at startup). Per-file problems are always
        logged and skipped rather than crashing the widget.
        """
        with self._lock:
            self._service_faqs.clear()
            self._faq_id_owner.clear()
            self._load_errors.clear()

            index_path = self._services_dir / "service_faq_index.json"
            index = self._read_index(index_path, strict=strict)
            if index is None:
                return

            for service_key, entry in index.services.items():
                if not entry.enabled:
                    logger.info("Skipping disabled service FAQ file: %s", service_key)
                    continue
                file_path = self._services_dir / entry.file
                self._load_service_file(service_key, file_path)

            self._general_faqs = self._load_general_faqs()

            logger.info(
                "Knowledge base loaded: %d service files, %d general FAQ files, %d errors",
                len(self._service_faqs),
                len(self._general_faqs),
                len(self._load_errors),
            )

    def _read_index(self, index_path: Path, strict: bool) -> Optional[ServiceFaqIndex]:
        try:
            raw = json.loads(index_path.read_text(encoding="utf-8"))
            return ServiceFaqIndex.model_validate(raw)
        except FileNotFoundError:
            msg = f"service_faq_index.json not found at {index_path}"
            logger.error(msg)
            if strict:
                raise KnowledgeLoadError(msg)
            self._load_errors.append(msg)
            return None
        except (json.JSONDecodeError, ValidationError) as exc:
            msg = f"service_faq_index.json is invalid: {exc}"
            logger.error(msg)
            if strict:
                raise KnowledgeLoadError(msg)
            self._load_errors.append(msg)
            return None

    def _load_service_file(self, expected_key: str, file_path: Path) -> None:
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            parsed = ServiceFaqFile.model_validate(raw)
        except FileNotFoundError:
            msg = f"Missing service FAQ file for '{expected_key}': {file_path}"
            logger.error(msg)
            self._load_errors.append(msg)
            return
        except (json.JSONDecodeError, ValidationError) as exc:
            msg = f"Invalid service FAQ file for '{expected_key}' ({file_path.name}): {exc}"
            logger.error(msg)
            self._load_errors.append(msg)
            return

        if parsed.service_key != expected_key:
            msg = (
                f"{file_path.name} declares service_key '{parsed.service_key}' "
                f"but is registered under '{expected_key}' — rejecting file. "
                "One service file must not claim another service's key."
            )
            logger.error(msg)
            self._load_errors.append(msg)
            return

        for item in parsed.faqs:
            owner = self._faq_id_owner.get(item.id)
            if owner and owner != expected_key:
                msg = (
                    f"Duplicate FAQ id '{item.id}' found in '{expected_key}' "
                    f"(already owned by '{owner}') — rejecting file."
                )
                logger.error(msg)
                self._load_errors.append(msg)
                return
        for item in parsed.faqs:
            self._faq_id_owner[item.id] = expected_key

        self._service_faqs[expected_key] = parsed

    def _load_general_faqs(self) -> dict[str, dict]:
        general_files = ["general.json", "pricing.json", "process.json", "appointments.json", "safety.json"]
        loaded: dict[str, dict] = {}
        for name in general_files:
            path = self._faq_root / name
            try:
                loaded[name] = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                logger.warning("Optional general FAQ file not found: %s", path)
            except json.JSONDecodeError as exc:
                msg = f"Invalid general FAQ file {name}: {exc}"
                logger.error(msg)
                self._load_errors.append(msg)
        return loaded

    # -- Query API ---------------------------------------------------------

    def is_service_enabled(self, service_key: str) -> bool:
        with self._lock:
            return service_key in self._service_faqs

    def get_service_faq_file(self, service_key: str) -> Optional[ServiceFaqFile]:
        with self._lock:
            return self._service_faqs.get(service_key)

    def get_faqs_for_service(self, service_key: str) -> list[dict]:
        """Search only the matched service's file, never the whole catalog."""
        with self._lock:
            service = self._service_faqs.get(service_key)
            if not service:
                return []
            return [item.model_dump() for item in service.faqs]

    def find_answer(self, service_key: Optional[str], query_keywords: list[str]) -> Optional[dict]:
        """Resolution order: matched service -> general -> process/pricing -> None.

        Caller is responsible for logging an unknown-query entry when this
        returns None (safe fallback + unknown-query log are conversation
        concerns, not knowledge-base concerns).
        """
        normalized = {kw.lower() for kw in query_keywords}

        if service_key:
            faqs = self.get_faqs_for_service(service_key)
            hit = self._best_match(faqs, normalized)
            if hit:
                return hit

        for name in ("general.json", "process.json", "pricing.json"):
            faqs = self._general_faqs.get(name, {}).get("faqs", [])
            hit = self._best_match(faqs, normalized)
            if hit:
                return hit

        return None

    @staticmethod
    def _fuzzy_token_overlap(query_tokens: set[str], phrase_tokens: set[str]) -> int:
        """Counts near-matches (exact, or shared 4-char prefix) so simple
        plural/verb-form differences like 'basements' vs 'basement' or
        'remodel' vs 'remodeling' still count as a hit."""
        score = 0
        for qt in query_tokens:
            for pt in phrase_tokens:
                if qt == pt:
                    score += 1
                    break
                if len(qt) >= 4 and len(pt) >= 4 and qt[:4] == pt[:4]:
                    score += 1
                    break
        return score

    @classmethod
    def _best_match(cls, faqs: list[dict], normalized_query_kw: set[str]) -> Optional[dict]:
        best, best_score = None, 0
        for faq in faqs:
            # Keywords are stored as short phrases ("basement moisture"), so
            # tokenize each phrase into individual words before comparing —
            # otherwise a single-word query token never matches a multi-word
            # keyword phrase.
            phrase_words: set[str] = set()
            for phrase in faq.get("keywords", []):
                phrase_words.update(_KEYWORD_TOKEN.findall(phrase.lower()))
            score = cls._fuzzy_token_overlap(normalized_query_kw, phrase_words)
            if score > best_score:
                best, best_score = faq, score
        return best if best_score > 0 else None

    @property
    def load_errors(self) -> list[str]:
        with self._lock:
            return list(self._load_errors)


# Module-level singleton used by the app factory / admin publish action.
knowledge_service = KnowledgeService()
