"""Navigation commands the customer can type at any point during a flow.

Single source of truth for recognized phrasing — side_question_detector.py
and flow_manager.py both import from here rather than hardcoding lists.
"""
from __future__ import annotations

BACK = "back"
SKIP = "skip"
CANCEL = "cancel"
START_OVER = "start_over"
CHANGE_EMAIL = "change_email"
CHANGE_PHONE = "change_phone"
CHANGE_ADDRESS = "change_address"
TALK_TO_PERSON = "talk_to_person"
RETURN_TO_BOT = "return_to_bot"

# phrase -> command. Matching is case-insensitive substring/equality on the
# normalized (lowercased, stripped) customer message.
COMMAND_PHRASES: dict[str, str] = {
    "back": BACK,
    "go back": BACK,
    "skip": SKIP,
    "skip this": SKIP,
    "cancel": CANCEL,
    "start over": START_OVER,
    "restart": START_OVER,
    "change my email": CHANGE_EMAIL,
    "update my email": CHANGE_EMAIL,
    "change my phone": CHANGE_PHONE,
    "update my phone": CHANGE_PHONE,
    "change my address": CHANGE_ADDRESS,
    "update my address": CHANGE_ADDRESS,
    "talk to a person": TALK_TO_PERSON,
    "talk to a human": TALK_TO_PERSON,
    "speak with the team": TALK_TO_PERSON,
    "speak to a person": TALK_TO_PERSON,
    "return to the bot": RETURN_TO_BOT,
    "back to the bot": RETURN_TO_BOT,
}

# Which single field, if any, a "change my X" command should reopen without
# discarding other completed fields.
COMMAND_TARGET_FIELD: dict[str, str] = {
    CHANGE_EMAIL: "email",
    CHANGE_PHONE: "phone",
    CHANGE_ADDRESS: "street_address",
}
