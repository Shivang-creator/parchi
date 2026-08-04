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
    Network (AMRSN) annual reports and WHO GLASS. Values are anchored at an
    earlier and a recent endpoint; intermediate years are reconstructed by
    interpolation plus noise. The *direction and magnitude* of each trend are
    real; the individual year points are not observations.
  - Prices are indicative Indian retail ranges for brand / generic / PMBJP
    (Jan Aushadhi) tiers. NPPA publishes binding ceiling prices per pack.
  - Banned / irrational fixed-dose combinations are drawn from CDSCO's
    published prohibition lists.
  - Course durations follow the short-course direction of current infectious
    disease guidance (IDSA / ATS / WSES), where the consistent finding of the
    last decade is that shorter is non-inferior for most indications.
  - Vector-borne burden uses realistic state-level magnitudes and the
    documented seasonal profiles reported by NCVBDC.

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
# 1. Organisms
# --------------------------------------------------------------------------
GRAM = {
    "Escherichia coli": "gram-negative",
    "Klebsiella pneumoniae": "gram-negative",
    "Pseudomonas aeruginosa": "gram-negative",
    "Acinetobacter baumannii": "gram-negative",
    "Proteus mirabilis": "gram-negative",
    "Enterobacter cloacae": "gram-negative",
    "Citrobacter spp": "gram-negative",
    "Salmonella Typhi": "gram-negative",
    "Salmonella Paratyphi A": "gram-negative",
    "Staphylococcus aureus": "gram-positive",
    "Coagulase-negative Staph": "gram-positive",
    "Enterococcus spp": "gram-positive",
    "Streptococcus pneumoniae": "gram-positive",
    "Streptococcus pyogenes": "gram-positive",
    "Haemophilus influenzae": "gram-negative",
    "Atypical pathogens": "atypical",
    "Bacteroides fragilis": "anaerobe",
}


# --------------------------------------------------------------------------
# 2. What causes what — P(organism | site) at the OUTPATIENT baseline
# --------------------------------------------------------------------------
INFECTION_PRIORS = {
    "Urinary tract infection": {
        "Escherichia coli": 0.55,
        "Klebsiella pneumoniae": 0.17,
        "Enterococcus spp": 0.09,
        "Proteus mirabilis": 0.07,
        "Pseudomonas aeruginosa": 0.06,
        "Citrobacter spp": 0.03,
        "Acinetobacter baumannii": 0.02,
        "Staphylococcus aureus": 0.01,
    },
    "Bloodstream infection / sepsis": {
        "Klebsiella pneumoniae": 0.22,
        "Escherichia coli": 0.20,
        "Staphylococcus aureus": 0.16,
        "Acinetobacter baumannii": 0.13,
        "Coagulase-negative Staph": 0.10,
        "Pseudomonas aeruginosa": 0.09,
        "Enterococcus spp": 0.08,
        "Enterobacter cloacae": 0.02,
    },
    "Pneumonia — community acquired": {
        # Klebsiella carries more weight here than in Western series — it is a
        # genuine community pathogen in India — but the mix is still dominated
        # by pneumococcus, atypicals and Haemophilus. An earlier version of
        # this table used a hospitalised-pneumonia mix and the model duly
        # recommended a carbapenem for an ambulatory patient.
        "Streptococcus pneumoniae": 0.32,
        "Atypical pathogens": 0.20,
        "Haemophilus influenzae": 0.16,
        "Klebsiella pneumoniae": 0.14,
        "Staphylococcus aureus": 0.10,
        "Escherichia coli": 0.04,
        "Pseudomonas aeruginosa": 0.02,
        "Acinetobacter baumannii": 0.02,
    },
    "Pneumonia — hospital / ventilator": {
        "Acinetobacter baumannii": 0.30,
        "Klebsiella pneumoniae": 0.26,
        "Pseudomonas aeruginosa": 0.22,
        "Staphylococcus aureus": 0.13,
        "Escherichia coli": 0.06,
        "Enterobacter cloacae": 0.03,
    },
    "Skin / soft tissue": {
        "Staphylococcus aureus": 0.52,
        "Streptococcus pyogenes": 0.16,
        "Pseudomonas aeruginosa": 0.11,
        "Escherichia coli": 0.09,
        "Klebsiella pneumoniae": 0.07,
        "Enterococcus spp": 0.05,
    },
    "Intra-abdominal": {
        "Escherichia coli": 0.38,
        "Klebsiella pneumoniae": 0.19,
        "Bacteroides fragilis": 0.16,
        "Enterococcus spp": 0.13,
        "Pseudomonas aeruginosa": 0.08,
        "Acinetobacter baumannii": 0.06,
    },
    "Diabetic foot infection": {
        "Staphylococcus aureus": 0.34,
        "Pseudomonas aeruginosa": 0.18,
        "Escherichia coli": 0.14,
        "Klebsiella pneumoniae": 0.12,
        "Enterococcus spp": 0.10,
        "Bacteroides fragilis": 0.07,
        "Proteus mirabilis": 0.05,
    },
    "Surgical site infection": {
        "Staphylococcus aureus": 0.36,
        "Escherichia coli": 0.19,
        "Klebsiella pneumoniae": 0.16,
        "Pseudomonas aeruginosa": 0.12,
        "Enterococcus spp": 0.09,
        "Acinetobacter baumannii": 0.08,
    },
    "Bacterial meningitis": {
        "Streptococcus pneumoniae": 0.42,
        "Haemophilus influenzae": 0.10,
        "Klebsiella pneumoniae": 0.15,
        "Escherichia coli": 0.13,
        "Staphylococcus aureus": 0.10,
        "Acinetobacter baumannii": 0.10,
    },
    "Febrile neutropenia": {
        "Escherichia coli": 0.26,
        "Klebsiella pneumoniae": 0.24,
        "Pseudomonas aeruginosa": 0.18,
        "Coagulase-negative Staph": 0.13,
        "Acinetobacter baumannii": 0.11,
        "Staphylococcus aureus": 0.08,
    },
    "Enteric fever (typhoid)": {
        "Salmonella Typhi": 0.80,
        "Salmonella Paratyphi A": 0.17,
        "Escherichia coli": 0.03,
    },
}

# An ICU infection is a different disease from the same-named OPD infection:
# catheters, ventilators and prior antibiotic exposure select hard for
# hospital-dwelling organisms while community organisms recede.
NOSOCOMIAL = {
    "Acinetobacter baumannii",
    "Pseudomonas aeruginosa",
    "Klebsiella pneumoniae",
    "Enterococcus spp",
    "Enterobacter cloacae",
    "Citrobacter spp",
    "Coagulase-negative Staph",
}
SETTING_PRIOR_SHIFT = {"OPD": 0.40, "Ward": 1.20, "ICU": 1.95}

# Infections that only ever occur in one context — a ventilator-associated
# pneumonia has no outpatient form, and shifting its priors is meaningless.
SITE_SETTINGS = {
    "Pneumonia — hospital / ventilator": ["Ward", "ICU"],
    "Febrile neutropenia": ["Ward", "ICU"],
    "Bacterial meningitis": ["Ward", "ICU"],
}


# --------------------------------------------------------------------------
# 3. Formulary
# --------------------------------------------------------------------------
# spectrum: 1 = narrow (stewardship-preferred) .. 5 = last-line (reserve)
# Prices are INR per unit dose (tablet or vial).
DRUGS = [
    # name, class, spectrum, route, adult_dose, peds_mg_kg_day, doses/day,
    # brand, generic, janaushadhi, renal_adjust, who_aware
    ("Nitrofurantoin", "Nitrofuran", 1, "PO", "100 mg", 5, 2, 12.0, 6.0, 3.0, 1, "Access"),
    ("Fosfomycin", "Phosphonic acid", 1, "PO", "3 g sachet", 0, 1, 320.0, 190.0, 0.0, 1, "Access"),
    ("Cotrimoxazole", "Folate inhibitor", 1, "PO", "960 mg (DS)", 8, 2, 6.0, 2.5, 1.0, 1, "Access"),
    ("Doxycycline", "Tetracycline", 2, "PO", "100 mg", 4, 2, 8.0, 3.0, 1.5, 0, "Access"),
    ("Minocycline", "Tetracycline", 3, "PO/IV", "100 mg", 4, 2, 26.0, 12.0, 0.0, 0, "Watch"),
    ("Metronidazole", "Nitroimidazole", 1, "PO/IV", "500 mg", 30, 3, 9.0, 4.0, 2.0, 0, "Access"),
    ("Amoxicillin", "Aminopenicillin", 1, "PO", "500 mg", 45, 3, 9.0, 4.0, 2.0, 1, "Access"),
    ("Amoxicillin-Clavulanate", "Beta-lactam/BLI", 2, "PO", "625 mg", 30, 3, 15.0, 8.0, 4.0, 1, "Access"),
    ("Ampicillin", "Aminopenicillin", 1, "IV", "1 g", 100, 4, 18.0, 9.0, 5.0, 1, "Access"),
    ("Clindamycin", "Lincosamide", 2, "PO/IV", "600 mg", 25, 3, 42.0, 18.0, 9.0, 0, "Access"),
    ("Azithromycin", "Macrolide", 2, "PO", "500 mg", 10, 1, 35.0, 12.0, 6.0, 0, "Watch"),
    ("Cefuroxime", "2nd-gen cephalosporin", 2, "PO/IV", "500 mg", 30, 2, 26.0, 12.0, 6.0, 1, "Watch"),
    ("Cefixime", "3rd-gen cephalosporin", 3, "PO", "200 mg", 8, 2, 18.0, 8.0, 4.0, 1, "Watch"),
    ("Ciprofloxacin", "Fluoroquinolone", 3, "PO", "500 mg", 20, 2, 12.0, 4.0, 2.0, 1, "Watch"),
    ("Levofloxacin", "Fluoroquinolone", 3, "PO", "500 mg", 10, 1, 28.0, 10.0, 5.0, 1, "Watch"),
    ("Gentamicin", "Aminoglycoside", 2, "IV", "5 mg/kg", 5, 1, 22.0, 11.0, 6.0, 1, "Access"),
    ("Amikacin", "Aminoglycoside", 3, "IV", "15 mg/kg", 15, 1, 60.0, 30.0, 16.0, 1, "Access"),
    ("Ceftriaxone", "3rd-gen cephalosporin", 3, "IV", "1 g", 75, 1, 60.0, 25.0, 15.0, 0, "Watch"),
    ("Ceftazidime", "3rd-gen cephalosporin", 3, "IV", "1 g", 100, 3, 90.0, 42.0, 0.0, 1, "Watch"),
    ("Cefepime", "4th-gen cephalosporin", 4, "IV", "1 g", 100, 3, 200.0, 90.0, 0.0, 1, "Watch"),
    ("Cefoperazone-Sulbactam", "Beta-lactam/BLI", 4, "IV", "1.5 g", 80, 2, 260.0, 120.0, 0.0, 1, "Watch"),
    ("Piperacillin-Tazobactam", "Beta-lactam/BLI", 4, "IV", "4.5 g", 300, 4, 450.0, 200.0, 0.0, 1, "Watch"),
    ("Ertapenem", "Carbapenem", 4, "IV", "1 g", 30, 1, 1400.0, 620.0, 0.0, 1, "Watch"),
    ("Meropenem", "Carbapenem", 5, "IV", "1 g", 60, 3, 1100.0, 350.0, 0.0, 1, "Watch"),
    ("Imipenem-Cilastatin", "Carbapenem", 5, "IV", "500 mg", 60, 4, 600.0, 280.0, 0.0, 1, "Watch"),
    ("Vancomycin", "Glycopeptide", 4, "IV", "1 g", 45, 2, 400.0, 180.0, 0.0, 1, "Watch"),
    ("Teicoplanin", "Glycopeptide", 4, "IV", "400 mg", 10, 1, 620.0, 310.0, 0.0, 1, "Watch"),
    ("Linezolid", "Oxazolidinone", 4, "PO/IV", "600 mg", 30, 2, 90.0, 35.0, 18.0, 0, "Reserve"),
    ("Tigecycline", "Glycylcycline", 5, "IV", "50 mg", 0, 2, 1600.0, 700.0, 0.0, 0, "Reserve"),
    ("Colistin", "Polymyxin", 5, "IV", "3 MIU", 75, 3, 520.0, 300.0, 0.0, 1, "Reserve"),
    ("Ceftazidime-Avibactam", "Beta-lactam/BLI", 5, "IV", "2.5 g", 0, 3, 8200.0, 5400.0, 0.0, 1, "Reserve"),
]


# --------------------------------------------------------------------------
# 4. Susceptibility: %S at OPD, (2018, 2024)
# --------------------------------------------------------------------------
# An ABSENT pair means the drug has no useful activity against that organism
# and is scored as zero cover — deliberate and clinically meaningful.
# Vancomycin/teicoplanin/linezolid genuinely cannot touch gram-negatives;
# colistin and aztreonam-class agents cannot touch gram-positives;
# cephalosporins have no enterococcal activity; ertapenem and tigecycline have
# no useful Pseudomonas activity; nitrofurantoin has none against Proteus.
# Those holes are the model working, not missing data.
#
# Conversely, carbapenems and piperacillin-tazobactam DO cover MSSA and
# E. faecalis, so those pairs are present — their ceiling is set by the local
# MSSA / E. faecalis share rather than by any resistance of their own.
SUSCEPTIBILITY_ANCHORS = {
    "Escherichia coli": {
        "Nitrofurantoin": (92, 86), "Fosfomycin": (97, 94),
        "Cotrimoxazole": (32, 25), "Doxycycline": (40, 33),
        "Amoxicillin": (18, 11), "Amoxicillin-Clavulanate": (48, 34),
        "Ampicillin": (18, 10), "Cefuroxime": (34, 22), "Cefixime": (28, 16),
        "Ciprofloxacin": (24, 13), "Levofloxacin": (28, 16),
        "Gentamicin": (72, 62), "Amikacin": (88, 79),
        "Ceftriaxone": (28, 17), "Ceftazidime": (30, 19), "Cefepime": (42, 27),
        "Cefoperazone-Sulbactam": (74, 60),
        "Piperacillin-Tazobactam": (72, 56),
        "Ertapenem": (86, 68), "Meropenem": (88, 70), "Imipenem-Cilastatin": (89, 72),
        "Tigecycline": (97, 95), "Colistin": (99, 96),
        "Ceftazidime-Avibactam": (94, 85),
    },
    "Klebsiella pneumoniae": {
        "Nitrofurantoin": (42, 33), "Fosfomycin": (80, 70),
        "Cotrimoxazole": (35, 26),
        "Amoxicillin-Clavulanate": (38, 25), "Cefuroxime": (30, 18),
        "Cefixime": (26, 14),
        "Ciprofloxacin": (35, 22), "Levofloxacin": (38, 25),
        "Gentamicin": (55, 42), "Amikacin": (70, 56),
        "Ceftriaxone": (30, 16), "Ceftazidime": (31, 17), "Cefepime": (38, 23),
        "Cefoperazone-Sulbactam": (60, 46),
        "Piperacillin-Tazobactam": (58, 40),
        "Ertapenem": (68, 46), "Meropenem": (72, 50), "Imipenem-Cilastatin": (73, 52),
        "Tigecycline": (90, 84), "Colistin": (97, 92),
        "Ceftazidime-Avibactam": (80, 62),
    },
    "Pseudomonas aeruginosa": {
        # No ertapenem, no tigecycline — intrinsically inactive.
        "Ciprofloxacin": (68, 58), "Levofloxacin": (66, 56),
        "Gentamicin": (66, 57), "Amikacin": (78, 70),
        "Ceftazidime": (72, 62), "Cefepime": (74, 64),
        "Cefoperazone-Sulbactam": (70, 60),
        "Piperacillin-Tazobactam": (76, 66),
        "Meropenem": (74, 62), "Imipenem-Cilastatin": (72, 60),
        "Colistin": (98, 95), "Ceftazidime-Avibactam": (90, 84),
    },
    "Acinetobacter baumannii": {
        # No ertapenem. Minocycline and colistin are what is left.
        "Cotrimoxazole": (30, 22), "Doxycycline": (52, 44), "Minocycline": (68, 58),
        "Ciprofloxacin": (24, 14), "Levofloxacin": (28, 18),
        "Gentamicin": (32, 22), "Amikacin": (38, 27),
        "Ceftazidime": (26, 15), "Cefepime": (26, 16),
        "Cefoperazone-Sulbactam": (48, 34),
        "Piperacillin-Tazobactam": (28, 18),
        "Meropenem": (34, 20), "Imipenem-Cilastatin": (35, 21),
        "Tigecycline": (86, 78), "Colistin": (96, 90),
    },
    "Proteus mirabilis": {
        # Intrinsically resistant to nitrofurantoin, colistin and tigecycline —
        # all three absent. This matters: nitrofurantoin is the default UTI
        # drug and it does nothing here.
        "Cotrimoxazole": (42, 35), "Amoxicillin-Clavulanate": (62, 52),
        "Ampicillin": (40, 30), "Cefuroxime": (58, 46), "Cefixime": (52, 40),
        "Ciprofloxacin": (38, 28), "Levofloxacin": (40, 30),
        "Gentamicin": (72, 62), "Amikacin": (86, 78),
        "Ceftriaxone": (48, 35), "Ceftazidime": (50, 38), "Cefepime": (58, 46),
        "Cefoperazone-Sulbactam": (76, 66),
        "Piperacillin-Tazobactam": (82, 72),
        "Ertapenem": (92, 84), "Meropenem": (94, 86), "Imipenem-Cilastatin": (86, 78),
        "Ceftazidime-Avibactam": (96, 92),
    },
    "Enterobacter cloacae": {
        # AmpC producer — third-generation cephalosporins fail even when they
        # test susceptible, hence the deliberately low ceftriaxone figure.
        "Cotrimoxazole": (52, 44), "Ciprofloxacin": (58, 46),
        "Levofloxacin": (60, 48), "Gentamicin": (68, 58), "Amikacin": (84, 76),
        "Ceftriaxone": (38, 26), "Ceftazidime": (40, 28), "Cefepime": (76, 66),
        "Cefoperazone-Sulbactam": (66, 56),
        "Piperacillin-Tazobactam": (62, 50),
        "Ertapenem": (78, 62), "Meropenem": (84, 72), "Imipenem-Cilastatin": (85, 74),
        "Tigecycline": (92, 87), "Colistin": (96, 92),
        "Ceftazidime-Avibactam": (90, 82),
    },
    "Citrobacter spp": {
        "Nitrofurantoin": (62, 54), "Cotrimoxazole": (50, 42),
        "Ciprofloxacin": (52, 40), "Levofloxacin": (54, 42),
        "Gentamicin": (66, 56), "Amikacin": (82, 74),
        "Ceftriaxone": (40, 28), "Cefepime": (72, 62),
        "Cefoperazone-Sulbactam": (66, 55),
        "Piperacillin-Tazobactam": (64, 52),
        "Ertapenem": (80, 66), "Meropenem": (86, 74), "Imipenem-Cilastatin": (86, 75),
        "Tigecycline": (92, 88), "Colistin": (96, 92),
    },
    "Staphylococcus aureus": {
        # Every beta-lactam here is capped by the local MSSA share: MRSA is
        # resistant to all of them whatever the zone diameter says.
        "Cotrimoxazole": (78, 72), "Doxycycline": (86, 82), "Minocycline": (88, 84),
        "Clindamycin": (70, 62),
        "Amoxicillin-Clavulanate": (68, 61), "Cefuroxime": (68, 61),
        "Azithromycin": (52, 42),
        "Ciprofloxacin": (54, 44), "Levofloxacin": (58, 48),
        "Gentamicin": (74, 68), "Amikacin": (82, 77),
        "Ceftriaxone": (68, 61), "Cefepime": (68, 61),
        "Cefoperazone-Sulbactam": (68, 61),
        "Piperacillin-Tazobactam": (68, 61),
        "Ertapenem": (68, 61), "Meropenem": (68, 61), "Imipenem-Cilastatin": (68, 61),
        "Vancomycin": (100, 100), "Teicoplanin": (100, 99),
        "Linezolid": (100, 99), "Tigecycline": (99, 99),
    },
    "Coagulase-negative Staph": {
        # Methicillin resistance is far commoner than in S. aureus, so the
        # beta-lactam ceiling is much lower.
        "Cotrimoxazole": (58, 50), "Doxycycline": (76, 70), "Clindamycin": (58, 50),
        "Amoxicillin-Clavulanate": (36, 28), "Cefuroxime": (36, 28),
        "Ciprofloxacin": (44, 34), "Levofloxacin": (48, 38),
        "Gentamicin": (56, 48), "Amikacin": (66, 58),
        "Ceftriaxone": (36, 28), "Cefepime": (36, 28),
        "Piperacillin-Tazobactam": (36, 28),
        "Meropenem": (36, 28), "Imipenem-Cilastatin": (36, 28),
        "Vancomycin": (100, 99), "Teicoplanin": (99, 98),
        "Linezolid": (100, 99), "Tigecycline": (99, 98),
    },
    "Enterococcus spp": {
        # Cephalosporins absent by design — intrinsic resistance to all of them.
        "Nitrofurantoin": (88, 83), "Fosfomycin": (94, 90),
        "Amoxicillin": (58, 47), "Ampicillin": (58, 47),
        "Amoxicillin-Clavulanate": (58, 47),
        "Piperacillin-Tazobactam": (60, 50),
        "Ertapenem": (54, 44), "Meropenem": (56, 46), "Imipenem-Cilastatin": (58, 48),
        "Ciprofloxacin": (32, 22), "Levofloxacin": (35, 25),
        "Vancomycin": (92, 86), "Teicoplanin": (93, 88),
        "Linezolid": (99, 98), "Tigecycline": (98, 97),
    },
    "Streptococcus pneumoniae": {
        "Cotrimoxazole": (48, 40), "Doxycycline": (72, 66), "Clindamycin": (82, 76),
        "Amoxicillin": (92, 88), "Ampicillin": (92, 88),
        "Amoxicillin-Clavulanate": (94, 90), "Cefuroxime": (90, 86),
        "Azithromycin": (70, 60),
        "Levofloxacin": (96, 94),
        "Ceftriaxone": (96, 94), "Cefepime": (96, 94),
        "Piperacillin-Tazobactam": (95, 93),
        "Ertapenem": (98, 97), "Meropenem": (99, 98), "Imipenem-Cilastatin": (99, 98),
        "Vancomycin": (100, 100), "Teicoplanin": (100, 100),
        "Linezolid": (100, 100), "Tigecycline": (99, 99),
    },
    "Streptococcus pyogenes": {
        # Still universally penicillin-susceptible worldwide — one of the very
        # few organisms where that remains true.
        "Amoxicillin": (100, 100), "Ampicillin": (100, 100),
        "Amoxicillin-Clavulanate": (100, 100), "Cefuroxime": (100, 100),
        "Ceftriaxone": (100, 100), "Clindamycin": (84, 78),
        "Azithromycin": (72, 62), "Doxycycline": (76, 70),
        "Levofloxacin": (96, 94), "Meropenem": (100, 100),
        "Vancomycin": (100, 100), "Linezolid": (100, 100),
    },
    "Bacteroides fragilis": {
        # Anaerobe. Aminoglycosides and fluoroquinolones are inactive — absent.
        "Metronidazole": (97, 95), "Clindamycin": (68, 58),
        "Amoxicillin-Clavulanate": (92, 88),
        "Cefoperazone-Sulbactam": (88, 84),
        "Piperacillin-Tazobactam": (94, 91),
        "Ertapenem": (96, 94), "Meropenem": (97, 95), "Imipenem-Cilastatin": (97, 95),
        "Tigecycline": (94, 91),
    },
    "Haemophilus influenzae": {
        "Amoxicillin": (74, 66),            # beta-lactamase production
        "Amoxicillin-Clavulanate": (94, 91),
        "Cefuroxime": (90, 86), "Cefixime": (96, 94),
        "Azithromycin": (94, 90), "Doxycycline": (88, 84),
        "Cotrimoxazole": (58, 48), "Levofloxacin": (99, 98),
        "Ceftriaxone": (99, 98), "Cefepime": (99, 98),
        "Piperacillin-Tazobactam": (96, 94),
        "Ertapenem": (99, 98), "Meropenem": (99, 99),
    },
    "Atypical pathogens": {
        # Mycoplasma, Chlamydophila, Legionella. They have no cell wall, so
        # EVERY beta-lactam is absent by design — no penicillin, no
        # cephalosporin, no carbapenem. This is the single commonest reason a
        # beta-lactam alone fails in community pneumonia.
        "Azithromycin": (94, 90), "Doxycycline": (97, 95),
        "Levofloxacin": (99, 98), "Minocycline": (96, 94),
    },
    "Salmonella Typhi": {
        "Cotrimoxazole": (94, 92), "Amoxicillin": (88, 85),
        "Ciprofloxacin": (14, 6), "Levofloxacin": (18, 8),
        "Azithromycin": (99, 98), "Cefixime": (96, 93),
        "Ceftriaxone": (98, 96), "Cefepime": (98, 96),
        "Meropenem": (100, 99),
    },
    "Salmonella Paratyphi A": {
        "Cotrimoxazole": (90, 87), "Amoxicillin": (84, 80),
        "Ciprofloxacin": (10, 4), "Levofloxacin": (14, 6),
        "Azithromycin": (98, 96), "Cefixime": (94, 90),
        "Ceftriaxone": (97, 95), "Cefepime": (97, 95),
        "Meropenem": (100, 99),
    },
}

SETTING_FACTOR = {"OPD": 1.00, "Ward": 0.86, "ICU": 0.71}


# --------------------------------------------------------------------------
# 5. Evidence-based course durations
# --------------------------------------------------------------------------
# Indian prescriptions routinely run far longer than the evidence supports.
# Every entry below reflects the short-course direction of the last decade of
# trials: for most indications, shorter is non-inferior.
DURATIONS = [
    # site, min_days, max_days, typical, note
    ("Urinary tract infection", 3, 7, 5,
     "Uncomplicated cystitis in women: 3 days of most agents, 5 for "
     "nitrofurantoin. Pyelonephritis 7. Anything longer adds resistance, "
     "not cure."),
    ("Bloodstream infection / sepsis", 7, 14, 7,
     "7 days is non-inferior to 14 for uncomplicated gram-negative "
     "bacteraemia. S. aureus bacteraemia is the exception — 14 days minimum, "
     "longer if endocarditis or a deep focus."),
    ("Pneumonia — community acquired", 3, 7, 5,
     "5 days, provided the patient is afebrile and clinically stable for 48 "
     "hours. Long courses are the commonest overuse in respiratory medicine."),
    ("Pneumonia — hospital / ventilator", 7, 8, 7,
     "7 days, including for non-fermenting gram-negatives. Longer courses "
     "have not shown benefit and select for resistance."),
    ("Skin / soft tissue", 5, 10, 6,
     "5-6 days for uncomplicated cellulitis with a good response. Extend only "
     "if the response is genuinely slow."),
    ("Intra-abdominal", 4, 7, 4,
     "4 days after adequate source control. If the patient is still septic, "
     "the answer is a second look at the source, not a longer course."),
    ("Diabetic foot infection", 7, 21, 10,
     "Soft-tissue infection 7-14 days. Osteomyelitis without resection needs "
     "6 weeks — a different decision entirely."),
    ("Surgical site infection", 5, 10, 7,
     "Drainage and debridement matter more than duration."),
    ("Bacterial meningitis", 10, 21, 14,
     "10-14 days for pneumococcus, 21 for gram-negative meningitis."),
    ("Febrile neutropenia", 7, 14, 7,
     "Continue until neutrophil recovery and the patient has been afebrile "
     "48 hours."),
    ("Enteric fever (typhoid)", 7, 14, 10,
     "7 days for azithromycin, 10-14 for ceftriaxone. Relapse is common if "
     "cut short."),
]


# --------------------------------------------------------------------------
# 6. Patient risk factors that shift the expected organism mix
# --------------------------------------------------------------------------
RISK_FACTORS = [
    ("Antibiotics in the last 90 days", 0.78, "Strongest single predictor of a resistant isolate"),
    ("Hospitalised in the last 90 days", 0.84, "Healthcare-associated exposure to nosocomial strains"),
    ("Indwelling urinary catheter", 0.86, "Biofilm-associated, typically MDR organisms"),
    ("Central venous line", 0.85, "Device-associated bloodstream organisms"),
    ("Mechanical ventilation", 0.80, "Ventilator-associated pneumonia skews to Acinetobacter/Pseudomonas"),
    ("Immunosuppressed / on chemotherapy", 0.88, "Broader organism range, lower reserve"),
    ("Resident of a long-term care facility", 0.85, "Colonisation with resistant flora"),
    ("Known prior MDR isolate", 0.62, "Past colonisation strongly predicts recurrence"),
    ("Diabetes mellitus", 0.93, "Higher burden of polymicrobial and resistant infection"),
    ("Chronic kidney disease on dialysis", 0.83, "Repeated vascular access and frequent hospital contact"),
]


# --------------------------------------------------------------------------
# 7. Banned / irrational fixed-dose combinations (CDSCO)
# --------------------------------------------------------------------------
FDC_FLAGS = [
    ("Cefixime", "Azithromycin", "BANNED",
     "Prohibited FDC. No evidence of added benefit; drives resistance in both classes."),
    ("Cefixime", "Ofloxacin", "BANNED",
     "Prohibited FDC. Two broad agents combined without rationale."),
    ("Cefixime", "Levofloxacin", "BANNED",
     "Prohibited FDC. Irrational dual cover."),
    ("Cefpodoxime", "Levofloxacin", "BANNED",
     "Prohibited FDC. Irrational dual gram-negative cover."),
    ("Cefpodoxime", "Ofloxacin", "BANNED", "Prohibited FDC."),
    ("Ceftriaxone", "Sulbactam", "IRRATIONAL",
     "Sulbactam adds nothing to ceftriaxone against ESBL producers; widely "
     "marketed in India regardless."),
    ("Ciprofloxacin", "Tinidazole", "IRRATIONAL",
     "Widely sold; fixed ratio prevents independent dosing and encourages overuse."),
    ("Ofloxacin", "Ornidazole", "IRRATIONAL",
     "Very common in Indian OPD for diarrhoea; little evidence, high resistance cost."),
    ("Levofloxacin", "Ornidazole", "IRRATIONAL",
     "Same pattern as ofloxacin-ornidazole."),
    ("Norfloxacin", "Tinidazole", "IRRATIONAL", "Same irrational pairing."),
    ("Amoxicillin", "Bromhexine", "BANNED",
     "Prohibited FDC. Mucolytic adds nothing to the antibiotic."),
    ("Amoxicillin", "Dicloxacillin", "IRRATIONAL",
     "Sub-therapeutic dicloxacillin component; does not reliably cover MSSA."),
    ("Nimesulide", "Paracetamol", "BANNED",
     "Prohibited FDC. Duplicated hepatotoxicity risk."),
    ("Diclofenac", "Serratiopeptidase", "IRRATIONAL",
     "No robust evidence for the enzyme component."),
    ("Pioglitazone", "Metformin+Glimepiride", "RESTRICTED",
     "Triple oral FDC; restricted use, high hypoglycaemia risk."),
    ("Chlorpheniramine", "Codeine", "RESTRICTED",
     "Restricted; dependence and paediatric respiratory depression risk."),
]


# --------------------------------------------------------------------------
# 8. Drug-drug interactions relevant to the formulary
# --------------------------------------------------------------------------
INTERACTIONS = [
    ("Linezolid", "SSRI / SNRI antidepressant", "MAJOR",
     "Serotonin syndrome. Linezolid is a reversible MAO inhibitor."),
    ("Linezolid", "Tramadol", "MAJOR", "Serotonin syndrome risk."),
    ("Ciprofloxacin", "Warfarin", "MAJOR", "INR rises sharply; bleeding risk."),
    ("Levofloxacin", "Warfarin", "MAJOR", "INR rises sharply; bleeding risk."),
    ("Cotrimoxazole", "Warfarin", "MAJOR", "Marked INR elevation."),
    ("Metronidazole", "Warfarin", "MAJOR", "Potentiates anticoagulation."),
    ("Metronidazole", "Alcohol", "MODERATE", "Disulfiram-like reaction."),
    ("Cotrimoxazole", "Methotrexate", "MAJOR", "Additive myelosuppression."),
    ("Linezolid", "Methotrexate", "MODERATE", "Additive myelosuppression."),
    ("Cotrimoxazole", "ACE inhibitor / ARB", "MODERATE", "Hyperkalaemia, especially in CKD."),
    ("Cotrimoxazole", "Spironolactone", "MAJOR", "Severe hyperkalaemia in older patients."),
    ("Azithromycin", "Ondansetron", "MODERATE", "Additive QT prolongation."),
    ("Levofloxacin", "Ondansetron", "MODERATE", "Additive QT prolongation."),
    ("Azithromycin", "Amiodarone", "MAJOR", "QT prolongation, torsades risk."),
    ("Levofloxacin", "Amiodarone", "MAJOR", "QT prolongation, torsades risk."),
    ("Amikacin", "Vancomycin", "MAJOR", "Additive nephrotoxicity."),
    ("Gentamicin", "Vancomycin", "MAJOR", "Additive nephrotoxicity."),
    ("Amikacin", "Furosemide", "MODERATE", "Additive oto- and nephrotoxicity."),
    ("Gentamicin", "Furosemide", "MODERATE", "Additive oto- and nephrotoxicity."),
    ("Colistin", "Amikacin", "MAJOR", "Compounded nephrotoxicity; monitor creatinine daily."),
    ("Colistin", "Vancomycin", "MAJOR", "Compounded nephrotoxicity."),
    ("Vancomycin", "Piperacillin-Tazobactam", "MODERATE",
     "This specific pair carries a higher acute kidney injury rate than either alone."),
    ("Ciprofloxacin", "Antacid / calcium / iron", "MODERATE",
     "Chelation cuts absorption. Separate doses by 2 hours."),
    ("Levofloxacin", "Antacid / calcium / iron", "MODERATE",
     "Chelation cuts absorption. Separate doses by 2 hours."),
    ("Doxycycline", "Antacid / calcium / iron", "MODERATE", "Chelation cuts absorption."),
    ("Ciprofloxacin", "Theophylline", "MAJOR", "Theophylline toxicity."),
    ("Clindamycin", "Neuromuscular blocker", "MODERATE", "Prolonged blockade."),
    ("Linezolid", "Rifampicin", "MODERATE", "Reduced linezolid exposure."),
]


# --------------------------------------------------------------------------
# 9. Renal dose adjustment bands
# --------------------------------------------------------------------------
RENAL_RULES = [
    ("Nitrofurantoin", 0, 30, "CONTRAINDICATED", 0.0,
     "Fails to reach therapeutic urinary concentration and accumulates. Do not use below CrCl 30."),
    ("Nitrofurantoin", 30, 999, "KEEP", 1.0, "Standard dose."),
    ("Fosfomycin", 0, 20, "CONTRAINDICATED", 0.0, "Inadequate urinary concentration."),
    ("Fosfomycin", 20, 999, "KEEP", 1.0, "Single 3 g sachet."),
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
    ("Ertapenem", 0, 30, "REDUCE", 0.5, "500 mg every 24 h."),
    ("Ertapenem", 30, 999, "KEEP", 1.0, "1 g every 24 h."),
    ("Imipenem-Cilastatin", 0, 15, "CONTRAINDICATED", 0.0, "Seizure risk; avoid unless on dialysis."),
    ("Imipenem-Cilastatin", 15, 30, "REDUCE", 0.5, "Halve the daily dose."),
    ("Imipenem-Cilastatin", 30, 60, "REDUCE", 0.75, "Reduce to 500 mg every 8 h."),
    ("Imipenem-Cilastatin", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Piperacillin-Tazobactam", 0, 20, "REDUCE", 0.5, "2.25 g every 8 h."),
    ("Piperacillin-Tazobactam", 20, 40, "REDUCE", 0.67, "2.25 g every 6 h."),
    ("Piperacillin-Tazobactam", 40, 999, "KEEP", 1.0, "4.5 g every 6 h."),
    ("Cefoperazone-Sulbactam", 0, 30, "REDUCE", 0.5,
     "Sulbactam is renally cleared; halve the dose."),
    ("Cefoperazone-Sulbactam", 30, 999, "KEEP", 1.0, "Standard dose."),
    ("Cefepime", 0, 11, "REDUCE", 0.25, "500 mg every 24 h."),
    ("Cefepime", 11, 30, "REDUCE", 0.5, "1 g every 24 h."),
    ("Cefepime", 30, 60, "REDUCE", 0.67, "1 g every 12 h."),
    ("Cefepime", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Ceftazidime", 0, 15, "REDUCE", 0.25, "500 mg every 24 h."),
    ("Ceftazidime", 15, 30, "REDUCE", 0.5, "1 g every 24 h."),
    ("Ceftazidime", 30, 50, "REDUCE", 0.67, "1 g every 12 h."),
    ("Ceftazidime", 50, 999, "KEEP", 1.0, "Standard dose."),
    ("Cefuroxime", 0, 10, "REDUCE", 0.33, "750 mg every 24 h."),
    ("Cefuroxime", 10, 20, "REDUCE", 0.5, "750 mg every 12 h."),
    ("Cefuroxime", 20, 999, "KEEP", 1.0, "Standard dose."),
    ("Cefixime", 0, 20, "REDUCE", 0.5, "Halve the dose."),
    ("Cefixime", 20, 999, "KEEP", 1.0, "Standard dose."),
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
    ("Teicoplanin", 0, 30, "EXTEND", 0.33, "Every third day after loading."),
    ("Teicoplanin", 30, 60, "EXTEND", 0.5, "Alternate days after loading."),
    ("Teicoplanin", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Colistin", 0, 30, "REDUCE", 0.5, "Substantial reduction; nephrotoxicity is dose-related."),
    ("Colistin", 30, 60, "REDUCE", 0.75, "Reduce maintenance dose."),
    ("Colistin", 60, 999, "KEEP", 1.0, "Standard dose."),
    ("Ceftazidime-Avibactam", 0, 15, "REDUCE", 0.25, "0.94 g every 48 h."),
    ("Ceftazidime-Avibactam", 15, 30, "REDUCE", 0.375, "0.94 g every 24 h."),
    ("Ceftazidime-Avibactam", 30, 50, "REDUCE", 0.5, "1.25 g every 8 h."),
    ("Ceftazidime-Avibactam", 50, 999, "KEEP", 1.0, "2.5 g every 8 h."),
    ("Amoxicillin-Clavulanate", 0, 10, "REDUCE", 0.33, "625 mg every 24 h."),
    ("Amoxicillin-Clavulanate", 10, 30, "REDUCE", 0.67, "625 mg every 12 h."),
    ("Amoxicillin-Clavulanate", 30, 999, "KEEP", 1.0, "625 mg every 8 h."),
    ("Amoxicillin", 0, 10, "REDUCE", 0.33, "500 mg every 24 h."),
    ("Amoxicillin", 10, 30, "REDUCE", 0.67, "500 mg every 12 h."),
    ("Amoxicillin", 30, 999, "KEEP", 1.0, "500 mg every 8 h."),
    ("Ampicillin", 0, 10, "EXTEND", 0.5, "Extend interval to every 12 h."),
    ("Ampicillin", 10, 999, "KEEP", 1.0, "Standard dose."),
]


# --------------------------------------------------------------------------
# 10. Vector-borne burden — state x year x month
# --------------------------------------------------------------------------
# Indicative annual case magnitudes by state, on the NCVBDC reporting scale.
STATE_BURDEN = {
    "Dengue": {
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
        "Assam": [1136, 1310, 218, 1230, 2400, 1900, 1500],
        "Jharkhand": [452, 825, 132, 1200, 1600, 1400, 1100],
        "Chhattisgarh": [2072, 1500, 380, 2900, 1800, 1600, 1300],
        "Karnataka Rural": [1200, 3100, 900, 1700, 2100, 3800, 2600],
    },
    "Malaria": {
        "Odisha": [65284, 38680, 18425, 12200, 9800, 8400, 7100],
        "Chhattisgarh": [77000, 45300, 22100, 18600, 15200, 12800, 10900],
        "Jharkhand": [46800, 31200, 15600, 11400, 9100, 7800, 6600],
        "Maharashtra": [12500, 10200, 6800, 8100, 7400, 6900, 6200],
        "West Bengal": [16400, 12100, 5900, 6800, 6200, 5600, 5100],
        "Uttar Pradesh": [8900, 7200, 3400, 4100, 3800, 3500, 3200],
        "Madhya Pradesh": [9800, 7600, 3900, 4600, 4200, 3900, 3600],
        "Assam": [8200, 4100, 1600, 1900, 1700, 1500, 1300],
        "Gujarat": [6100, 4800, 2200, 2700, 2400, 2200, 2000],
        "Rajasthan": [4900, 3800, 1700, 2100, 1900, 1750, 1600],
    },
    "Chikungunya": {
        "Karnataka": [16000, 12800, 4200, 6100, 7400, 8900, 6800],
        "Maharashtra": [8900, 7200, 2100, 3400, 4100, 4800, 3700],
        "Delhi": [1600, 1100, 380, 890, 1200, 1400, 1000],
        "Gujarat": [4200, 3400, 980, 1600, 2000, 2400, 1800],
        "Tamil Nadu": [3100, 2500, 720, 1200, 1500, 1800, 1400],
        "Andhra Pradesh": [2400, 1900, 560, 940, 1200, 1400, 1100],
        "Telangana": [2100, 1700, 490, 820, 1050, 1250, 960],
    },
}

# Fraction of the annual caseload falling in each month.
SEASONALITY = {
    # Dengue: sharply post-monsoon.
    "Dengue": [0.012, 0.010, 0.011, 0.014, 0.021, 0.035,
               0.068, 0.118, 0.196, 0.231, 0.180, 0.104],
    # Malaria: monsoon-driven, broader and earlier than dengue.
    "Malaria": [0.030, 0.025, 0.028, 0.038, 0.055, 0.092,
                0.140, 0.158, 0.147, 0.118, 0.098, 0.071],
    # Chikungunya: tracks dengue, slightly earlier peak.
    "Chikungunya": [0.018, 0.015, 0.017, 0.024, 0.036, 0.058,
                    0.095, 0.140, 0.185, 0.195, 0.132, 0.085],
}

# How a confirmed case of each disease converts into hospital load. These are
# the numbers an administrator actually needs, and they differ sharply by
# disease — malaria rarely needs platelets, dengue frequently does.
DISEASE_LOAD = {
    #            opd_per_case, admit_rate, stay_days, transfuse_rate, units
    "Dengue":       (8.0, 0.10, 4.5, 0.32, 4.0),
    "Malaria":      (5.0, 0.07, 3.5, 0.04, 1.5),
    "Chikungunya":  (6.0, 0.03, 3.0, 0.02, 1.0),
}


# --------------------------------------------------------------------------
# builders
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
        for setting in SITE_SETTINGS.get(site, SETTINGS):
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
                        "gram": GRAM[organism],
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
    names = [r["antibiotic"] for r in rows]
    assert len(names) == len(set(names)), "duplicate drug in formulary"
    _write("drugs.csv", rows)


def build_susceptibility() -> None:
    formulary = {d[0] for d in DRUGS}
    rows = []
    for organism, drugs in SUSCEPTIBILITY_ANCHORS.items():
        unknown = set(drugs) - formulary
        assert not unknown, f"{organism} references drugs not in formulary: {unknown}"
        for drug, (early, recent) in drugs.items():
            for setting in SETTINGS:
                factor = SETTING_FACTOR[setting]
                for year in YEARS:
                    t = (year - YEARS[0]) / (YEARS[-1] - YEARS[0])
                    base = early + (recent - early) * t
                    value = base * factor
                    if year not in (YEARS[0], YEARS[-1]):
                        value += RNG.normal(0, 1.4)
                    rows.append(
                        {
                            "organism": organism,
                            "antibiotic": drug,
                            "setting": setting,
                            "year": year,
                            "percent_susceptible": round(
                                float(np.clip(value, 1.0, 100.0)), 1
                            ),
                        }
                    )
    _write("amr_susceptibility.csv", rows)


def build_durations() -> None:
    sites = set(INFECTION_PRIORS)
    rows = []
    for site, lo, hi, typical, note in DURATIONS:
        assert site in sites, f"duration for unknown site: {site}"
        rows.append(
            {
                "site": site, "min_days": lo, "max_days": hi,
                "typical_days": typical, "guidance": note,
            }
        )
    missing = sites - {r["site"] for r in rows}
    assert not missing, f"sites without a duration entry: {missing}"
    _write("durations.csv", rows)


def build_risk_factors() -> None:
    _write("risk_factors.csv", [
        {"factor": f, "susceptibility_multiplier": m, "rationale": r}
        for f, m, r in RISK_FACTORS
    ])


def build_fdc() -> None:
    _write("fdc_flags.csv", [
        {"drug_a": a, "drug_b": b, "status": s, "reason": r}
        for a, b, s, r in FDC_FLAGS
    ])


def build_interactions() -> None:
    _write("interactions.csv", [
        {"drug": d, "interacts_with": w, "severity": s, "effect": e}
        for d, w, s, e in INTERACTIONS
    ])


def build_renal() -> None:
    formulary = {d[0] for d in DRUGS}
    for rule in RENAL_RULES:
        assert rule[0] in formulary, f"renal rule for unknown drug: {rule[0]}"
    _write("renal_rules.csv", [
        {
            "antibiotic": d, "crcl_min": lo, "crcl_max": hi,
            "action": act, "dose_fraction": frac, "guidance": note,
        }
        for d, lo, hi, act, frac, note in RENAL_RULES
    ])


def build_burden() -> None:
    rows = []
    for disease, states in STATE_BURDEN.items():
        profile = SEASONALITY[disease]
        assert abs(sum(profile) - 1.0) < 1e-6, f"{disease} seasonality sums to {sum(profile)}"
        for state, annuals in states.items():
            assert len(annuals) == len(YEARS), f"{disease}/{state} wrong year count"
            for year, total in zip(YEARS, annuals):
                for month_idx, share in enumerate(profile, start=1):
                    cases = total * share * (1.0 + RNG.normal(0, 0.09))
                    rows.append(
                        {
                            "disease": disease, "state": state, "year": year,
                            "month": month_idx, "cases": max(0, int(round(cases))),
                        }
                    )
    _write("vector_burden.csv", rows)

    _write("disease_load.csv", [
        {
            "disease": d, "opd_per_case": o, "admission_rate": a,
            "mean_stay_days": s, "transfusion_rate": t, "units_per_transfusion": u,
        }
        for d, (o, a, s, t, u) in DISEASE_LOAD.items()
    ])




# --------------------------------------------------------------------------
# 11. NEWS2 — the reception desk's early warning score
# --------------------------------------------------------------------------
# The National Early Warning Score 2 is a real, validated, published
# instrument. Six physiological parameters plus consciousness, each banded,
# summed. It is what turns a registration desk from "first come, first served"
# into triage — and it needs only what a desk can actually measure.
#
# parameter, low, high, points  (bands are inclusive on both ends)
NEWS2_BANDS = [
    ("Respiration rate",  0,   8, 3), ("Respiration rate",  9,  11, 1),
    ("Respiration rate", 12,  20, 0), ("Respiration rate", 21,  24, 2),
    ("Respiration rate", 25, 200, 3),

    ("Oxygen saturation",  0,  91, 3), ("Oxygen saturation", 92,  93, 2),
    ("Oxygen saturation", 94,  95, 1), ("Oxygen saturation", 96, 100, 0),

    ("Systolic blood pressure",   0,  90, 3),
    ("Systolic blood pressure",  91, 100, 2),
    ("Systolic blood pressure", 101, 110, 1),
    ("Systolic blood pressure", 111, 219, 0),
    ("Systolic blood pressure", 220, 300, 3),

    ("Pulse",   0,  40, 3), ("Pulse",  41,  50, 1), ("Pulse",  51,  90, 0),
    ("Pulse",  91, 110, 1), ("Pulse", 111, 130, 2), ("Pulse", 131, 300, 3),

    ("Temperature", 0,    35.0, 3), ("Temperature", 35.1, 36.0, 1),
    ("Temperature", 36.1, 38.0, 0), ("Temperature", 38.1, 39.0, 1),
    ("Temperature", 39.1, 45.0, 2),
]

# score_min, score_max, band, response, minutes_to_review
NEWS2_RESPONSE = [
    (0, 0, "Routine", "Minimum 12-hourly observations. Continue routine monitoring.", 720),
    (1, 4, "Low", "Minimum 4-6 hourly observations. Nurse to decide whether "
                  "escalation of care is needed.", 240),
    (5, 6, "Medium", "Registered nurse to urgently inform the medical team. "
                     "Hourly observations. Assess in a monitored environment.", 60),
    (7, 30, "High", "Emergency response. Continuous monitoring. Immediate "
                    "assessment by a clinician with critical-care competencies.", 0),
]

# Departments an Indian OPD actually routes to, with realistic throughput.
DEPARTMENTS = [
    # name, patients per doctor per hour, doctors on duty, share of arrivals
    ("General Medicine",   9.0, 3, 0.34),
    ("Paediatrics",        8.0, 2, 0.17),
    ("Obstetrics & Gynae", 6.5, 2, 0.14),
    ("Orthopaedics",       7.5, 1, 0.11),
    ("Surgery",            6.0, 1, 0.09),
    ("Dermatology",       10.0, 1, 0.07),
    ("ENT",                9.5, 1, 0.05),
    ("Ophthalmology",      9.0, 1, 0.03),
]

# Arrivals across an Indian OPD day. The 8-11am crush is the defining feature:
# patients travel at dawn, arrive together, and wait for hours.
OPD_ARRIVAL_PROFILE = [
    ("07:00", 0.09), ("08:00", 0.21), ("09:00", 0.19), ("10:00", 0.14),
    ("11:00", 0.10), ("12:00", 0.07), ("13:00", 0.04), ("14:00", 0.05),
    ("15:00", 0.05), ("16:00", 0.04), ("17:00", 0.02),
]


# --------------------------------------------------------------------------
# 12. The pharmacy counter
# --------------------------------------------------------------------------
# Counselling is the part of dispensing that is free, evidence-based, and
# almost never done. Each line is what a pharmacist should actually say.
COUNSELLING = [
    ("Nitrofurantoin", "Take with food", "Harmless brown urine is expected. "
     "Complete the full course even once burning stops."),
    ("Fosfomycin", "Empty stomach, at bedtime", "Dissolve the sachet in half a "
     "glass of water. One dose only — do not repeat unless told to."),
    ("Cotrimoxazole", "With food, plenty of water", "Stop and return if a rash "
     "appears. Avoid in the last weeks of pregnancy."),
    ("Doxycycline", "With food, sitting upright", "Do not lie down for 30 "
     "minutes. Avoid milk, antacids and iron within 2 hours. Use sun protection."),
    ("Minocycline", "With food", "May cause dizziness. Avoid antacids within 2 hours."),
    ("Metronidazole", "With or after food", "No alcohol during the course or for "
     "48 hours after — the reaction is severe."),
    ("Amoxicillin", "With or without food", "Complete the course. Return if a "
     "rash or swelling appears."),
    ("Amoxicillin-Clavulanate", "With the first bite of a meal", "Taking it with "
     "food markedly reduces nausea and diarrhoea."),
    ("Ampicillin", "Empty stomach", "One hour before or two hours after food."),
    ("Clindamycin", "With a full glass of water", "Return urgently for severe or "
     "watery diarrhoea — this drug carries a real C. difficile risk."),
    ("Azithromycin", "With or without food", "Short course by design. Do not "
     "double the dose if one is missed."),
    ("Cefuroxime", "With food", "Absorption is much better with a meal."),
    ("Cefixime", "With or without food", "Complete the course."),
    ("Ciprofloxacin", "Empty stomach preferred", "Avoid milk, antacids, calcium "
     "and iron within 2 hours. Stop and return for tendon or heel pain."),
    ("Levofloxacin", "Empty stomach preferred", "Same 2-hour separation from "
     "antacids and calcium. Avoid strong sun. Report tendon pain."),
    ("Gentamicin", "Injection", "Blood levels and kidney function must be "
     "monitored. Report any hearing change or ringing immediately."),
    ("Amikacin", "Injection", "Levels and creatinine monitored. Report hearing "
     "change, ringing or unsteadiness at once."),
    ("Ceftriaxone", "Injection", "Do not mix with calcium-containing fluids."),
    ("Ceftazidime", "Injection", "Course completed as prescribed."),
    ("Cefepime", "Injection", "Report confusion or twitching, especially with "
     "reduced kidney function."),
    ("Cefoperazone-Sulbactam", "Injection", "Avoid alcohol during and shortly "
     "after the course."),
    ("Piperacillin-Tazobactam", "Injection", "Kidney function monitored, "
     "particularly if vancomycin is also running."),
    ("Ertapenem", "Injection", "Once daily. Complete the course."),
    ("Meropenem", "Injection", "Reserve agent. De-escalate as soon as the "
     "culture allows."),
    ("Imipenem-Cilastatin", "Injection", "Report any twitching or seizure "
     "activity, especially in kidney impairment."),
    ("Vancomycin", "Slow infusion", "Infuse over at least an hour — rapid "
     "infusion causes flushing. Trough levels and creatinine monitored."),
    ("Teicoplanin", "Injection", "Loading doses matter; do not skip them."),
    ("Linezolid", "With or without food", "Avoid aged cheese, tap beer and "
     "fermented foods. Tell the doctor about any antidepressant. Blood counts "
     "monitored beyond two weeks."),
    ("Tigecycline", "Infusion", "Nausea is common and usually settles."),
    ("Colistin", "Infusion", "Kidney function checked daily. Report reduced "
     "urine output."),
    ("Ceftazidime-Avibactam", "Infusion", "Last-line agent, reserved for "
     "confirmed resistant organisms."),
]

# Pregnancy and lactation safety — a question the counter is asked constantly
# and answers from memory.
PREGNANCY = [
    ("Nitrofurantoin", "Caution", "Avoid at term (38+ weeks) and in G6PD deficiency."),
    ("Fosfomycin", "Safe", "Widely used as a single dose in pregnancy."),
    ("Cotrimoxazole", "Avoid", "Folate antagonist in the first trimester; "
     "kernicterus risk at term."),
    ("Doxycycline", "Avoid", "Fetal teeth and bone. Contraindicated after week 15."),
    ("Minocycline", "Avoid", "Same tetracycline class effects."),
    ("Metronidazole", "Caution", "Generally acceptable after the first trimester."),
    ("Amoxicillin", "Safe", "One of the best-characterised agents in pregnancy."),
    ("Amoxicillin-Clavulanate", "Safe", "Widely used; watch neonatal NEC risk in PPROM."),
    ("Ampicillin", "Safe", "Long, reassuring record."),
    ("Clindamycin", "Safe", "Acceptable in all trimesters."),
    ("Azithromycin", "Safe", "Preferred macrolide in pregnancy."),
    ("Cefuroxime", "Safe", "Cephalosporins are broadly acceptable."),
    ("Cefixime", "Safe", "Acceptable."),
    ("Ciprofloxacin", "Avoid", "Fluoroquinolone cartilage concerns; use only if "
     "no alternative exists."),
    ("Levofloxacin", "Avoid", "Same class concern."),
    ("Gentamicin", "Caution", "Fetal ototoxicity risk; use only when clearly indicated."),
    ("Amikacin", "Caution", "Same aminoglycoside concern."),
    ("Ceftriaxone", "Safe", "Widely used."),
    ("Ceftazidime", "Safe", "Acceptable."),
    ("Cefepime", "Safe", "Acceptable."),
    ("Cefoperazone-Sulbactam", "Caution", "Limited data."),
    ("Piperacillin-Tazobactam", "Safe", "Acceptable."),
    ("Ertapenem", "Caution", "Limited human data."),
    ("Meropenem", "Caution", "Used when the indication is compelling."),
    ("Imipenem-Cilastatin", "Caution", "Limited data."),
    ("Vancomycin", "Caution", "Used where indicated; monitor levels."),
    ("Teicoplanin", "Caution", "Limited data."),
    ("Linezolid", "Caution", "Limited human data."),
    ("Tigecycline", "Avoid", "Tetracycline-class fetal effects."),
    ("Colistin", "Caution", "Reserved for resistant organisms with no alternative."),
    ("Ceftazidime-Avibactam", "Caution", "Very limited data."),
]

# What a district hospital pharmacy actually has on the shelf. Stock-outs of
# the cheap narrow agents are the quiet reason broad-spectrum drugs get used.
STOCK = [
    # drug, units in stock, monthly consumption, jan_aushadhi_stocked
    ("Nitrofurantoin", 840, 620, 1), ("Fosfomycin", 40, 95, 0),
    ("Cotrimoxazole", 1900, 700, 1), ("Doxycycline", 1450, 880, 1),
    ("Minocycline", 60, 40, 0), ("Metronidazole", 2400, 1500, 1),
    ("Amoxicillin", 2100, 1600, 1), ("Amoxicillin-Clavulanate", 1250, 1400, 1),
    ("Ampicillin", 600, 300, 1), ("Clindamycin", 220, 180, 0),
    ("Azithromycin", 1600, 1250, 1), ("Cefuroxime", 480, 400, 1),
    ("Cefixime", 1350, 1100, 1), ("Ciprofloxacin", 1750, 900, 1),
    ("Levofloxacin", 1100, 950, 1), ("Gentamicin", 400, 260, 1),
    ("Amikacin", 520, 430, 1), ("Ceftriaxone", 1650, 1500, 1),
    ("Ceftazidime", 260, 220, 0), ("Cefepime", 180, 210, 0),
    ("Cefoperazone-Sulbactam", 240, 300, 0),
    ("Piperacillin-Tazobactam", 310, 380, 0), ("Ertapenem", 45, 30, 0),
    ("Meropenem", 290, 260, 0), ("Imipenem-Cilastatin", 90, 70, 0),
    ("Vancomycin", 160, 140, 0), ("Teicoplanin", 55, 45, 0),
    ("Linezolid", 380, 300, 1), ("Tigecycline", 25, 20, 0),
    ("Colistin", 120, 110, 0), ("Ceftazidime-Avibactam", 8, 6, 0),
]

# Affordability reference points. Out-of-pocket spending is the mechanism by
# which illness becomes poverty in India, and medicines are its largest single
# component — so a rupee figure means nothing until it is set against a wage.
AFFORDABILITY = [
    ("MGNREGA rural daily wage", 261, "Statutory rural employment guarantee wage"),
    ("Rural informal daily wage", 350, "Typical agricultural / casual labour"),
    ("Urban informal daily wage", 480, "Construction, domestic and gig work"),
    ("Salaried urban (median)", 1150, "Formal-sector median daily equivalent"),
]

# Above this share of household daily income, a course is routinely abandoned
# part-way — which is worse than never starting it, because partial courses
# select for resistance.
ABANDONMENT_THRESHOLDS = [
    (0.0, 0.5, "Low", "Affordable within a day's earnings."),
    (0.5, 1.5, "Moderate", "Costs up to a day and a half of income. Counsel "
                           "explicitly on completing the course."),
    (1.5, 4.0, "High", "Several days of income. Substitute to the cheapest "
                       "equivalent and confirm the patient can actually buy it."),
    (4.0, 999.0, "Catastrophic", "Beyond a week of income. This prescription "
                                 "will very likely be abandoned part-way, which "
                                 "is worse than not starting it."),
]


def build_triage() -> None:
    _write("news2_bands.csv", [
        {"parameter": p, "low": lo, "high": hi, "points": pts}
        for p, lo, hi, pts in NEWS2_BANDS
    ])
    _write("news2_response.csv", [
        {"score_min": lo, "score_max": hi, "band": band,
         "response": resp, "minutes_to_review": mins}
        for lo, hi, band, resp, mins in NEWS2_RESPONSE
    ])
    total_share = sum(d[3] for d in DEPARTMENTS)
    assert abs(total_share - 1.0) < 1e-9, f"department shares sum to {total_share}"
    _write("departments.csv", [
        {"department": n, "per_doctor_per_hour": tp, "doctors": docs,
         "arrival_share": share}
        for n, tp, docs, share in DEPARTMENTS
    ])
    profile_total = sum(p[1] for p in OPD_ARRIVAL_PROFILE)
    assert abs(profile_total - 1.0) < 1e-9, f"arrival profile sums to {profile_total}"
    _write("opd_arrivals.csv", [
        {"hour": h, "share": s} for h, s in OPD_ARRIVAL_PROFILE
    ])


def build_pharmacy() -> None:
    formulary = {d[0] for d in DRUGS}
    for table, name in [(COUNSELLING, "counselling"), (PREGNANCY, "pregnancy"),
                        (STOCK, "stock")]:
        unknown = {row[0] for row in table} - formulary
        assert not unknown, f"{name} references unknown drugs: {unknown}"

    _write("counselling.csv", [
        {"antibiotic": d, "timing": t, "advice": a} for d, t, a in COUNSELLING
    ])
    _write("pregnancy.csv", [
        {"antibiotic": d, "category": c, "note": n} for d, c, n in PREGNANCY
    ])
    _write("stock.csv", [
        {"antibiotic": d, "units_in_stock": u, "monthly_consumption": m,
         "janaushadhi_stocked": ja}
        for d, u, m, ja in STOCK
    ])
    _write("affordability.csv", [
        {"reference": r, "daily_income_inr": w, "note": n}
        for r, w, n in AFFORDABILITY
    ])
    _write("abandonment_risk.csv", [
        {"days_of_income_min": lo, "days_of_income_max": hi,
         "risk": risk, "guidance": note}
        for lo, hi, risk, note in ABANDONMENT_THRESHOLDS
    ])


if __name__ == "__main__":
    print("Building Parchi data layer ->", DATA)
    build_priors()
    build_drugs()
    build_susceptibility()
    build_durations()
    build_risk_factors()
    build_fdc()
    build_interactions()
    build_renal()
    build_burden()
    build_triage()
    build_pharmacy()
    print("Done.")
