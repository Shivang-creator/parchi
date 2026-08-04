"""Parchi engines — each module answers one question about a prescription.

    data      loading and caching of the curated Indian data layer
    coverage  will this antibiotic actually work, here, this year?
    dosing    what dose does this body need, and what does the course cost?
    safety    is this combination banned, and does it collide with their meds?
    forecast  what is walking through the door in three weeks?
    geo       if this patient needs more than we have, how far is help?
"""

from . import coverage, data, dosing, forecast, safety  # noqa: F401

__all__ = ["data", "coverage", "dosing", "safety", "forecast", "geo"]
