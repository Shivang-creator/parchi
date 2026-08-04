"""Seasonal surge forecasting — and what a surge actually costs a hospital.

Indian disease load is violently seasonal. Dengue is the sharpest case: roughly
three-fifths of a state's annual caseload lands in September, October and
November, and the curve repeats every year. Yet hospitals still meet it
unprepared — because nobody converts an epidemiological curve into the two
numbers an administrator can act on: *how many extra people walk into OPD*, and
*how many platelet units do we need on the shelf*.

Method: multiplicative seasonal decomposition.

    forecast(state, month) = projected_annual_total(state, year)
                             x seasonal_index(state, month)

The seasonal index is the average share of the annual total falling in each
month, learned per state. The annual level is a least-squares trend over
observed years. Both parts are visible to the user — no black box.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import data

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


@dataclass
class SurgeAssumptions:
    """Every conversion factor, exposed rather than buried.

    Defaults sit in the ranges reported for dengue admissions and transfusion
    practice; a hospital plugs in its own audit numbers and the whole forecast
    re-bases.
    """

    febrile_opd_per_case: float = 8.0      # OPD screens per confirmed case
    admission_rate: float = 0.10           # confirmed cases needing admission
    mean_stay_days: float = 4.5
    platelet_transfusion_rate: float = 0.32  # of admissions
    units_per_transfused_patient: float = 4.0


def state_series(state: str) -> pd.DataFrame:
    """Monthly case counts for one state, chronologically ordered."""
    frame = data.dengue()
    frame = frame[frame["state"] == state].copy()
    frame = frame.sort_values(["year", "month"]).reset_index(drop=True)
    frame["period"] = pd.to_datetime(
        frame["year"].astype(str) + "-" + frame["month"].astype(str).str.zfill(2) + "-01"
    )
    return frame


def seasonal_index(state: str) -> pd.Series:
    """Average share of the annual caseload falling in each month."""
    frame = state_series(state)
    annual = frame.groupby("year")["cases"].transform("sum")
    frame = frame.assign(share=frame["cases"] / annual.replace(0, np.nan))
    index = frame.groupby("month")["share"].mean()
    return index / index.sum()


def annual_trend(state: str, horizon_years: int = 2) -> tuple[pd.DataFrame, float]:
    """Least-squares trend through annual totals, projected forward."""
    frame = state_series(state)
    annual = frame.groupby("year")["cases"].sum().reset_index()

    x = annual["year"].to_numpy(dtype=float)
    y = annual["cases"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    future = np.arange(x.max() + 1, x.max() + 1 + horizon_years)
    projected = np.clip(slope * future + intercept, 0, None)

    annual["kind"] = "observed"
    forward = pd.DataFrame({"year": future.astype(int), "cases": projected, "kind": "projected"})
    return pd.concat([annual, forward], ignore_index=True), float(slope)


def forecast_months(state: str, months_ahead: int = 12) -> pd.DataFrame:
    """Monthly forecast with an empirical uncertainty band.

    The band comes from how far the seasonal model missed on the years we do
    have — a residual quantile, not a distributional assumption.
    """
    frame = state_series(state)
    index = seasonal_index(state)
    annual, _ = annual_trend(state, horizon_years=(months_ahead // 12) + 2)
    annual_lookup = annual.set_index("year")["cases"]

    # In-sample residuals: how well does annual_total x seasonal_index fit?
    fitted = []
    for _, row in frame.iterrows():
        total = float(annual_lookup.get(int(row["year"]), np.nan))
        fitted.append(total * float(index.loc[int(row["month"])]))
    frame["fitted"] = fitted
    residual_ratio = (frame["cases"] / frame["fitted"].replace(0, np.nan)).dropna()
    lo_ratio = float(residual_ratio.quantile(0.10))
    hi_ratio = float(residual_ratio.quantile(0.90))

    last = frame.iloc[-1]
    year, month = int(last["year"]), int(last["month"])

    rows = []
    for _ in range(months_ahead):
        month += 1
        if month > 12:
            month, year = 1, year + 1
        total = float(annual_lookup.get(year, annual_lookup.iloc[-1]))
        point = total * float(index.loc[month])
        rows.append(
            {
                "year": year,
                "month": month,
                "label": f"{MONTH_NAMES[month - 1]} {year}",
                "cases": point,
                "lower": point * lo_ratio,
                "upper": point * hi_ratio,
            }
        )
    return pd.DataFrame(rows)


@dataclass
class SurgeDemand:
    label: str
    cases: float
    opd_screens: float
    admissions: float
    bed_days: float
    platelet_units: float


def demand_from_cases(
    forecast: pd.DataFrame,
    assumptions: SurgeAssumptions | None = None,
) -> pd.DataFrame:
    """Convert a case forecast into staffing, bed and platelet requirements."""
    a = assumptions or SurgeAssumptions()
    out = forecast.copy()
    out["opd_screens"] = out["cases"] * a.febrile_opd_per_case
    out["admissions"] = out["cases"] * a.admission_rate
    out["bed_days"] = out["admissions"] * a.mean_stay_days
    out["platelet_units"] = (
        out["admissions"] * a.platelet_transfusion_rate * a.units_per_transfused_patient
    )
    return out


def peak_row(forecast: pd.DataFrame) -> pd.Series:
    return forecast.loc[forecast["cases"].idxmax()]


def surge_ratio(forecast: pd.DataFrame) -> float:
    """Peak month divided by the quietest month — the preparedness gap."""
    lo = float(forecast["cases"].min())
    if lo <= 0:
        return float("inf")
    return round(float(forecast["cases"].max()) / lo, 1)


def national_peak_calendar() -> pd.DataFrame:
    """Which month each state peaks in — the roster-planning view."""
    rows = []
    for state in data.states():
        index = seasonal_index(state)
        peak_month = int(index.idxmax())
        rows.append(
            {
                "state": state,
                "peak_month": peak_month,
                "peak_month_name": MONTH_NAMES[peak_month - 1],
                "peak_share": round(float(index.max()) * 100, 1),
                "annual_cases_latest": int(
                    state_series(state).query("year == year.max()")["cases"].sum()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("annual_cases_latest", ascending=False)
