"""Golden-hour escalation — the nearest facility that can actually treat this.

"Nearest hospital" is the wrong question and it kills people. A myocardial
infarction needs a catheterisation lab. An obstructed labour needs an operating
theatre and blood. A stroke needs thrombolysis inside a hard time window. A
signboard three kilometres away that can do none of those is not care, it is
a delay with a waiting room.

Indian Public Health Standards define what each tier of the public system must
be able to provide, so a facility's tier is a usable proxy for its capability.
This module asks: from here, how long until the patient reaches somewhere that
can do the specific thing they need — and does that beat the clock for their
emergency?
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Time from symptom onset within which the definitive intervention has to
# happen for it to still work. These windows are the reason geography is a
# clinical variable in India rather than a logistical footnote.
EMERGENCIES = {
    "Myocardial infarction (STEMI)": {
        "capability": "Cardiac catheterisation",
        "window_min": 120,
        "note": "Primary PCI target is 120 minutes from first medical contact. "
                "Beyond that, muscle is lost and does not come back.",
    },
    "Obstructed labour": {
        "capability": "Caesarean section",
        "window_min": 120,
        "note": "Obstructed labour without surgical delivery is a leading "
                "contributor to maternal death and uterine rupture.",
    },
    "Post-partum haemorrhage": {
        "capability": "Blood bank",
        "window_min": 60,
        "note": "The commonest cause of maternal death in India. Survival "
                "depends on transfusion within the first hour.",
    },
    "Acute ischaemic stroke": {
        "capability": "Stroke thrombolysis",
        "window_min": 270,
        "note": "Thrombolysis window is 4.5 hours from onset, and that clock "
                "includes imaging and door-to-needle time.",
    },
    "Severe trauma": {
        "capability": "Emergency surgery",
        "window_min": 60,
        "note": "The classical golden hour — haemorrhage control determines "
                "survival more than anything that happens later.",
    },
    "Sepsis requiring intensive care": {
        "capability": "Intensive care",
        "window_min": 180,
        "note": "Organ support and source control; mortality climbs with every "
                "hour of delay.",
    },
}

# Average achievable road speed, km/h. Deliberately conservative: Indian rural
# road speeds with an ambulance are nothing like highway speeds, and the
# straight-line distance below already understates the real route.
ROAD_SPEED_KMH = 32.0
ROUTE_FACTOR = 1.35     # road distance vs straight line

# Anything closer than this is the same site under another name, not a
# genuine second facility to refer to.
CO_LOCATED_KM = 0.25


@functools.lru_cache(maxsize=None)
def facilities() -> pd.DataFrame:
    path = DATA_DIR / "facilities.csv"
    if not path.exists():
        return pd.DataFrame(
            columns=["name", "tier", "tier_rank", "state", "anchor",
                     "latitude", "longitude", "capabilities"]
        )
    frame = pd.read_csv(path, comment="#")
    frame["capabilities"] = frame["capabilities"].fillna("")
    return frame


def available() -> bool:
    return not facilities().empty


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def travel_minutes(distance_km: float) -> float:
    return (distance_km * ROUTE_FACTOR) / ROAD_SPEED_KMH * 60.0


@dataclass
class Escalation:
    emergency: str
    capability: str
    window_min: int
    nearest_any: pd.Series | None
    nearest_capable: pd.Series | None
    minutes_to_any: float
    minutes_to_capable: float

    @property
    def reachable(self) -> bool:
        return (
            self.nearest_capable is not None
            and self.minutes_to_capable <= self.window_min
        )

    @property
    def wasted_minutes(self) -> float:
        """Time lost if the patient is taken to the nearest facility first.

        This is the specific, avoidable failure: an ambulance drives to the
        closest signboard, the patient is stabilised and re-referred, and the
        clock runs out during the second journey.
        """
        if self.nearest_capable is None or self.nearest_any is None:
            return 0.0
        if self.nearest_any["name"] == self.nearest_capable["name"]:
            return 0.0
        return round(self.minutes_to_any * 2, 1)


def assess(
    lat: float,
    lon: float,
    emergency: str,
    exclude_name: str | None = None,
) -> Escalation:
    """Score one emergency from one location.

    `exclude_name` drops the referring facility itself from the candidate set.
    Without it the origin is its own nearest facility at zero minutes, which
    silently collapses the whole misrouting calculation.
    """
    spec = EMERGENCIES[emergency]
    capability = spec["capability"]
    frame = facilities().copy()

    if exclude_name is not None:
        frame = frame[frame["name"] != exclude_name]

    # OpenStreetMap frequently carries the same site twice under slightly
    # different names — a hospital and its own outpatient block, say. Without
    # this the "nearest facility" is the origin itself at zero minutes, which
    # silently zeroes the misrouting cost and reads as a bug on screen.
    if not frame.empty:
        separation = np.array([
            haversine_km(lat, lon, r.latitude, r.longitude)
            for r in frame.itertuples()
        ])
        frame = frame[separation > CO_LOCATED_KM]

    if frame.empty:
        return Escalation(emergency, capability, spec["window_min"],
                          None, None, math.inf, math.inf)

    frame["distance_km"] = [
        haversine_km(lat, lon, r.latitude, r.longitude)
        for r in frame.itertuples()
    ]
    frame["minutes"] = frame["distance_km"].apply(travel_minutes)
    frame = frame.sort_values("minutes")

    capable = frame[frame["capabilities"].str.contains(capability, regex=False)]

    nearest_any = frame.iloc[0]
    nearest_capable = capable.iloc[0] if not capable.empty else None

    return Escalation(
        emergency=emergency,
        capability=capability,
        window_min=spec["window_min"],
        nearest_any=nearest_any,
        nearest_capable=nearest_capable,
        minutes_to_any=round(float(nearest_any["minutes"]), 1),
        minutes_to_capable=(
            round(float(nearest_capable["minutes"]), 1)
            if nearest_capable is not None else math.inf
        ),
    )


def coverage_by_emergency(
    lat: float, lon: float, exclude_name: str | None = None
) -> pd.DataFrame:
    """Every emergency type scored from one location — the site's real profile."""
    rows = []
    for name, spec in EMERGENCIES.items():
        result = assess(lat, lon, name, exclude_name)
        rows.append(
            {
                "Emergency": name,
                "Needs": spec["capability"],
                "Window (min)": spec["window_min"],
                "Nearest capable (min)": (
                    round(result.minutes_to_capable)
                    if result.minutes_to_capable != math.inf else None
                ),
                "Facility": (
                    result.nearest_capable["name"]
                    if result.nearest_capable is not None else "none in dataset"
                ),
                "Survivable": "yes" if result.reachable else "no",
            }
        )
    return pd.DataFrame(rows)


def nearest_table(lat: float, lon: float, limit: int = 12) -> pd.DataFrame:
    frame = facilities().copy()
    if frame.empty:
        return frame
    frame["distance_km"] = [
        haversine_km(lat, lon, r.latitude, r.longitude) for r in frame.itertuples()
    ]
    frame["minutes"] = frame["distance_km"].apply(travel_minutes).round(0)
    frame["distance_km"] = frame["distance_km"].round(1)
    return frame.sort_values("minutes").head(limit)
