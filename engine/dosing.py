"""Dose from body parameters.

Most prescribing errors are not "wrong drug" — they are "right drug, wrong
dose for this body". The two commonest versions in an Indian OPD are a normal
adult dose given to someone with quietly impaired kidneys, and a weight-based
paediatric dose worked out under time pressure.

This module turns age / sex / weight / serum creatinine into a dose, and
refuses outright when the drug should not be used at that renal function.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import data


@dataclass
class Patient:
    age: int
    sex: str                    # "Male" | "Female"
    weight_kg: float
    serum_creatinine: float     # mg/dL
    setting: str = "OPD"
    pregnant: bool = False

    @property
    def is_paediatric(self) -> bool:
        return self.age < 12


@dataclass
class DoseResult:
    antibiotic: str
    action: str                 # KEEP | REDUCE | EXTEND | CONTRAINDICATED
    dose_text: str
    guidance: str
    crcl: float
    ckd_stage: str
    dose_fraction: float
    is_paediatric: bool

    @property
    def blocked(self) -> bool:
        return self.action == "CONTRAINDICATED"

    @property
    def adjusted(self) -> bool:
        return self.action in ("REDUCE", "EXTEND")


def cockcroft_gault(patient: Patient) -> float:
    """Creatinine clearance, mL/min.

        CrCl = ((140 - age) x weight x [0.85 if female]) / (72 x serum creatinine)

    Cockcroft-Gault rather than eGFR/CKD-EPI on purpose: renal drug dosing
    references are written against CrCl, and it needs only variables a
    registration desk can actually capture.
    """
    if patient.serum_creatinine <= 0:
        raise ValueError("Serum creatinine must be positive")
    crcl = ((140 - patient.age) * patient.weight_kg) / (72 * patient.serum_creatinine)
    if patient.sex == "Female":
        crcl *= 0.85
    return max(0.0, round(crcl, 1))


def ckd_stage(crcl: float) -> str:
    if crcl >= 90:
        return "Normal (G1)"
    if crcl >= 60:
        return "Mildly reduced (G2)"
    if crcl >= 45:
        return "Mild-moderate (G3a)"
    if crcl >= 30:
        return "Moderate-severe (G3b)"
    if crcl >= 15:
        return "Severe (G4)"
    return "Kidney failure (G5)"


def dose_for(antibiotic: str, patient: Patient) -> DoseResult:
    meta = data.drug_row(antibiotic)
    crcl = cockcroft_gault(patient)
    stage = ckd_stage(crcl)

    rules = data.renal_rules()
    rules = rules[rules["antibiotic"] == antibiotic]

    action, fraction, guidance = "KEEP", 1.0, "No renal adjustment required."
    if not rules.empty:
        band = rules[(rules["crcl_min"] <= crcl) & (crcl < rules["crcl_max"])]
        if not band.empty:
            row = band.iloc[0]
            action = str(row["action"])
            fraction = float(row["dose_fraction"])
            guidance = str(row["guidance"])
    elif int(meta["renal_adjust"]) == 0:
        guidance = "Not renally cleared — no adjustment needed."

    if patient.is_paediatric:
        per_kg = float(meta["peds_mg_per_kg_per_day"])
        doses = int(meta["doses_per_day"])
        total_mg = per_kg * patient.weight_kg * fraction
        per_dose = total_mg / max(doses, 1)
        dose_text = (
            f"{total_mg:.0f} mg/day in {doses} divided doses "
            f"({per_dose:.0f} mg per dose) — {per_kg:.0f} mg/kg/day x {patient.weight_kg:.0f} kg"
        )
    else:
        adult = str(meta["adult_dose"])
        doses = int(meta["doses_per_day"])
        if fraction == 1.0:
            dose_text = f"{adult} x {doses}/day"
        elif fraction == 0.0:
            dose_text = "Do not administer"
        else:
            dose_text = f"{adult} x {doses}/day, reduced to {fraction:.0%} of normal"

    return DoseResult(
        antibiotic=antibiotic,
        action=action,
        dose_text=dose_text,
        guidance=guidance,
        crcl=crcl,
        ckd_stage=stage,
        dose_fraction=fraction,
        is_paediatric=patient.is_paediatric,
    )


# --------------------------------------------------------------------------
# Cost
# --------------------------------------------------------------------------
@dataclass
class CostResult:
    antibiotic: str
    days: int
    doses_per_day: int
    brand_total: float
    generic_total: float
    janaushadhi_total: float
    janaushadhi_available: bool

    @property
    def best_total(self) -> float:
        if self.janaushadhi_available:
            return self.janaushadhi_total
        return self.generic_total

    @property
    def saving(self) -> float:
        return round(self.brand_total - self.best_total, 2)

    @property
    def multiple(self) -> float:
        """How many times the cheap option the branded course costs."""
        if self.best_total <= 0:
            return 0.0
        return round(self.brand_total / self.best_total, 1)


@dataclass
class DurationAdvice:
    site: str
    prescribed: int
    typical: int
    minimum: int
    maximum: int
    guidance: str

    @property
    def verdict(self) -> str:
        if self.prescribed > self.maximum:
            return "TOO LONG"
        if self.prescribed < self.minimum:
            return "TOO SHORT"
        if self.prescribed > self.typical:
            return "LONGER THAN NEEDED"
        return "APPROPRIATE"

    @property
    def excess_days(self) -> int:
        return max(0, self.prescribed - self.typical)


def duration_advice(site: str, prescribed_days: int) -> DurationAdvice | None:
    """Is this course the right length?

    Course length is the most overlooked lever in stewardship. A decade of
    trials has consistently found shorter to be non-inferior, yet Indian
    prescriptions routinely run to ten or fourteen days out of habit. Every
    extra day is resistance pressure and cost with no added cure.
    """
    row = data.duration_for(site)
    if row is None:
        return None
    return DurationAdvice(
        site=site,
        prescribed=int(prescribed_days),
        typical=int(row["typical_days"]),
        minimum=int(row["min_days"]),
        maximum=int(row["max_days"]),
        guidance=str(row["guidance"]),
    )


def course_cost(antibiotic: str, days: int, dose_fraction: float = 1.0) -> CostResult:
    meta = data.drug_row(antibiotic)
    doses = int(meta["doses_per_day"])
    units = doses * days * max(dose_fraction, 0.0)

    ja_price = float(meta["price_janaushadhi"])
    return CostResult(
        antibiotic=antibiotic,
        days=days,
        doses_per_day=doses,
        brand_total=round(float(meta["price_brand"]) * units, 2),
        generic_total=round(float(meta["price_generic"]) * units, 2),
        janaushadhi_total=round(ja_price * units, 2),
        janaushadhi_available=ja_price > 0,
    )


def regimen_cost(
    items: list[tuple[str, int, float]],
) -> tuple[float, float, float]:
    """Total cost of a whole prescription, not one line of it.

    Patients are handed a slip with several drugs on it and pay for all of
    them at once. `items` is a list of (antibiotic, days, dose_fraction).
    Returns (brand total, cheapest-available total, saving).
    """
    brand = cheapest = 0.0
    for name, days, fraction in items:
        try:
            cost = course_cost(name, days, fraction)
        except KeyError:
            continue
        brand += cost.brand_total
        cheapest += cost.best_total
    return round(brand, 2), round(cheapest, 2), round(brand - cheapest, 2)
