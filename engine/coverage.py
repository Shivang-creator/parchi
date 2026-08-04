"""Empiric antibiotic coverage.

The clinical question this answers: *before any culture result exists, what is
the probability that this antibiotic actually kills whatever is causing this
infection — in this ward, in this country, this year?*

Culture takes 48-72 hours and in most Indian outpatient settings is never sent
at all, so the first dose is always a bet. This module prices the bet.

    P(cover) = SUM over organisms  P(organism | site)  x  P(susceptible | organism, drug, setting, year)

Patient risk factors (prior antibiotics, devices, recent admission) discount
the susceptibility term, because those patients carry more resistant flora
than the surveillance average.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import data


@dataclass
class OrganismContribution:
    """One row of the 'why' table behind a coverage number."""

    organism: str
    prior: float
    percent_susceptible: float
    contribution: float          # prior x susceptibility, in probability units


@dataclass
class CoverageResult:
    antibiotic: str
    coverage: float                       # 0..1, risk-adjusted
    baseline_coverage: float              # 0..1, before risk adjustment
    spectrum: int
    who_aware: str
    route: str
    breakdown: list[OrganismContribution] = field(default_factory=list)
    risk_penalty: float = 1.0

    @property
    def coverage_pct(self) -> float:
        return round(self.coverage * 100, 1)

    @property
    def gap_pct(self) -> float:
        """Percentage-point coverage lost to this patient's risk factors."""
        return round((self.baseline_coverage - self.coverage) * 100, 1)


RISK_DECAY = 0.65

# Risk factors must not be counted twice. The ICU susceptibility figures were
# themselves measured on ICU patients — people who by definition have had
# recent antibiotics, devices and a prior admission. Applying the full
# outpatient risk penalty on top of already-ICU data punishes the same
# exposure twice and drives coverage to numbers no real unit sees. So the
# penalty is damped as the baseline setting already accounts for more of it.
SETTING_RISK_DAMPING = {"OPD": 1.00, "Ward": 0.60, "ICU": 0.35}


def risk_multiplier(selected_factors: list[str], setting: str = "OPD") -> float:
    """Combine risk-factor multipliers with diminishing returns.

    Risk factors overlap heavily — a ventilated ICU patient has almost by
    definition had recent antibiotics and a central line, so multiplying all
    three at full strength double-counts the same underlying exposure and
    drives coverage to implausible near-zero.

    Instead we sort strongest-first and apply the i-th factor with exponent
    RISK_DECAY**i. The first factor counts fully, the second about two-thirds,
    the third under half. A patient with six risk factors lands where they
    belong — 'high risk' — rather than at an arithmetic absurdity.
    """
    if not selected_factors:
        return 1.0

    table = data.risk_factors().set_index("factor")["susceptibility_multiplier"]
    multipliers = sorted(
        float(table.loc[f]) for f in selected_factors if f in table.index
    )

    penalty = 1.0
    for i, m in enumerate(multipliers):
        penalty *= m ** (RISK_DECAY**i)

    damping = SETTING_RISK_DAMPING.get(setting, 1.0)
    return float(1.0 - (1.0 - penalty) * damping)


def _susceptibility_lookup(setting: str, year: int) -> pd.Series:
    sus = data.susceptibility()
    frame = sus[(sus["setting"] == setting) & (sus["year"] == year)]
    return frame.set_index(["organism", "antibiotic"])["percent_susceptible"]


def _priors_for(site: str, setting: str) -> pd.DataFrame:
    frame = data.priors()
    return frame[(frame["site"] == site) & (frame["setting"] == setting)]


def score_antibiotic(
    antibiotic: str,
    site: str,
    setting: str,
    selected_factors: list[str] | None = None,
    year: int = data.LATEST_YEAR,
) -> CoverageResult:
    selected_factors = selected_factors or []
    penalty = risk_multiplier(selected_factors, setting)

    prior_rows = _priors_for(site, setting)
    lookup = _susceptibility_lookup(setting, year)
    meta = data.drug_row(antibiotic)

    breakdown: list[OrganismContribution] = []
    baseline = 0.0
    for _, row in prior_rows.iterrows():
        organism, prior = row["organism"], float(row["prior"])
        try:
            pct = float(lookup.loc[(organism, antibiotic)])
        except KeyError:
            # Drug has no meaningful activity against this organism.
            pct = 0.0
        contribution = prior * pct / 100.0
        baseline += contribution
        breakdown.append(
            OrganismContribution(
                organism=organism,
                prior=prior,
                percent_susceptible=pct,
                contribution=contribution,
            )
        )

    breakdown.sort(key=lambda c: c.contribution, reverse=True)

    return CoverageResult(
        antibiotic=antibiotic,
        coverage=baseline * penalty,
        baseline_coverage=baseline,
        spectrum=int(meta["spectrum"]),
        who_aware=str(meta["who_aware"]),
        route=str(meta["route"]),
        breakdown=breakdown,
        risk_penalty=penalty,
    )


def rank_antibiotics(
    site: str,
    setting: str,
    selected_factors: list[str] | None = None,
    year: int = data.LATEST_YEAR,
    route_filter: str | None = None,
) -> list[CoverageResult]:
    """All formulary drugs, best expected coverage first."""
    results = []
    for name in data.antibiotic_names():
        result = score_antibiotic(name, site, setting, selected_factors, year)
        if route_filter and route_filter not in result.route:
            continue
        results.append(result)
    results.sort(key=lambda r: r.coverage, reverse=True)
    return results


# How much empiric coverage is "good enough" depends on what happens if you
# are wrong. Being wrong about an outpatient cystitis means the patient comes
# back in three days; being wrong about ICU septic shock means they die. So the
# bar rises with the stakes.
#
# The 80% figure is not invented: IDSA guidance is that an agent should only be
# used empirically where local susceptibility exceeds ~80%. Applying that rule
# honestly to Indian surveillance data is itself the finding — for several
# common infections, no oral agent qualifies any more.
ADEQUACY_TARGET = {"OPD": 0.80, "Ward": 0.85, "ICU": 0.90}

# Below the bar but still a defensible empiric bet with 48-72h follow-up.
MARGINAL_FLOOR = 0.60


def adequacy_tier(coverage_value: float, setting: str) -> str:
    """ADEQUATE | MARGINAL | INADEQUATE — drives the colour of every alert."""
    bar = ADEQUACY_TARGET.get(setting, 0.85)
    if coverage_value >= bar:
        return "ADEQUATE"
    if coverage_value >= MARGINAL_FLOOR:
        return "MARGINAL"
    return "INADEQUATE"


@dataclass
class Recommendation:
    choice: CoverageResult
    rationale: str
    escalated: bool           # nothing narrow cleared the bar
    target: float
    runners_up: list[CoverageResult] = field(default_factory=list)


def stewardship_choice(
    ranked: list[CoverageResult],
    setting: str = "OPD",
    target: float | None = None,
    allow_reserve: bool = False,
) -> Recommendation | None:
    """The NARROWEST drug that still clears an absolute coverage bar.

    This is the whole point of stewardship, and it is the opposite of ranking
    by strength. Reaching for a carbapenem when nitrofurantoin covers the same
    patient is precisely how carbapenem resistance was manufactured. So we set
    an absolute adequacy bar for the setting, then pick the least aggressive
    drug that clears it — never the most powerful one.

    WHO AWaRe 'Reserve' agents (colistin, linezolid) are excluded from empiric
    first-line unless nothing else clears the bar, in which case we say so
    explicitly rather than silently recommending a last-line drug.
    """
    if not ranked:
        return None

    bar = target if target is not None else ADEQUACY_TARGET.get(setting, 0.85)
    candidates = [r for r in ranked if allow_reserve or r.who_aware != "Reserve"]
    if not candidates:
        candidates = list(ranked)

    adequate = [r for r in candidates if r.coverage >= bar]

    if adequate:
        # Narrowest first; among equals, best coverage.
        adequate.sort(key=lambda r: (r.spectrum, -r.coverage))
        pick = adequate[0]
        others = [r for r in adequate if r is not pick][:3]
        return Recommendation(
            choice=pick,
            rationale=(
                f"Narrowest agent clearing the {bar:.0%} empiric bar for a "
                f"{setting} patient. {len(adequate)} of {len(candidates)} "
                f"formulary options qualified; this is the least aggressive."
            ),
            escalated=False,
            target=bar,
            runners_up=others,
        )

    # Nothing clears the bar. Two very different situations live here.
    fallback = sorted(candidates, key=lambda r: -r.coverage)
    pick = fallback[0]
    tier = adequacy_tier(pick.coverage, setting)

    if tier == "MARGINAL":
        note = (
            f"No agent reaches the {bar:.0%} empiric standard. "
            f"{pick.antibiotic} is the narrowest reasonable bet at "
            f"{pick.coverage_pct}% — acceptable only with a culture sent now "
            f"and review in 48-72 hours."
        )
    else:
        note = (
            f"No formulary agent reaches even {MARGINAL_FLOOR:.0%} for this "
            f"patient; the best single drug is {pick.coverage_pct}%. Empiric "
            f"monotherapy is not adequate here — send cultures before the "
            f"first dose and use combination therapy."
        )

    with_reserve = sorted(ranked, key=lambda r: -r.coverage)
    if with_reserve and with_reserve[0].coverage > pick.coverage + 1e-9:
        note += (
            f" Highest coverage overall is {with_reserve[0].antibiotic} at "
            f"{with_reserve[0].coverage_pct}%, a WHO Reserve agent held back "
            f"from routine empiric use."
        )

    # Prefer the narrowest among drugs statistically tied with the best.
    tied = [r for r in fallback if r.coverage >= pick.coverage - 0.02]
    tied.sort(key=lambda r: (r.spectrum, -r.coverage))
    pick = tied[0]

    return Recommendation(
        choice=pick,
        rationale=note,
        escalated=True,
        target=bar,
        runners_up=[r for r in fallback if r is not pick][:3],
    )


# --------------------------------------------------------------------------
# Combination therapy
# --------------------------------------------------------------------------
def score_combination(
    antibiotics: list[str],
    site: str,
    setting: str,
    selected_factors: list[str] | None = None,
    year: int = data.LATEST_YEAR,
) -> CoverageResult:
    """Expected coverage of two or more agents given together.

    The naive move is 1 - prod(1 - p_i), which treats the agents as
    independent. They are not: two carbapenems fail on the *same* carbapenemase-
    producing isolate, so their failures are almost perfectly correlated.

    The correct decomposition works organism by organism. For each possible
    organism, the combination covers it if ANY agent covers it, so we take the
    maximum susceptibility across agents, then weight by how likely that
    organism is:

        P(cover) = SUM_organism  P(organism) x MAX_drug P(susceptible)

    This is why meropenem + colistin is worth so much more than meropenem +
    imipenem in an Indian ICU — colistin covers the carbapenem-resistant
    gram-negatives that a second carbapenem cannot.
    """
    selected_factors = selected_factors or []
    penalty = risk_multiplier(selected_factors, setting)

    prior_rows = _priors_for(site, setting)
    lookup = _susceptibility_lookup(setting, year)

    breakdown: list[OrganismContribution] = []
    baseline = 0.0
    for _, row in prior_rows.iterrows():
        organism, prior = row["organism"], float(row["prior"])
        best_pct = 0.0
        for drug in antibiotics:
            try:
                best_pct = max(best_pct, float(lookup.loc[(organism, drug)]))
            except KeyError:
                continue
        contribution = prior * best_pct / 100.0
        baseline += contribution
        breakdown.append(
            OrganismContribution(organism, prior, best_pct, contribution)
        )

    breakdown.sort(key=lambda c: c.contribution, reverse=True)
    widest = max((int(data.drug_row(a)["spectrum"]) for a in antibiotics), default=0)

    return CoverageResult(
        antibiotic=" + ".join(antibiotics),
        coverage=baseline * penalty,
        baseline_coverage=baseline,
        spectrum=widest,
        who_aware=", ".join(sorted({str(data.drug_row(a)["who_aware"]) for a in antibiotics})),
        route="/".join(sorted({str(data.drug_row(a)["route"]) for a in antibiotics})),
        breakdown=breakdown,
        risk_penalty=penalty,
    )


def best_combination(
    site: str,
    setting: str,
    selected_factors: list[str] | None = None,
    anchor: str | None = None,
    year: int = data.LATEST_YEAR,
) -> tuple[CoverageResult, CoverageResult]:
    """Best two-drug pairing, and the best single agent it improves on.

    Searching all pairs of an 18-drug formulary is 153 combinations — trivially
    cheap, and it surfaces the non-obvious partner rather than the habitual one.
    """
    names = data.antibiotic_names()
    singles = rank_antibiotics(site, setting, selected_factors, year)
    best_single = singles[0]

    candidates = [anchor] if anchor else names
    best_pair, best_score = None, -1.0
    for a in candidates:
        for b in names:
            if a == b:
                continue
            result = score_combination([a, b], site, setting, selected_factors, year)
            # Tie-break toward the narrower pairing.
            if result.coverage > best_score + 1e-9:
                best_pair, best_score = result, result.coverage
    return best_pair, best_single


# --------------------------------------------------------------------------
# Resistance trajectory
# --------------------------------------------------------------------------
def coverage_trend(
    antibiotic: str,
    site: str,
    setting: str,
    selected_factors: list[str] | None = None,
) -> pd.DataFrame:  # noqa: D401
    """Coverage for this drug/site/setting across every surveillance year."""
    years = sorted(data.susceptibility()["year"].unique())
    rows = []
    for year in years:
        result = score_antibiotic(antibiotic, site, setting, selected_factors, int(year))
        rows.append({"year": int(year), "coverage": result.coverage * 100})
    return pd.DataFrame(rows)


def project_expiry(
    trend: pd.DataFrame,
    threshold: float = 50.0,
    horizon: int = 12,
) -> tuple[pd.DataFrame, int | None]:
    """Extrapolate the coverage trend and find when it crosses `threshold`.

    A least-squares line through the observed years, projected forward. This is
    deliberately the simplest defensible model: the clinically useful signal is
    the direction and the crossing year, and a linear fit on 7 points does not
    earn anything fancier.

    Returns (projection frame, first year below threshold or None).
    """
    x = trend["year"].to_numpy(dtype=float)
    y = trend["coverage"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    future_years = np.arange(x.max() + 1, x.max() + 1 + horizon)
    projected = np.clip(slope * future_years + intercept, 0, 100)

    frame = pd.DataFrame({"year": future_years.astype(int), "coverage": projected})

    # Already below the bar today? Then the crossing happened in the past —
    # report the first observed year under threshold, not a future projection.
    if y[-1] < threshold:
        already = trend[trend["coverage"] < threshold]
        return frame, int(already.iloc[0]["year"]) if not already.empty else int(x[-1])

    if slope < 0:
        below = frame[frame["coverage"] < threshold]
        if not below.empty:
            return frame, int(below.iloc[0]["year"])

    return frame, None
