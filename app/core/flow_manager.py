"""Controls the active multi-step flow (e.g. the 20-step estimate flow).

Owns: which field is asked next, how "back"/"skip"/"start over" behave, and
guarantees that reopening one field (change my email) never discards other
already-completed fields.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.constants.conversation_commands import (
    BACK,
    CANCEL,
    COMMAND_TARGET_FIELD,
    SKIP,
    START_OVER,
)
from app.core.conversation_state import ConversationState

FieldValidator = Callable[[str], dict[str, Any]]


@dataclass
class FlowStep:
    field_name: str
    prompt: str
    validator: Optional[FieldValidator] = None
    optional: bool = False


@dataclass
class FlowDefinition:
    name: str
    steps: list[FlowStep]

    def step_index(self, field_name: str) -> int:
        for i, step in enumerate(self.steps):
            if step.field_name == field_name:
                return i
        raise ValueError(f"'{field_name}' is not a step in flow '{self.name}'.")


class FlowManager:
    def __init__(self, flow: FlowDefinition):
        self.flow = flow

    def start(self, state: ConversationState) -> FlowStep:
        state.active_flow = self.flow.name
        first_step = self.flow.steps[0]
        state.current_step = first_step.field_name
        state.set_pending_field(first_step.field_name)
        return first_step

    def _next_unanswered_step(self, state: ConversationState, after_index: int = -1) -> Optional[FlowStep]:
        for step in self.flow.steps[after_index + 1:]:
            if step.field_name not in state.completed_fields:
                return step
        return None

    def submit_field_answer(self, state: ConversationState, value: Any) -> Optional[FlowStep]:
        """Records the answer for the currently pending field and advances.

        Returns the next FlowStep to prompt for, or None if the flow is
        complete. Caller is responsible for validating `value` first via
        side_question_detector + the field's own validator — this method
        assumes it has already been validated.
        """
        if state.pending_field is None:
            raise ValueError("No field is currently pending.")

        state.complete_field(state.pending_field, value)
        current_index = self.flow.step_index(state.pending_field)
        next_step = self._next_unanswered_step(state, after_index=current_index)

        if next_step is None:
            state.current_step = None
            state.set_pending_field(None)
            return None

        state.current_step = next_step.field_name
        state.set_pending_field(next_step.field_name)
        return next_step

    def handle_navigation_command(self, state: ConversationState, command: str) -> Optional[FlowStep]:
        """Handles back/skip/cancel/start_over/change_my_X. Never discards
        fields other than the one explicitly targeted."""
        if command == START_OVER:
            state.reset_flow()
            return self.start(state)

        if command == CANCEL:
            state.reset_flow()
            return None

        if command == BACK:
            current_field = state.pending_field or state.current_step
            if current_field is None:
                return None
            idx = self.flow.step_index(current_field)
            prev_index = max(idx - 1, 0)
            prev_step = self.flow.steps[prev_index]
            state.completed_fields.pop(prev_step.field_name, None)
            state.current_step = prev_step.field_name
            state.set_pending_field(prev_step.field_name)
            return prev_step

        if command == SKIP:
            current_field = state.pending_field
            if current_field is None:
                return None
            step = self.flow.steps[self.flow.step_index(current_field)]
            if not step.optional:
                # Cannot skip a required field — caller should surface this;
                # we simply return the same step unchanged.
                return step
            next_step = self._next_unanswered_step(state, after_index=self.flow.step_index(current_field))
            if next_step is None:
                state.current_step = None
                state.set_pending_field(None)
                return None
            state.current_step = next_step.field_name
            state.set_pending_field(next_step.field_name)
            return next_step

        target_field = COMMAND_TARGET_FIELD.get(command)
        if target_field:
            state.reopen_field(target_field)
            state.current_step = target_field
            return self.flow.steps[self.flow.step_index(target_field)]

        return None

    def is_complete(self, state: ConversationState) -> bool:
        return all(step.optional or step.field_name in state.completed_fields for step in self.flow.steps)
