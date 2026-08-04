"""Cached loaders for the Parchi data layer.

Every CSV carries a leading `#` provenance line, so all reads skip comments.
A single module owns disk access; nothing else in the codebase opens a file.
"""

from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LATEST_YEAR = 2024
SETTINGS = ["OPD", "Ward", "ICU"]


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, comment="#")


@functools.lru_cache(maxsize=None)
def priors() -> pd.DataFrame:
    return _read("infection_priors.csv")


@functools.lru_cache(maxsize=None)
def drugs() -> pd.DataFrame:
    return _read("drugs.csv")


@functools.lru_cache(maxsize=None)
def susceptibility() -> pd.DataFrame:
    return _read("amr_susceptibility.csv")


@functools.lru_cache(maxsize=None)
def durations() -> pd.DataFrame:
    return _read("durations.csv")


@functools.lru_cache(maxsize=None)
def risk_factors() -> pd.DataFrame:
    return _read("risk_factors.csv")


@functools.lru_cache(maxsize=None)
def fdc_flags() -> pd.DataFrame:
    return _read("fdc_flags.csv")


@functools.lru_cache(maxsize=None)
def interactions() -> pd.DataFrame:
    return _read("interactions.csv")


@functools.lru_cache(maxsize=None)
def renal_rules() -> pd.DataFrame:
    return _read("renal_rules.csv")


@functools.lru_cache(maxsize=None)
def burden() -> pd.DataFrame:
    return _read("vector_burden.csv")


@functools.lru_cache(maxsize=None)
def disease_load() -> pd.DataFrame:
    return _read("disease_load.csv")


@functools.lru_cache(maxsize=None)
def news2_bands() -> pd.DataFrame:
    return _read("news2_bands.csv")


@functools.lru_cache(maxsize=None)
def news2_response() -> pd.DataFrame:
    return _read("news2_response.csv")


@functools.lru_cache(maxsize=None)
def departments() -> pd.DataFrame:
    return _read("departments.csv")


@functools.lru_cache(maxsize=None)
def opd_arrivals() -> pd.DataFrame:
    return _read("opd_arrivals.csv")


@functools.lru_cache(maxsize=None)
def counselling() -> pd.DataFrame:
    return _read("counselling.csv")


@functools.lru_cache(maxsize=None)
def pregnancy() -> pd.DataFrame:
    return _read("pregnancy.csv")


@functools.lru_cache(maxsize=None)
def stock() -> pd.DataFrame:
    return _read("stock.csv")


@functools.lru_cache(maxsize=None)
def affordability() -> pd.DataFrame:
    return _read("affordability.csv")


@functools.lru_cache(maxsize=None)
def abandonment_risk() -> pd.DataFrame:
    return _read("abandonment_risk.csv")


# --------------------------------------------------------------------------
# convenience accessors
# --------------------------------------------------------------------------
def infection_sites() -> list[str]:
    return sorted(priors()["site"].unique())


def antibiotic_names() -> list[str]:
    return sorted(drugs()["antibiotic"].unique())


def organisms() -> list[str]:
    return sorted(susceptibility()["organism"].unique())


def diseases() -> list[str]:
    return sorted(burden()["disease"].unique())


def states(disease: str | None = None) -> list[str]:
    frame = burden()
    if disease:
        frame = frame[frame["disease"] == disease]
    return sorted(frame["state"].unique())


def settings_for(site: str) -> list[str]:
    """Which care settings this infection can actually present in.

    A ventilator-associated pneumonia has no outpatient form. Offering OPD in
    that dropdown would invite a nonsense query and return a nonsense answer.
    """
    frame = priors()
    present = set(frame[frame["site"] == site]["setting"])
    return [s for s in SETTINGS if s in present]


def drug_row(name: str) -> pd.Series:
    match = drugs()[drugs()["antibiotic"] == name]
    if match.empty:
        raise KeyError(f"Unknown antibiotic: {name}")
    return match.iloc[0]


def duration_for(site: str) -> pd.Series | None:
    match = durations()[durations()["site"] == site]
    return None if match.empty else match.iloc[0]


def organisms_for(site: str, setting: str) -> pd.DataFrame:
    frame = priors()
    return frame[(frame["site"] == site) & (frame["setting"] == setting)]


# --------------------------------------------------------------------------
# custom antibiogram override
# --------------------------------------------------------------------------
# A hospital's own antibiogram beats national surveillance every time. When one
# is loaded it replaces the national panel wholesale, and every engine
# downstream picks it up without changing a line.
_OVERRIDE: pd.DataFrame | None = None

# Engines memoise derived matrices off the susceptibility table. Swapping the
# table underneath them without clearing those caches would silently keep
# serving national numbers while the UI claimed the hospital's own were live.
_CACHE_CLEARERS: list = []


def register_cache(clear_fn) -> None:
    _CACHE_CLEARERS.append(clear_fn)


def _invalidate() -> None:
    susceptibility.cache_clear()
    for clear_fn in _CACHE_CLEARERS:
        clear_fn()


def load_antibiogram(frame: pd.DataFrame) -> tuple[bool, str]:
    """Install a user-supplied susceptibility table.

    Expects columns: organism, antibiotic, setting, year, percent_susceptible.
    Returns (ok, message) rather than raising — this is driven from a file
    upload widget where a bad file is expected, not exceptional.
    """
    global _OVERRIDE
    required = {"organism", "antibiotic", "setting", "year", "percent_susceptible"}
    missing = required - set(frame.columns)
    if missing:
        return False, f"Missing required column(s): {', '.join(sorted(missing))}"

    frame = frame.copy()
    frame["percent_susceptible"] = pd.to_numeric(
        frame["percent_susceptible"], errors="coerce"
    )
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame = frame.dropna(subset=["percent_susceptible", "year"])
    if frame.empty:
        return False, "No usable rows after parsing."

    known_drugs = set(antibiotic_names())
    unknown = sorted(set(frame["antibiotic"]) - known_drugs)
    frame = frame[frame["antibiotic"].isin(known_drugs)]
    if frame.empty:
        return False, "None of the antibiotics in that file are in the formulary."

    _OVERRIDE = frame
    _invalidate()
    note = f"Loaded {len(frame):,} rows covering {frame['organism'].nunique()} organisms."
    if unknown:
        note += f" Ignored {len(unknown)} unrecognised agent(s): {', '.join(unknown[:5])}."
    return True, note


def clear_antibiogram() -> None:
    global _OVERRIDE
    _OVERRIDE = None
    _invalidate()


def using_custom_antibiogram() -> bool:
    return _OVERRIDE is not None


def _susceptibility_source() -> pd.DataFrame:
    return _OVERRIDE if _OVERRIDE is not None else _read("amr_susceptibility.csv")


# Rebind the cached loader so the override is honoured everywhere.
susceptibility = functools.lru_cache(maxsize=None)(_susceptibility_source)
