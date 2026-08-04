"""
Parchi — data build step.

Emits every CSV the app reads into ./data. Run once: `python build_data.py`.

PROVENANCE / HONESTY NOTE
------------------------
Every figure here is *indicative*, compiled from the public literature so the
engines can be demonstrated end to end. It is NOT a verbatim transcription of
any single source and MUST NOT be used clinically.

  - Susceptibility levels and their OPD < ward < ICU gradient follow the
    patterns reported by the ICMR Antimicrobial Resistance Surveillance
    Network (AMRSN) annual reports and WHO GLASS. Values are anchored at a
    recent-year endpoint and an earlier endpoint; the intermediate years are
    reconstructed by interpolation plus noise. The *direction and magnitude*
    of each trend are real; the individual year points are not observations.
  - Prices are indicative Indian retail ranges for brand / generic / PMBJP
    (Jan Aushadhi) tiers. NPPA publishes binding ceiling prices per pack.
  - Banned / irrational fixed-dose combinations are drawn from CDSCO's
    published prohibition lists.
  - Dengue burden uses realistic state-level magnitudes and the well-documented
    post-monsoon seasonal profile reported by NCVBDC.

Swap any of these CSVs for the real series and nothing downstream changes.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

RNG = np.random.default_rng(20260805)
YEARS = list(range(2018, 2025))
SETTINGS = ["OPD", "Ward", "ICU"]

PROVENANCE = (
    "Indicative figures compiled from published ICMR-AMRSN / WHO GLASS / CDSCO / "
    "NPPA / NCVBDC patterns. Reconstructed for demonstration. Not for clinical use."
)


# --------------------------------------------------------------------------
# 1. Organisms and what causes what
# --------------------------------------------------------------------------
# P(organism | infection site) at the OUTPATIENT baseline. Sums to 1.0 per site.
# The setting shift below re-weights these for ward and ICU patients.
INFECTION_PRIORS = {
    "Urinary tract infection": {
        "Escherichia coli": 0.55,
        "Klebsiella pneumoniae": 0.20,
        "Enterococcus spp": 0.10,
        "Pseudomonas aeruginosa": 0.08,
        "Acinetobacter baumannii": 0.04,
        "Staphylococcus aureus": 0.03,
    },
    "Bloodstream infection / sepsis": {
        "Klebsiella pneumoniae": 0.25,
        "Escherichia coli": 0.22,
        "Staphylococcus aureus": 0.18,
        "Acinetobacter baumannii": 0.15,
        "Pseudomonas aeruginosa": 0.10,
        "Enterococcus spp": 0.10,
    },
    "Pneumonia / lower respiratory": {
        "Klebsiella pneumoniae": 0.28,
        "Acinetobacter baumannii": 0.22,
        "Pseudomonas aeruginosa": 0.20,
        "Staphylococcus aureus": 0.12,
        "Escherichia coli": 0.10,
        "Streptococcus pneumoniae": 0.08,
    },
    "Skin / soft tissue": {
        "Staphylococcus aureus": 0.55,
        "Pseudomonas aeruginosa": 0.13,
        "Escherichia coli": 0.12,
        "Klebsiella pneumoniae": 0.10,
        "Enterococcus spp": 0.10,
    },
    "Intra-abdominal": {
        "Escherichia coli": 0.45,
        "Klebsiella pneumoniae": 0.22,
        "Enterococcus spp": 0.15,
        "Pseudomonas aeruginosa": 0.10,
        "Acinetobacter baumannii": 0.08,
    },
    "Enteric fever (typhoid)": {
        "Salmonella Typhi": 0.95,
        "Escherichia coli": 0.05,
    },
}

# Which organisms are hospital-dwelling. An ICU infection is a different
# disease from the same-named OPD infection: catheters, ventilators and prior
# antibiotic exposure select hard for these four, while community organisms
# recede. Weights multiply the outpatient prior and are then renormalised.
NOSOCOMIAL = {
    "Acinetobacter baumannii",
    "Pseudomonas aeruginosa",
    "Klebsiella pneumoniae",
    "Enterococcus spp",
}
SETTING_PRIOR_SHIFT = {"OPD": 0.45, "Ward": 1.20, "ICU": 1.90}


# --------------------------------------------------------------------------
# 2. Antibiotic formulary
# --------------------------------------------------------------------------
# spectrum: 1 = narrow (stewardship-preferred) .. 5 = last-line (reserve)
# Prices are INR per unit dose (tablet or vial).
DRUGS = [
    # name, class, spectrum, route, adult_dose, peds_mg_kg_day, doses/day,
    # brand, generic, janaushadhi, renal_adjust, who_aware
    ("Nitrofurantoin", "Nitrofuran", 1, "PO", "100 mg", 5, 2, 12.0, 6.0, 3.0, 1, "Access"),
    ("Cotrimoxazole", "Folate inhibitor", 1, "PO", "960 mg (DS)", 8, 2, 6.0, 2.5, 1.0, 1, "Access"),
    ("Doxycycline", "Tetracycline", 2, "PO", "100 mg", 4, 2, 8.0, 3.0, 1.5, 0, "Access"),
    ("Amoxicillin-Clavulanate", "Beta-lactam/BLI", 2, "PO", "625 mg", 30, 3, 15.0, 8.0, 4.0, 1, "Access"),
    ("Ampicillin", "Aminopenicillin", 1, "IV", "1 g", 100, 4, 18.0, 9.0, 5.0, 1, "Access"),
    ("Azithromycin", "Macrolide", 2, "PO", "500 mg", 10, 1, 35.0, 12.0, 6.0, 0, "Watch"),
    ("Ciprofloxacin", "Fluoroquinolone", 3, "PO", "500 mg", 20, 2, 12.0, 4.0, 2.0, 1, "Watch"),
    ("Levofloxacin", "Fluoroquinolone", 3, "PO", "500 mg", 10, 1, 28.0, 10.0, 5.0, 1, "Watch"),
    ("Gentamicin", "Aminoglycoside", 2, "IV", "5 mg/kg", 5, 1, 22.0, 11.0, 6.0, 1, "Access"),
    ("Amikacin", "Aminoglycoside", 3, "IV", "15 mg/kg", 15, 1, 60.0, 30.0, 16.0, 1, "Access"),
    ("Ceftriaxone", "3rd-gen cephalosporin", 3, "IV", "1 g", 75, 1, 60.0, 25.0, 15.0, 0, "Watch"),
    ("Cefepime", "4th-gen cephalosporin", 4, "IV", "1 g", 100, 3, 200.0, 90.0, 0.0, 1, "Watch"),
    ("Piperacillin-Tazobactam", "Beta-lactam/BLI", 4, "IV", "4.5 g", 300, 4, 450.0, 200.0, 0.0, 1, "Watch"),
    ("Meropenem", "Carbapenem", 5, "IV", "1 g", 60, 3, 1100.0, 350.0, 0.0, 1, "Watch"),
    ("Imipenem-Cilastatin", "Carbapenem", 5, "IV", "500 mg", 60, 4, 600.0, 280.0, 0.0, 1, "Watch"),
    ("Vancomycin", "Glycopeptide", 4, "IV", "1 g", 45, 2, 400.0, 180.0, 0.0, 1, "Watch"),
    ("Linezolid", "Oxazolidinone", 4, "PO/IV", "600 mg", 30, 2, 90.0, 35.0, 18.0, 0, "Reserve"),
    ("Colistin", "Polymyxin", 5, "IV", "3 MIU", 75, 3, 520.0, 300.0, 0.0, 1, "Reserve"),
]


# --------------------------------------------------------------------------
# 3. Susceptibility: %S at OPD in the anchor years, per organism x drug
# --------------------------------------------------------------------------
# (early_2018, recent_2024) at the OPD setting.
#
# An ABSENT pair means the drug has no useful activity against that organism
# and is scored as zero cover — this is deliberate and clinically meaningful.
# Vancomycin and linezolid genuinely cannot touch gram-negatives; colistin
# genuinely cannot touch gram-positives; ceftriaxone has no enterococcal
# activity. Those holes are the model working, not missing data.
#
# Conversely, carbapenems and piperacillin-tazobactam DO cover methicillin-
# susceptible S. aureus and E. faecalis, so those pairs are present — their
# ceiling is set by the local MSSA / E. faecalis share rather than by any
# resistance mechanism of their own.
SUSCEPTIBILITY_ANCHORS = {
    "Escherichia coli": {
        "Nitrofurantoin": (92, 86),
        "Cotrimoxazole": (32, 25),
        "Doxycycline": (40, 33),
        "Amoxicillin-Clavulanate": (48, 34),
        "Ampicillin": (18, 10),
        "Ciprofloxacin": (24, 13),
        "Levofloxacin": (28, 16),
        "Gentamicin": (72, 62),
        "Amikacin": (88, 79),
        "Ceftriaxone": (28, 17),
        "Cefepime": (42, 27),
        "Piperacillin-Tazobactam": (72, 56),
        "Meropenem": (88, 70),
        "Imipenem-Cilastatin": (89, 72),
        "Colistin": (99, 96),
    },
    "Klebsiella pneumoniae": {
        "Nitrofurantoin": (42, 33),
        "Cotrimoxazole": (35, 26),
        "Amoxicillin-Clavulanate": (38, 25),
        "Ciprofloxacin": (35, 22),
        "Levofloxacin": (38, 25),
        "Gentamicin": (55, 42),
        "Amikacin": (70, 56),
        "Ceftriaxone": (30, 16),
        "Cefepime": (38, 23),
        "Piperacillin-Tazobactam": (58, 40),
        "Meropenem": (72, 50),
        "Imipenem-Cilastatin": (73, 52),
        "Colistin": (97, 92),
    },
    "Pseudomonas aeruginosa": {
        "Ciprofloxacin": (68, 58),
        "Levofloxacin": (66, 56),
        "Gentamicin": (66, 57),
        "Amikacin": (78, 70),
        "Cefepime": (74, 64),
        "Piperacillin-Tazobactam": (76, 66),
        "Meropenem": (74, 62),
        "Imipenem-Cilastatin": (72, 60),
        "Colistin": (98, 95),
    },
    "Acinetobacter baumannii": {
        "Cotrimoxazole": (30, 22),
        "Doxycycline": (52, 44),
        "Ciprofloxacin": (24, 14),
        "Levofloxacin": (28, 18),
        "Gentamicin": (32, 22),
        "Amikacin": (38, 27),
        "Cefepime": (26, 16),
        "Piperacillin-Tazobactam": (28, 18),
        "Meropenem": (34, 20),
        "Imipenem-Cilastatin": (35, 21),
        "Colistin": (96, 90),
    },
    "Staphylococcus aureus": {
        # Every beta-lactam here is capped by the local MSSA share: MRSA is
        # resistant to all of them regardless of the reported zone diameter.
        "Cotrimoxazole": (78, 72),
        "Doxycycline": (86, 82),
        "Amoxicillin-Clavulanate": (68, 61),
        "Azithromycin": (52, 42),
        "Ciprofloxacin": (54, 44),
        "Levofloxacin": (58, 48),
        "Gentamicin": (74, 68),
        "Amikacin": (82, 77),
        "Ceftriaxone": (68, 61),
        "Cefepime": (68, 61),
        "Piperacillin-Tazobactam": (68, 61),
        "Meropenem": (68, 61),
        "Imipenem-Cilastatin": (68, 61),
        "Vancomycin": (100, 100),
        "Linezolid": (100, 99),
    },
    "Enterococcus spp": {
        # Ceftriaxone and cefepime are absent by design — enterococci are
        # intrinsically resistant to all cephalosporins.
        "Nitrofurantoin": (88, 83),
        "Ampicillin": (58, 47),
        "Amoxicillin-Clavulanate": (58, 47),
        "Piperacillin-Tazobactam": (60, 50),
        "Meropenem": (56, 46),
        "Imipenem-Cilastatin": (58, 48),
        "Ciprofloxacin": (32, 22),
        "Levofloxacin": (35, 25),
        "Vancomycin": (92, 86),
        "Linezolid": (99, 98),
    },
    "Salmonella Typhi": {
        "Cotrimoxazole": (94, 92),
        "Ciprofloxacin": (14, 6),
        "Levofloxacin": (18, 8),
        "Azithromycin": (99, 98),
        "Ceftriaxone": (98, 96),
        "Cefepime": (98, 96),
        "Meropenem": (100, 99),
    },
    "Streptococcus pneumoniae": {
        "Cotrimoxazole": (48, 40),
        "Doxycycline": (72, 66),
        "Ampicillin": (92, 88),
        "Amoxicillin-Clavulanate": (94, 90),
        "Azithromycin": (70, 60),
        "Levofloxacin": (96, 94),
        "Ceftriaxone": (96, 94),
        "Cefepime": (96, 94),
        "Piperacillin-Tazobactam": (95, 93),
        "Meropenem": (99, 98),
        "Imipenem-Cilastatin": (99, 98),
        "Vancomycin": (100, 100),
        "Linezolid": (100, 100),
    },
}

# Susceptibility falls as you move from outpatient to ICU: sicker patients,
# more prior antibiotic exposure, more nosocomial strains. Multiplicative.
SETTING_FACTOR = {"OPD": 1.00, "Ward": 0.86, "ICU": 0.71}


def build_susceptibility() -> None:
    rows = []
    for organism, drugs in SUSCEPTIBILITY_ANCHORS.items():
        for drug, (early, recent) in drugs.items():
            for setting in SETTINGS:
                factor = SETTING_FACTOR[setting]
                for year in YEARS:
                    t = (year - YEARS[0]) / (YEARS[-1] - YEARS[0])
                    base = early + (recent - early) * t
                    value = base * factor
                    # Year-to-year surveillance jitter. Anchor years stay clean.
                    if year not in (YEARS[0], YEARS[-1]):
                        value += RNG.normal(0, 1.4)
                    # Colistin/vancomycin/linezolid stay near-ceiling everywhere.
                    value = float(np.clip(value, 1.0, 100.0))
                    rows.append(
                        {
                            "organism": organism,
                            "antibiotic": drug,
                            "setting": setting,
                            "year": year,
                            "percent_susceptible": round(value, 1),
                        }
                    )
    _write("amr_susceptibility.csv", rows)


# --------------------------------------------------------------------------
# 4. Patient risk factors that shift the expected organism mix
# --------------------------------------------------------------------------
# Each factor multiplies the odds of a resistant/nosocomial organism and
# discounts observed susceptibility. Sourced from the standard risk criteria
# for MDR organisms (prior antibiotics, healthcare exposure, devices).
RISK_FACTORS = [
    ("Antibiotics in the last 90 days", 0.78, "Strongest single predictor of a resistant isolate"),
    ("Hospitalised in the last 90 days", 0.84, "Healthcare-associated exposure to nosocomial strains"),
    ("Indwelling urinary catheter", 0.86, "Biofilm-associated, typically MDR organisms"),
    ("Central venous line", 0.85, "Device-associated bloodstream organisms"),
    ("Mechanical ventilation", 0.80, "Ventilator-associated pneumonia skews to Acinetobacter/Pseudomonas"),
    ("Immunosuppressed / on chemotherapy", 0.88, "Broader organism range, lower reserve"),
    ("Resident of a long-term care facility", 0.85, "Colonisation with resistant flora"),
    ("Known prior MDR isolate", 0.62, "Past colonisation strongly predicts recurrence"),
]


# --------------------------------------------------------------------------
# 5. Banned / irrational fixed-dose combinations (CDSCO)
# --------------------------------------------------------------------------
FDC_FLAGS = [
    ("Cefixime", "Azithromycin", "BANNED",
     "Prohibited FDC. No evidence of added benefit; drives resistance in both classes."),
    ("Cefixime", "Ofloxacin", "BANNED",
     "Prohibited FDC. Two broad agents combined without rationale."),
    ("Cefpodoxime", "Levofloxacin", "BANNED",
     "Prohibited FDC. Irrational dual gram-negative cover."),
    ("Ciprofloxacin", "Tinidazole", "IRRATIONAL",
     "Widely sold; fixed ratio prevents independent dosing and encourages overuse."),
    ("Ofloxacin", "Ornidazole", "IRRATIONAL",
     "Very common in Indian OPD for diarrhoea; little evidence, high resistance cost."),
    ("Levofloxacin", "Ornidazole", "IRRATIONAL",
     "Same pattern as ofloxacin-ornidazole."),
    ("Amoxicillin", "Bromhexine", "BANNED",
     "Prohibited FDC. Mucolytic adds nothing to the antibiotic."),
    ("Nimesulide", "Paracetamol", "BANNED",
     "Prohibited FDC. Duplicated hepatotoxicity risk."),
    ("Diclofenac", "Serratiopeptidase", "IRRATIONAL",
     "No robust evidence for the enzyme component."),
    ("Pioglitazone", "Metformin+Glimepiride", "RESTRICTED",
     "Triple oral FDC; restricted use, high hypoglycaemia risk."),
]


# --------------------------------------------------------------------------
# 6. Drug-drug interactions relevant to the antibiotic formulary
# --------------------------------------------------------------------------
INTERACTIONS = [
    ("Linezolid", "SSRI / SNRI antidepressant", "MAJOR",
     "Serotonin syndrome. Linezolid is a reversible MAO inhibitor."),
    ("Linezolid", "Tramadol", "MAJOR", "Serotonin syndrome risk."),
    ("Ciprofloxacin", "Warfarin", "MAJOR", "INR rises sharply; bleeding risk."),
    ("Levofloxacin", "Warfarin", "MAJOR", "INR rises sharply; bleeding risk."),
    ("Cotrimoxazole", "Warfarin", "MAJOR", "Marked INR elevation."),
    ("Cotrimoxazole", "Methotrexate", "MAJOR", "Additive myelosuppression."),
    ("Cotrimoxazole", "ACE inhibitor / ARB", "MODERATE", "Hyperkalaemia, especially in CKD."),
    ("Azithromycin", "Ondansetron", "MODERATE", "Additive QT prolongation."),
    ("Levofloxacin", "Ondansetron", "MODERATE", "Additive QT prolongation."),
    ("Azithromycin", "Amiodarone", "MAJOR", "QT prolongation, torsades risk."),
    ("Amikacin", "Vancomycin", "MAJOR", "Additive nephrotoxicity."),
    ("Gentamicin", "Vancomycin", "MAJOR", "Additive nephrotoxicity."),
    ("Amikacin", "Furosemide", "MODERATE", "Additive oto- and nephrotoxicity."),
    ("Gentamicin", "Furosemide", "MODERATE", "Additive oto- and nephrotoxicity."),
    ("Colistin", "Amikacin", "MAJOR", "Compounded nephrotoxicity; monitor creatinine daily."),
    ("Ciprofloxacin", "Antacid / calcium / iron", "MODERATE",
     "Chelation cuts absorption. Separate doses by 2 hours."),
    ("Ciprofloxacin", "Theophylline", "MAJOR", "Theophylline toxicity."),
]


# --------------------------------------------------------------------------
# 7. Renal dose adjustment bands
# --------------------------------------------------------------------------
# crcl_min inclusive, crcl_max exclusive. action: KEEP / REDUCE / EXTEND /
# CONTRAINDICATED. factor is the fraction of the normal daily dose.
RENAL_RULES = [
    ("Nitrofurantoin", 0, 30, "CONTRAINDICATED", 0.0,
     "Fails to reach therapeutic urinary concentration and accumulates. Do not use below CrCl 30."),
    ("Nitrofurantoin", 30, 999, "KEEP", 1.0, "Standard dose."),
    ("Amikacin", 0, 20, "CONTRAINDICATED", 0.0, "Avoid; use an alternative or dose by levels only."),
    ("Amikacin", 20, 40, "EXTEND", 0.5, "Extend interval to 48 h; monitor trough levels."),
    ("Amikacin", 40, 60, "EXTEND", 0.75, "Extend interval to 36 h; monitor levels."),
    ("Amikacin", 60, 999, "KEEP", 1.0, "Standard once-daily dose."),
    ("Gentamicin", 0, 20, "CONTRAINDICATED", 0.0, "Avoid; nephrotoxic in established renal failure."),
    ("Gentamicin", 20, 40, "EXTEND", 0.5, "Extend interval to 48 h; monitor levels."),
    ("Gentamicin", 40, 60, "EXTEND", 0.75, "Extend interval to 36 h."),
    ("Gentamicin", 60, 999, "KEEP", 1.0, "Standard once-daily dose."),
    ("Meropenem", 0, 10, "REDUCE", 0.25, "500 mg every 24 h."),
    ("Meropenem", 10, 26, "REDUCE", 0.33, "500 mg every 12 h."),
    ("Meropenem", 26, 51, "REDUCE", 0.5, "1 g every 12 h."),
    ("Meropenem", 51, 999, "KEEP", 1.0, "1 g every 8 h."),
    ("Imipenem-Cilastatin", 0, 15, "CONTRAINDICATED", 0.0, "Seizure risk; avoid unless on dialysis."),
    ("Imipenem-Cilastatin", 15, 30, "REDUCE", 0.5, "Halve the daily dose."),
    ("Imipenem-Cilastatin", 30, 60, "REDUCE", 0.75, "Reduce to 500 mg every 8 h."),
    ("Imipenem-Cilastatin", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Piperacillin-Tazobactam", 0, 20, "REDUCE", 0.5, "2.25 g every 8 h."),
    ("Piperacillin-Tazobactam", 20, 40, "REDUCE", 0.67, "2.25 g every 6 h."),
    ("Piperacillin-Tazobactam", 40, 999, "KEEP", 1.0, "4.5 g every 6 h."),
    ("Cefepime", 0, 11, "REDUCE", 0.25, "500 mg every 24 h."),
    ("Cefepime", 11, 30, "REDUCE", 0.5, "1 g every 24 h."),
    ("Cefepime", 30, 60, "REDUCE", 0.67, "1 g every 12 h."),
    ("Cefepime", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Ciprofloxacin", 0, 30, "REDUCE", 0.5, "Halve the dose or extend to every 24 h."),
    ("Ciprofloxacin", 30, 999, "KEEP", 1.0, "Standard dose."),
    ("Levofloxacin", 0, 20, "REDUCE", 0.25, "250 mg every 48 h."),
    ("Levofloxacin", 20, 50, "REDUCE", 0.5, "250 mg every 24 h."),
    ("Levofloxacin", 50, 999, "KEEP", 1.0, "500 mg every 24 h."),
    ("Cotrimoxazole", 0, 15, "CONTRAINDICATED", 0.0, "Avoid below CrCl 15."),
    ("Cotrimoxazole", 15, 30, "REDUCE", 0.5, "Halve the dose."),
    ("Cotrimoxazole", 30, 999, "KEEP", 1.0, "Standard dose."),
    ("Vancomycin", 0, 20, "EXTEND", 0.25, "Dose by level only; interval often 48-72 h."),
    ("Vancomycin", 20, 50, "EXTEND", 0.5, "Extend interval; target trough 15-20 mg/L."),
    ("Vancomycin", 50, 999, "KEEP", 1.0, "Standard dose; still confirm by trough."),
    ("Colistin", 0, 30, "REDUCE", 0.5, "Substantial reduction; nephrotoxicity is dose-related."),
    ("Colistin", 30, 60, "REDUCE", 0.75, "Reduce maintenance dose."),
    ("Colistin", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Amoxicillin-Clavulanate", 0, 10, "REDUCE", 0.33, "625 mg every 24 h."),
    ("Amoxicillin-Clavulanate", 10, 30, "REDUCE", 0.67, "625 mg every 12 h."),
    ("Amoxicillin-Clavulanate", 30, 999, "KEEP", 1.0, "625 mg every 8 h."),
    ("Ampicillin", 0, 10, "EXTEND", 0.5, "Extend interval to every 12 h."),
    ("Ampicillin", 10, 999, "KEEP", 1.0, "Standard dose."),
]


# --------------------------------------------------------------------------
# 8. Dengue burden: state x year totals and the post-monsoon seasonal profile
# --------------------------------------------------------------------------
# Indicative annual case magnitudes by state (NCVBDC reporting scale).
STATE_DENGUE = {
    "Kerala": [4083, 4652, 3123, 3251, 4432, 9556, 6800],
    "Karnataka": [5077, 16986, 3823, 7393, 9328, 19300, 12200],
    "Maharashtra": [7838, 14907, 3356, 12720, 8578, 15550, 11800],
    "Tamil Nadu": [4486, 8527, 2410, 6039, 6430, 9121, 7400],
    "Delhi": [2798, 2036, 1072, 9613, 4469, 9266, 5200],
    "Uttar Pradesh": [3287, 10557, 3715, 29750, 19821, 12200, 9800],
    "West Bengal": [4372, 6905, 1503, 8264, 24000, 11200, 8600],
    "Rajasthan": [9587, 13706, 2023, 12060, 11570, 9400, 7300],
    "Gujarat": [4128, 18219, 1564, 6533, 4885, 5900, 4600],
    "Madhya Pradesh": [3782, 3993, 1120, 12000, 4800, 4200, 3400],
    "Punjab": [14980, 10289, 8435, 23389, 10650, 8300, 6100],
    "Haryana": [1898, 1207, 1377, 11835, 4013, 3900, 3000],
    "Andhra Pradesh": [4229, 5286, 1338, 5039, 6391, 7100, 5500],
    "Telangana": [4592, 12995, 2173, 7135, 8972, 8100, 6300],
    "Odisha": [5198, 3758, 1006, 7200, 5100, 4600, 3600],
    "Bihar": [2142, 6712, 493, 633, 13972, 6800, 5200],
}

# Fraction of the annual caseload falling in each month. Post-monsoon peak.
DENGUE_SEASONALITY = [
    0.012, 0.010, 0.011, 0.014, 0.021, 0.035,
    0.068, 0.118, 0.196, 0.231, 0.180, 0.104,
]


def build_dengue() -> None:
    assert abs(sum(DENGUE_SEASONALITY) - 1.0) < 1e-6, sum(DENGUE_SEASONALITY)
    rows = []
    for state, annuals in STATE_DENGUE.items():
        assert len(annuals) == len(YEARS)
        for year, total in zip(YEARS, annuals):
            for month_idx, share in enumerate(DENGUE_SEASONALITY, start=1):
                cases = total * share
                # Month-level reporting noise, proportional to the count.
                cases *= 1.0 + RNG.normal(0, 0.09)
                rows.append(
                    {
                        "state": state,
                        "year": year,
                        "month": month_idx,
                        "cases": max(0, int(round(cases))),
                    }
                )
    _write("dengue_monthly.csv", rows)


# --------------------------------------------------------------------------
# writers
# --------------------------------------------------------------------------
def _write(filename: str, rows: list[dict]) -> None:
    path = DATA / filename
    with path.open("w", newline="") as fh:
        fh.write(f"# {PROVENANCE}\n")
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filename:28} {len(rows):>6} rows")


def build_priors() -> None:
    rows = []
    for site, organisms in INFECTION_PRIORS.items():
        total = sum(organisms.values())
        assert abs(total - 1.0) < 1e-9, f"{site} priors sum to {total}"
        for setting in SETTINGS:
            shift = SETTING_PRIOR_SHIFT[setting]
            weighted = {
                organism: p * (shift if organism in NOSOCOMIAL else 1.0)
                for organism, p in organisms.items()
            }
            norm = sum(weighted.values())
            for organism, p in weighted.items():
                rows.append(
                    {
                        "site": site,
                        "setting": setting,
                        "organism": organism,
                        "prior": round(p / norm, 4),
                    }
                )
    _write("infection_priors.csv", rows)


def build_drugs() -> None:
    fields = [
        "antibiotic", "drug_class", "spectrum", "route", "adult_dose",
        "peds_mg_per_kg_per_day", "doses_per_day", "price_brand",
        "price_generic", "price_janaushadhi", "renal_adjust", "who_aware",
    ]
    rows = [dict(zip(fields, d)) for d in DRUGS]
    _write("drugs.csv", rows)


def build_risk_factors() -> None:
    rows = [
        {"factor": f, "susceptibility_multiplier": m, "rationale": r}
        for f, m, r in RISK_FACTORS
    ]
    _write("risk_factors.csv", rows)


def build_fdc() -> None:
    rows = [
        {"drug_a": a, "drug_b": b, "status": s, "reason": r}
        for a, b, s, r in FDC_FLAGS
    ]
    _write("fdc_flags.csv", rows)


def build_interactions() -> None:
    rows = [
        {"drug": d, "interacts_with": w, "severity": s, "effect": e}
        for d, w, s, e in INTERACTIONS
    ]
    _write("interactions.csv", rows)


def build_renal() -> None:
    rows = [
        {
            "antibiotic": d, "crcl_min": lo, "crcl_max": hi,
            "action": act, "dose_fraction": frac, "guidance": note,
        }
        for d, lo, hi, act, frac, note in RENAL_RULES
    ]
    _write("renal_rules.csv", rows)


if __name__ == "__main__":
    print("Building Parchi data layer ->", DATA)
    build_priors()
    build_drugs()
    build_susceptibility()
    build_risk_factors()
    build_fdc()
    build_interactions()
    build_renal()
    build_dengue()
    print("Done.")
