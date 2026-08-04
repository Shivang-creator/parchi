"""The registration desk — where acuity is currently decided by arrival order.

An Indian OPD is a queue. Patients travel before dawn, arrive together, and
are seen in the order they reached the window. The person having a heart
attack waits behind the person with a rash, because nobody at the desk has
anything to sort them with.

They do not need much. NEWS2 — the National Early Warning Score 2 — is a real,
validated instrument built from six things a registration desk can measure in
ninety seconds: respiration rate, oxygen saturation, blood pressure, pulse,
temperature and whether the patient is alert. It is what turns a queue into
triage.

This module scores it, says what the score obliges you to do, and then models
the queue itself: given who is waiting and how fast each department actually
moves, how long is this person's wait?
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import data

CONSCIOUSNESS = {
    "Alert": 0,
    "Confusion (new)": 3,
    "Responds to voice": 3,
    "Responds to pain": 3,
    "Unresponsive": 3,
}


@dataclass
class Observation:
    """One measured parameter and what it contributed."""

    parameter: str
    value: float | str
    points: int
    unit: str = ""

    @property
    def is_red(self) -> bool:
        """A single parameter scoring 3 escalates on its own, whatever the total.

        This is the part of NEWS2 that people get wrong. A patient can total 3
        and still need an urgent review, because one derangement severe enough
        to score 3 by itself means something is badly wrong with that system.
        """
        return self.points >= 3


@dataclass
class Triage:
    score: int
    band: str
    response: str
    minutes_to_review: int
    observations: list[Observation] = field(default_factory=list)
    on_oxygen: bool = False

    @property
    def red_flags(self) -> list[Observation]:
        return [o for o in self.observations if o.is_red]

    @property
    def priority(self) -> int:
        """1 (see now) to 5 (routine) — the number the queue actually sorts on."""
        if self.score >= 7:
            return 1
        if self.score >= 5 or self.red_flags:
            return 2
        if self.score >= 3:
            return 3
        if self.score >= 1:
            return 4
        return 5


def _band_points(parameter: str, value: float) -> int:
    bands = data.news2_bands()
    rows = bands[bands["parameter"] == parameter]
    hit = rows[(rows["low"] <= value) & (value <= rows["high"])]
    if hit.empty:
        # Outside every published band means outside the instrument's range,
        # which in practice only happens for physiologically extreme values.
        return int(rows["points"].max()) if not rows.empty else 0
    return int(hit.iloc[0]["points"])


def score(
    respiration_rate: float,
    oxygen_saturation: float,
    systolic_bp: float,
    pulse: float,
    temperature: float,
    consciousness: str = "Alert",
    on_oxygen: bool = False,
) -> Triage:
    """Full NEWS2, with the single-parameter escalation rule applied."""
    observations = [
        Observation("Respiration rate", respiration_rate,
                    _band_points("Respiration rate", respiration_rate), "/min"),
        Observation("Oxygen saturation", oxygen_saturation,
                    _band_points("Oxygen saturation", oxygen_saturation), "%"),
        Observation("Systolic blood pressure", systolic_bp,
                    _band_points("Systolic blood pressure", systolic_bp), "mmHg"),
        Observation("Pulse", pulse, _band_points("Pulse", pulse), "/min"),
        Observation("Temperature", temperature,
                    _band_points("Temperature", temperature), "°C"),
        Observation("Consciousness", consciousness,
                    CONSCIOUSNESS.get(consciousness, 0)),
    ]
    if on_oxygen:
        observations.append(Observation("Supplemental oxygen", "yes", 2))

    total = sum(o.points for o in observations)

    table = data.news2_response()
    row = table[(table["score_min"] <= total) & (total <= table["score_max"])]
    row = row.iloc[0] if not row.empty else table.iloc[-1]
    band, response = str(row["band"]), str(row["response"])
    minutes = int(row["minutes_to_review"])

    result = Triage(total, band, response, minutes, observations, on_oxygen)

    # Single-parameter escalation: a 3 in any one parameter lifts a "low"
    # patient to urgent review regardless of the total.
    if result.red_flags and band in ("Routine", "Low"):
        flagged = ", ".join(o.parameter.lower() for o in result.red_flags)
        result.band = "Medium"
        result.minutes_to_review = 60
        result.response = (
            f"Total score is only {total}, but {flagged} scores 3 on its own. "
            f"NEWS2 escalates on any single parameter scoring 3 — urgent review "
            f"within the hour, whatever the total says."
        )
    return result


# --------------------------------------------------------------------------
# The queue
# --------------------------------------------------------------------------
@dataclass
class QueueState:
    department: str
    waiting: int
    doctors: int
    per_doctor_per_hour: float

    @property
    def throughput(self) -> float:
        return self.doctors * self.per_doctor_per_hour


def expected_wait_minutes(
    department: str, ahead_in_queue: int, doctors: int | None = None
) -> float:
    """How long until this patient is seen, given who is in front of them."""
    table = data.departments()
    row = table[table["department"] == department]
    if row.empty:
        return float("nan")
    row = row.iloc[0]
    staff = doctors if doctors is not None else int(row["doctors"])
    throughput = max(staff, 1) * float(row["per_doctor_per_hour"])
    return (ahead_in_queue / throughput) * 60.0


def triage_adjusted_position(priority: int, queue: pd.DataFrame) -> int:
    """Where this patient lands once the queue is sorted by acuity, not arrival.

    `queue` needs a `priority` column. Anyone of strictly higher acuity is
    ahead; within the same priority, arrival order is preserved.
    """
    if queue.empty:
        return 0
    return int((queue["priority"] < priority).sum())


def day_projection(
    total_arrivals: int, department: str | None = None
) -> pd.DataFrame:
    """Arrivals, capacity and backlog hour by hour across an OPD day.

    The 8-11am crush is the defining feature of an Indian OPD: patients travel
    at dawn and arrive together, so demand is front-loaded into three hours
    while capacity is flat across nine. The backlog column is the queue that
    crush creates — and it is entirely predictable the day before.
    """
    arrivals = data.opd_arrivals()
    departments = data.departments()

    if department:
        row = departments[departments["department"] == department].iloc[0]
        share = float(row["arrival_share"])
        capacity_per_hour = int(row["doctors"]) * float(row["per_doctor_per_hour"])
    else:
        share = 1.0
        capacity_per_hour = float(
            (departments["doctors"] * departments["per_doctor_per_hour"]).sum()
        )

    rows, backlog = [], 0.0
    for _, arrival in arrivals.iterrows():
        incoming = total_arrivals * share * float(arrival["share"])
        available = backlog + incoming
        seen = min(available, capacity_per_hour)
        backlog = available - seen
        rows.append({
            "hour": str(arrival["hour"]),
            "arrivals": incoming,
            "capacity": capacity_per_hour,
            "seen": seen,
            "waiting": backlog,
            "wait_minutes": (backlog / capacity_per_hour * 60) if capacity_per_hour else 0.0,
        })
    return pd.DataFrame(rows)


def staffing_to_clear(
    total_arrivals: int, department: str, target_wait_minutes: float = 60.0
) -> int:
    """Smallest number of doctors that keeps the worst wait under target.

    The useful output of a queue model is not the wait — it is the roster
    change that fixes it.
    """
    table = data.departments()
    row = table[table["department"] == department]
    if row.empty:
        return 0
    share = float(row.iloc[0]["arrival_share"])
    rate = float(row.iloc[0]["per_doctor_per_hour"])
    arrivals = data.opd_arrivals()

    for doctors in range(1, 41):
        capacity = doctors * rate
        backlog, worst = 0.0, 0.0
        for _, arrival in arrivals.iterrows():
            available = backlog + total_arrivals * share * float(arrival["share"])
            backlog = max(0.0, available - capacity)
            worst = max(worst, backlog / capacity * 60 if capacity else 0.0)
        if worst <= target_wait_minutes:
            return doctors
    return 40


def synthetic_queue(size: int, seed: int = 7) -> pd.DataFrame:
    """A plausible waiting room, for demonstrating the sort.

    Vitals are drawn so that most people are well and a few are not — which is
    what an OPD queue actually looks like, and why sorting by arrival order
    buries the ones who matter.
    """
    rng = np.random.default_rng(seed)
    departments = data.departments()
    names = list(departments["department"])
    weights = departments["arrival_share"].to_numpy(dtype=float)

    rows = []
    for i in range(size):
        sick = rng.random() < 0.16
        vitals = dict(
            respiration_rate=float(rng.normal(26 if sick else 17, 3.5)),
            oxygen_saturation=float(rng.normal(91 if sick else 98, 2.2)),
            systolic_bp=float(rng.normal(98 if sick else 124, 14)),
            pulse=float(rng.normal(118 if sick else 82, 14)),
            temperature=float(rng.normal(38.6 if sick else 36.8, 0.7)),
            consciousness="Confusion (new)" if (sick and rng.random() < 0.2) else "Alert",
        )
        result = score(**vitals)
        rows.append({
            "token": 100 + i,
            "arrived": i,
            "department": str(rng.choice(names, p=weights / weights.sum())),
            "age": int(np.clip(rng.normal(41, 20), 1, 95)),
            "news2": result.score,
            "priority": result.priority,
            "band": result.band,
        })
    return pd.DataFrame(rows)
