"""Cached loaders for the Parchi data layer.

Every CSV carries a leading `#` provenance line, so all reads skip comments.
"""

from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LATEST_YEAR = 2024


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
def dengue() -> pd.DataFrame:
    return _read("dengue_monthly.csv")


def infection_sites() -> list[str]:
    return sorted(priors()["site"].unique())


def antibiotic_names() -> list[str]:
    return sorted(drugs()["antibiotic"].unique())


def states() -> list[str]:
    return sorted(dengue()["state"].unique())


def drug_row(name: str) -> pd.Series:
    match = drugs()[drugs()["antibiotic"] == name]
    if match.empty:
        raise KeyError(f"Unknown antibiotic: {name}")
    return match.iloc[0]
