"""Orchestrates one turn of the conversation, in the exact priority order
required by the spec:

    1. Security and abuse checks         (not yet built — see routes phase)
    2. Safety / emergency-language        -> safety_router
    3. Human takeover status              -> human_takeover
    4. Active conversation-flow status    -> flow_manager
    5. Side-question detection            -> side_question_detector
    6. Direct field-answer validation     -> app/validators/*
    7. Service intent detection           -> intent_router
    8-9. Estimate/pricing + FAQ matching  -> knowledge_service
    10-11. Callback/appointment + contact (not yet built — later phase)
    12. Low-confidence fallback           -> fallback_handler
    13. Unknown-query logging             -> fallback_handler

No lower-priority branch may run before a higher one has been checked. This
module is intentionally the ONLY place that encodes that ordering — do not
duplicate routing decisions in routes/chat_api.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from app.constants.conversation_modes import ADMIN_ACTIVE, CLOSED, WAITING_FOR_CUSTOMER
from app.core.conversation_state import ConversationState
from app.core.fallback_handler import build_ambiguous_message, handle_fallback
from app.core.flow_manager import FlowManager
from app.core.intent_router import RouteKind, build_catalog, route_service_intent
from app.core.response_builder import side_question_response
from app.core.safety_router import check_safety
from app.core.side_question_detector import MessageKind, detect
from app.services.knowledge_service import KnowledgeService
from app.validators.email_validator import validate_email
from app.validators.phone_validator import validate_phone
from app.validators.zip_validator import validate_zip

FIELD_VALIDATORS: dict[str, Callable[[str], dict]] = {
    "email": validate_email,
    "phone": validate_phone,
    "zip_code": validate_zip,
}


def _generic_required_validator(value: str) -> dict:
    if value and value.strip():
        return {"valid": True, "normalized_value": value.strip(), "error_code": None, "message": None}
    return {"valid": False, "normalized_value": None, "error_code": "required", "message": "This field is required."}


def _validator_for(field_name: Optional[str]) -> Callable[[str], dict]:
    if field_name is None:
        return _generic_required_validator
    return FIELD_VALIDATORS.get(field_name, _generic_required_validator)


_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def _keywords(message: str) -> list[str]:
    return _WORD_PATTERN.findall(message.lower())


@dataclass
class ChatTurnResult:
    response_text: Optional[str]  # None means "no automatic bot response" (e.g. admin_active)
    handled_by: str  # which routing stage produced the response, for logging/tests


class ChatEngine:
    def __init__(self, knowledge_service: KnowledgeService, flow_manager: FlowManager):
        self.knowledge_service = knowledge_service
        self.flow_manager = flow_manager

    def process_message(self, state: ConversationState, message: str) -> ChatTurnResult:
        state.record_turn(message)

        # 2. Safety check — runs regardless of mode or active flow.
        safety = check_safety(message)
        if safety.is_safety_concern:
            state.record_turn(message, safety.message)
            return ChatTurnResult(safety.message, "safety_router")

        # 3. Human takeover status — bot stays silent, message is still saved.
        if state.mode in (ADMIN_ACTIVE, WAITING_FOR_CUSTOMER, CLOSED):
            return ChatTurnResult(None, "human_takeover")

        # 4/5/6. Active flow -> side-question detection -> field validation.
        if state.pending_field:
            result = self._handle_active_flow_turn(state, message)
            state.record_turn(message, result.response_text)
            return result

        # 7. Service intent detection.
        catalog = build_catalog(self.knowledge_service)
        route = route_service_intent(message, catalog)

        if route.kind == RouteKind.EXACT_MATCH:
            service_file = self.knowledge_service.get_service_faq_file(route.service_key)
            response = service_file.summary if service_file else None
            if response:
                state.previous_intent = "service_availability"
                state.record_turn(message, response)
                return ChatTurnResult(response, "intent_router:exact_match")

        if route.kind == RouteKind.AMBIGUOUS:
            names = [
                self.knowledge_service.get_service_faq_file(c.service_key).display_name
                for c in route.candidates
                if self.knowledge_service.get_service_faq_file(c.service_key)
            ]
            response = build_ambiguous_message(names)
            state.record_turn(message, response)
            return ChatTurnResult(response, "intent_router:ambiguous")

        # 8-9. FAQ / general / process / pricing matching.
        faq_hit = self.knowledge_service.find_answer(None, _keywords(message))
        if faq_hit:
            state.record_turn(message, faq_hit["answer"])
            return ChatTurnResult(faq_hit["answer"], "knowledge_service:general_faq")

        # 12/13. Low-confidence fallback + unknown-query logging.
        response = handle_fallback(message, confidence=route.confidence)
        state.record_turn(message, response)
        return ChatTurnResult(response, "fallback_handler")

    def _handle_active_flow_turn(self, state: ConversationState, message: str) -> ChatTurnResult:
        pending_field = state.pending_field
        validator = _validator_for(pending_field)
        detection = detect(message, pending_field, field_validator=validator)

        if detection.kind == MessageKind.NAVIGATION_COMMAND:
            next_step = self.flow_manager.handle_navigation_command(state, detection.command)
            response = next_step.prompt if next_step else "Understood."
            return ChatTurnResult(response, "flow_manager:navigation_command")

        if detection.kind == MessageKind.SIDE_QUESTION:
            service_key = state.completed_fields.get("service_key")
            faq_hit = self.knowledge_service.find_answer(service_key, _keywords(message))
            answer = faq_hit["answer"] if faq_hit else handle_fallback(message)
            current_step = next(
                (s for s in self.flow_manager.flow.steps if s.field_name == pending_field), None
            )
            repeated_prompt = current_step.prompt if current_step else None
            response = side_question_response(answer, repeated_prompt)
            return ChatTurnResult(response, "side_question_detector")

        # FIELD_ANSWER
        result = validator(message)
        if not result["valid"]:
            return ChatTurnResult(result["message"], "field_validator:invalid")

        next_step = self.flow_manager.submit_field_answer(state, result["normalized_value"])
        response = next_step.prompt if next_step else "Thanks — that completes your project details."
        return ChatTurnResult(response, "flow_manager:field_answer")
