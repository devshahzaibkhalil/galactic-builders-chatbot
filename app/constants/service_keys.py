"""Canonical service catalog keys — must match app/data/faqs/services/service_faq_index.json.

This is the single place other modules import the *set* of valid keys from
when they need it without loading the full knowledge base (e.g. schema
choices, constants for tests). The FAQ index remains the source of truth for
display names, categories, and enabled/disabled status.
"""
from __future__ import annotations

INTERIOR_REMODELING = (
    "kitchen_remodeling",
    "bathroom_remodeling",
    "basement_remodeling",
    "home_addition_construction",
    "flooring_installation",
    "flooring_repair",
    "drywall_installation",
    "interior_painting",
)

EXTERIOR_CONSTRUCTION = (
    "deck_construction",
    "patio_construction",
    "exterior_painting",
    "exterior_structure_repairs",
    "roof_installation",
    "roof_repair",
    "gutter_cleaning",
)

INSTALLATION_AND_REPAIR = (
    "fan_installation",
    "fan_repair",
    "tv_mounting",
    "furniture_assembly",
    "plumbing_fixture_installation",
    "water_fixture_repair",
)

ALL_SERVICE_KEYS = INTERIOR_REMODELING + EXTERIOR_CONSTRUCTION + INSTALLATION_AND_REPAIR
