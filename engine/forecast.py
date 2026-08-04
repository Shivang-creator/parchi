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

    Defaults come from the per-disease load table; a hospital plugs in its own
    audit numbers and the whole forecast re-bases. The differences between
    diseases are the point — malaria fills beds but rarely needs platelets,
    dengue does both.
    """

    febrile_opd_per_case: float = 8.0      # OPD screens per confirmed case
    admission_rate: float = 0.10           # confirmed cases needing admission
    mean_stay_days: float = 4.5
    platelet_transfusion_rate: float = 0.32  # of admissions
    units_per_transfused_patient: float = 4.0

    @classmethod
    def for_disease(cls, disease: str) -> "SurgeAssumptions":
        table = data.disease_load()
        row = table[table["disease"] == disease]
        if row.empty:
            return cls()
        r = row.iloc[0]
        return cls(
            febrile_opd_per_case=float(r["opd_per_case"]),
            admission_rate=float(r["admission_rate"]),
            mean_stay_days=float(r["mean_stay_days"]),
            platelet_transfusion_rate=float(r["transfusion_rate"]),
            units_per_transfused_patient=float(r["units_per_transfusion"]),
        )


def state_series(state: str, disease: str = "Dengue") -> pd.DataFrame:
    """Monthly case counts for one state and disease, chronologically ordered."""
    frame = data.burden()
    frame = frame[(frame["state"] == state) & (frame["disease"] == disease)].copy()
    frame = frame.sort_values(["year", "month"]).reset_index(drop=True)
    frame["period"] = pd.to_datetime(
        frame["year"].astype(str) + "-" + frame["month"].astype(str).str.zfill(2) + "-01"
    )
    return frame


def seasonal_index(state: str, disease: str = "Dengue") -> pd.Series:
    """Average share of the annual caseload falling in each month."""
    frame = state_series(state, disease)
    annual = frame.groupby("year")["cases"].transform("sum")
    frame = frame.assign(share=frame["cases"] / annual.replace(0, np.nan))
    index = frame.groupby("month")["share"].mean()
    return index / index.sum()


# Extrapolating an epidemic trend is unreliable the further out you go, so the
# fitted slope is damped rather than taken at face value. This pulls long
# projections toward the current level instead of toward a confident fantasy.
TREND_DAMPING = 0.7


def annual_trend(
    state: str, disease: str = "Dengue", horizon_years: int = 2
) -> tuple[pd.DataFrame, float]:
    """Trend through annual totals, projected forward on a log scale.

    A straight line in case-space is the wrong model and it fails loudly:
    malaria has declined so steeply in India that a linear fit extrapolates
    below zero within a year, and clipping at zero turns the whole forecast
    into zeros. Case counts are non-negative and move multiplicatively, so the
    fit belongs in log space — where a declining series decays toward zero
    asymptotically instead of crashing through it.

    Falls back to a linear fit only if a year genuinely reported no cases.
    """
    frame = state_series(state, disease)
    annual = frame.groupby("year")["cases"].sum().reset_index()

    x = annual["year"].to_numpy(dtype=float)
    y = annual["cases"].to_numpy(dtype=float)
    future = np.arange(x.max() + 1, x.max() + 1 + horizon_years)

    if (y > 0).all():
        log_slope, log_intercept = np.polyfit(x, np.log(y), 1)
        damped = log_slope * TREND_DAMPING
        anchor = np.log(y[-1])
        projected = np.exp(anchor + damped * (future - x.max()))
        slope = float(np.exp(log_slope) - 1.0)      # fractional change per year
    else:
        lin_slope, lin_intercept = np.polyfit(x, y, 1)
        projected = np.clip(
            y[-1] + lin_slope * TREND_DAMPING * (future - x.max()), 0, None
        )
        slope = float(lin_slope)

    # Never project a collapse to literally nothing — surveillance floors out.
    projected = np.maximum(projected, max(y.min() * 0.25, 1.0))

    annual["kind"] = "observed"
    forward = pd.DataFrame(
        {"year": future.astype(int), "cases": projected, "kind": "projected"}
    )
    return pd.concat([annual, forward], ignore_index=True), slope


def forecast_months(state: str, disease: str = "Dengue", months_ahead: int = 12) -> pd.DataFrame:
    """Monthly forecast with an empirical uncertainty band.

    The band comes from how far the seasonal model missed on the years we do
    have — a residual quantile, not a distributional assumption.
    """
    frame = state_series(state, disease)
    index = seasonal_index(state, disease)
    annual, _ = annual_trend(state, disease, horizon_years=(months_ahead // 12) + 2)
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


def backtest(
    state: str, disease: str = "Dengue", holdout_months: int = 12
) -> dict:
    """Hold out the last year, forecast it blind, and score the result.

    A forecast that has never been scored is an opinion. This refits the whole
    pipeline — seasonal index and annual trend — on data up to a cutoff, then
    predicts the months it was never shown.

    Reported as MAPE and as a naive-baseline comparison, because MAPE alone
    is not interpretable: the honest question is whether the model beats
    "assume this month looks like the same month last year", which for a
    strongly seasonal disease is already a decent forecast.
    """
    frame = state_series(state, disease)
    if len(frame) <= holdout_months + 24:
        return {}

    train = frame.iloc[:-holdout_months].copy()
    test = frame.iloc[-holdout_months:].copy()

    # Seasonal index from the training window only.
    annual_train = train.groupby("year")["cases"].transform("sum")
    shares = train.assign(share=train["cases"] / annual_train.replace(0, np.nan))
    index = shares.groupby("month")["share"].mean()
    index = index / index.sum()

    # Annual level, fitted the same way the live model fits it.
    totals = train.groupby("year")["cases"].sum()
    complete = totals.iloc[:-1] if len(totals) > 3 else totals
    x = complete.index.to_numpy(dtype=float)
    y = complete.to_numpy(dtype=float)
    if (y > 0).all() and len(y) > 2:
        log_slope, _ = np.polyfit(x, np.log(y), 1)
        level = float(y[-1]) * float(np.exp(log_slope * TREND_DAMPING))
    else:
        level = float(y[-1])

    predicted = np.array([level * float(index.loc[int(m)]) for m in test["month"]])
    actual = test["cases"].to_numpy(dtype=float)

    # Naive seasonal baseline: the same month, one year earlier.
    naive = frame.iloc[-holdout_months - 12:-12]["cases"].to_numpy(dtype=float)

    def mape(pred: np.ndarray) -> float:
        mask = actual > 0
        if not mask.any():
            return float("nan")
        return float(np.mean(np.abs(pred[mask] - actual[mask]) / actual[mask]) * 100)

    model_mape, naive_mape = mape(predicted), mape(naive)
    return {
        "months": holdout_months,
        "model_mape": model_mape,
        "naive_mape": naive_mape,
        "beats_naive": model_mape < naive_mape,
        "improvement": naive_mape - model_mape,
        "peak_month_correct": (
            int(test.iloc[int(np.argmax(predicted))]["month"])
            == int(test.iloc[int(np.argmax(actual))]["month"])
        ),
        "labels": [f"{MONTH_NAMES[int(m) - 1]} {int(y)}"
                   for m, y in zip(test["month"], test["year"])],
        "actual": actual,
        "predicted": predicted,
    }


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


def national_peak_calendar(disease: str = "Dengue") -> pd.DataFrame:
    """Which month each state peaks in — the roster-planning view."""
    rows = []
    for state in data.states(disease):
        index = seasonal_index(state, disease)
        peak_month = int(index.idxmax())
        series = state_series(state, disease)
        rows.append(
            {
                "state": state,
                "peak_month": peak_month,
                "peak_month_name": MONTH_NAMES[peak_month - 1],
                "peak_share": round(float(index.max()) * 100, 1),
                "annual_cases_latest": int(
                    series[series["year"] == series["year"].max()]["cases"].sum()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("annual_cases_latest", ascending=False)


def combined_load(state: str, months_ahead: int = 12) -> pd.DataFrame:
    """Total hospital load across every disease this state reports.

    A hospital does not experience one outbreak at a time. Malaria and dengue
    peak weeks apart, and the bed pressure they create adds up.
    """
    total = None
    for disease in data.diseases():
        if state not in data.states(disease):
            continue
        fc = forecast_months(state, disease, months_ahead)
        dem = demand_from_cases(fc, SurgeAssumptions.for_disease(disease))
        keep = dem[["label", "cases", "opd_screens", "admissions",
                    "bed_days", "platelet_units"]].copy()
        keep = keep.rename(columns={"cases": disease.lower() + "_cases"})
        if total is None:
            total = keep
        else:
            for col in ["opd_screens", "admissions", "bed_days", "platelet_units"]:
                total[col] = total[col] + keep[col]
            total[disease.lower() + "_cases"] = keep[disease.lower() + "_cases"]
    return total if total is not None else pd.DataFrame()
