"""Prescription safety checks — combinations and interactions.

Two distinct Indian problems live here.

1. Fixed-dose combinations. India's market carries thousands of FDCs, and
   CDSCO has formally prohibited hundreds of them, yet they keep being
   prescribed and dispensed. Cefixime + azithromycin is the canonical
   antibiotic example: two broad agents welded together at a fixed ratio, no
   evidence of benefit, and resistance pressure on both classes at once.

2. Interactions that matter. Every EHR fires interaction alerts on everything,
   so clinicians click through all of them — the classic alert-fatigue trap.
   This module only surfaces MAJOR interactions by default, so an alert
   appearing means something.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import data

SEVERITY_ORDER = {"MAJOR": 0, "MODERATE": 1, "MINOR": 2}
STATUS_ORDER = {"BANNED": 0, "RESTRICTED": 1, "IRRATIONAL": 2}

# Interaction tables are written against drug *classes*, but a patient's med
# list is written in brand-and-molecule shorthand ("Tab Sertraline 50mg").
# Without this bridge the checker silently misses the interaction that matters
# most — linezolid plus an SSRI is the classic serotonin-syndrome pairing and
# it is invisible if you only match the literal string "SSRI".
CLASS_MEMBERS = {
    "ssri": ["sertraline", "fluoxetine", "escitalopram", "citalopram",
             "paroxetine", "fluvoxamine"],
    "snri": ["venlafaxine", "duloxetine", "desvenlafaxine"],
    "antidepressant": ["amitriptyline", "nortriptyline", "imipramine",
                       "mirtazapine", "bupropion"],
    "warfarin": ["warfarin", "acitrom", "acenocoumarol"],
    "inhibitor": ["ramipril", "enalapril", "lisinopril", "perindopril"],
    "ace": ["ramipril", "enalapril", "lisinopril", "perindopril"],
    "arb": ["telmisartan", "losartan", "olmesartan", "valsartan", "irbesartan"],
    "antacid": ["antacid", "sucralfate", "magaldrate", "gelusil"],
    "calcium": ["calcium", "shelcal", "calcimax"],
    "iron": ["iron", "ferrous", "fecontin", "orofer"],
    "methotrexate": ["methotrexate"],
    "theophylline": ["theophylline", "aminophylline", "deriphyllin"],
    "ondansetron": ["ondansetron", "emeset", "vomikind"],
    "amiodarone": ["amiodarone", "cordarone"],
    "furosemide": ["furosemide", "frusemide", "lasix", "torsemide"],
    "tramadol": ["tramadol", "ultracet"],
}


def _expand(term: str) -> list[str]:
    """A matcher term plus any molecules that belong to its class."""
    term = term.strip().lower()
    return [term] + CLASS_MEMBERS.get(term, [])


@dataclass
class Alert:
    kind: str          # "combination" | "interaction"
    severity: str      # BANNED / RESTRICTED / IRRATIONAL / MAJOR / MODERATE
    title: str
    detail: str

    @property
    def is_blocking(self) -> bool:
        return self.severity in ("BANNED", "MAJOR")


def _normalise(name: str) -> str:
    return name.strip().lower()


def check_combinations(prescribed: list[str]) -> list[Alert]:
    """Flag banned or irrational fixed-dose combinations in the prescription."""
    alerts: list[Alert] = []
    lowered = {_normalise(p) for p in prescribed}

    for _, row in data.fdc_flags().iterrows():
        a, b = _normalise(row["drug_a"]), _normalise(row["drug_b"])
        # Match either two separately prescribed agents, or a single combined
        # product written as one line ("Cefixime + Azithromycin").
        both_present = a in lowered and b in lowered
        as_one_line = any(a in item and b in item for item in lowered)
        if both_present or as_one_line:
            alerts.append(
                Alert(
                    kind="combination",
                    severity=str(row["status"]),
                    title=f"{row['drug_a']} + {row['drug_b']}",
                    detail=str(row["reason"]),
                )
            )

    alerts.sort(key=lambda a: STATUS_ORDER.get(a.severity, 9))
    return alerts


def check_interactions(
    prescribed: list[str],
    current_meds: list[str],
    include_moderate: bool = False,
) -> list[Alert]:
    """Interactions between what we are about to add and what they already take.

    `current_meds` are free-text entries from the patient's existing list; we
    match on substring both ways so 'Tab Warfarin 5mg' still matches 'Warfarin'.
    """
    alerts: list[Alert] = []
    everything = [_normalise(m) for m in current_meds + prescribed]

    for _, row in data.interactions().iterrows():
        drug = _normalise(row["drug"])
        partner = str(row["interacts_with"])
        severity = str(row["severity"])

        if severity == "MODERATE" and not include_moderate:
            continue
        if not any(drug in item or item in drug for item in [_normalise(p) for p in prescribed]):
            continue

        # The partner field can name a class ("SSRI / SNRI antidepressant") or
        # a specific agent. Expand each token through the class map so a real
        # med list written in molecule names still matches.
        tokens: list[str] = []
        for raw in partner.replace("/", " ").replace("+", " ").split():
            cleaned = raw.strip().lower()
            if len(cleaned) > 2:
                tokens.extend(_expand(cleaned))

        hit = any(tok in item for item in everything for tok in tokens)
        if hit:
            alerts.append(
                Alert(
                    kind="interaction",
                    severity=severity,
                    title=f"{row['drug']} x {partner}",
                    detail=str(row["effect"]),
                )
            )

    alerts.sort(key=lambda a: SEVERITY_ORDER.get(a.severity, 9))
    return alerts


def run_all(
    prescribed: list[str],
    current_meds: list[str],
    include_moderate: bool = False,
) -> list[Alert]:
    return check_combinations(prescribed) + check_interactions(
        prescribed, current_meds, include_moderate
    )
