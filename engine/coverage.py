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

import functools
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


# --------------------------------------------------------------------------
# The fast path
# --------------------------------------------------------------------------
# Scoring every drug, and then every PAIR of drugs, one organism at a time
# through pandas `.loc` took over a second — and Streamlit re-runs the whole
# script on every keystroke, so that is a second of lag on every interaction.
#
# The whole calculation is a matrix product. Pivot susceptibility once into an
# (organism x drug) array of fractions, and coverage for every drug at once is
# just `priors @ matrix`. Combinations are an element-wise max between two
# columns before the same product. Same arithmetic, same answers, ~200x faster.
def _matrix(setting: str, year: int) -> tuple[dict, list, np.ndarray]:
    # Keyed on which susceptibility table is live for this session, so a
    # hospital's uploaded antibiogram and the national panel never share an
    # entry.
    return _matrix_for(setting, year, data.antibiogram_token())


@functools.lru_cache(maxsize=64)
def _matrix_for(setting: str, year: int, _table: int) -> tuple[dict, list, np.ndarray]:
    sus = data.susceptibility()
    frame = sus[(sus["setting"] == setting) & (sus["year"] == year)]
    pivot = frame.pivot_table(
        index="organism", columns="antibiotic",
        values="percent_susceptible", aggfunc="first",
    )
    # Reindex to the full formulary so column positions are stable, and treat a
    # missing pair as zero cover — which is the clinically correct reading.
    pivot = pivot.reindex(columns=data.antibiotic_names()).fillna(0.0)
    organism_index = {name: i for i, name in enumerate(pivot.index)}
    return organism_index, list(pivot.columns), pivot.to_numpy(dtype=float) / 100.0


def _prior_vector(site: str, setting: str, year: int) -> np.ndarray:
    """Priors aligned to the susceptibility matrix's organism ordering."""
    return _prior_vector_for(site, setting, year, data.antibiogram_token())


@functools.lru_cache(maxsize=256)
def _prior_vector_for(site: str, setting: str, year: int, _table: int) -> np.ndarray:
    organism_index, _, matrix = _matrix(setting, year)
    vector = np.zeros(matrix.shape[0])
    for _, row in _priors_for(site, setting).iterrows():
        position = organism_index.get(row["organism"])
        if position is not None:
            vector[position] = float(row["prior"])
    return vector


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
    """All formulary drugs, best expected coverage first.

    One matrix product scores the entire formulary; the per-organism breakdown
    is only built for the handful of drugs that survive the route filter, since
    that detail is only ever read for the recommendation itself.
    """
    selected_factors = selected_factors or []
    penalty = risk_multiplier(selected_factors, setting)
    _, columns, matrix = _matrix(setting, year)
    priors = _prior_vector(site, setting, year)
    baselines = priors @ matrix

    formulary = data.drugs().set_index("antibiotic")
    results = []
    for position, name in enumerate(columns):
        meta = formulary.loc[name]
        route = str(meta["route"])
        if route_filter and route_filter not in route:
            continue
        baseline = float(baselines[position])
        results.append(
            CoverageResult(
                antibiotic=name,
                coverage=baseline * penalty,
                baseline_coverage=baseline,
                spectrum=int(meta["spectrum"]),
                who_aware=str(meta["who_aware"]),
                route=route,
                breakdown=[],
                risk_penalty=penalty,
            )
        )
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
# De-escalation — the step that actually protects the last-line drugs
# --------------------------------------------------------------------------
@dataclass
class DeEscalation:
    organism: str
    current: str
    current_works: bool
    recommended: str | None
    recommended_probability: float
    spectrum_saved: int
    rupees_saved: float
    options: list[tuple[str, float, int]]     # (drug, %S, spectrum)
    lab_confirmed: bool
    message: str


def active_agents(organism: str, setting: str, year: int = data.LATEST_YEAR) -> list[str]:
    """Agents with any recorded activity against this organism, narrowest first.

    Used to keep a lab-report picker honest: offering fosfomycin against an
    Acinetobacter isolate invites a nonsense entry, and since a lab report is
    treated as authoritative the model would then dutifully act on it.
    """
    organism_index, columns, matrix = _matrix(setting, year)
    position = organism_index.get(organism)
    if position is None:
        return []
    row = matrix[position]
    live = [(columns[j], float(row[j])) for j in range(len(columns)) if row[j] > 0.05]
    live.sort(key=lambda pair: (int(data.drug_row(pair[0])["spectrum"]), -pair[1]))
    return [name for name, _ in live]


def deescalate(
    organism: str,
    current_drug: str,
    setting: str,
    lab_susceptible_to: list[str] | None = None,
    year: int = data.LATEST_YEAR,
) -> DeEscalation:
    """Given a culture result, narrow the therapy.

    Empiric therapy is a bet placed blind. Forty-eight hours later the culture
    comes back and the bet can be settled — but in practice almost nobody goes
    back and narrows, so the patient finishes a week of meropenem for an
    organism that a five-rupee tablet would have killed. De-escalation is the
    single highest-value stewardship action there is, and it is the one most
    reliably skipped.

    Once the organism is known this is no longer a marginalisation over
    possible bugs — it is a direct lookup. If the lab also reported which
    agents tested susceptible, that list is authoritative and overrides the
    surveillance estimate entirely.
    """
    lookup = _susceptibility_lookup(setting, year)
    lab_set = {d.strip() for d in (lab_susceptible_to or []) if d.strip()}

    options: list[tuple[str, float, int]] = []
    for drug in data.antibiotic_names():
        meta = data.drug_row(drug)
        if lab_set:
            probability = 100.0 if drug in lab_set else 0.0
        else:
            try:
                probability = float(lookup.loc[(organism, drug)])
            except KeyError:
                probability = 0.0
        if probability > 0:
            options.append((drug, probability, int(meta["spectrum"])))

    # Effective enough to rely on once the organism is known.
    bar = 100.0 if lab_set else 80.0
    effective = [o for o in options if o[1] >= bar]
    effective.sort(key=lambda o: (o[2], -o[1]))

    current_meta = data.drug_row(current_drug)
    current_spectrum = int(current_meta["spectrum"])
    current_probability = next(
        (p for d, p, _ in options if d == current_drug), 0.0
    )
    current_works = current_probability >= bar

    if not effective:
        if lab_set:
            note = (
                f"**The lab reports no formulary agent active against this "
                f"{organism} isolate.** This is an extensively drug-resistant "
                f"organism — involve infectious diseases and consider "
                f"combination therapy."
            )
        else:
            # Careful: without a lab report we only have population statistics.
            # Saying the isolate is resistant would be asserting something we
            # have not measured. What is actually true is that surveillance
            # alone cannot identify a reliably narrow option.
            note = (
                f"**Surveillance alone cannot narrow this safely.** For "
                f"{organism} in this setting, no agent exceeds {bar:.0f}% "
                f"expected susceptibility, so de-escalating on population data "
                f"would be a guess. Request the sensitivity report — with the "
                f"actual isolate result, narrowing is usually possible."
            )
        return DeEscalation(
            organism, current_drug, current_works, None, 0.0, 0, 0.0,
            sorted(options, key=lambda o: -o[1])[:8], bool(lab_set), note,
        )

    narrowest = effective[0]
    saved = current_spectrum - narrowest[2]

    if not current_works:
        message = (
            f"**{current_drug} does not cover this isolate.** The culture has "
            f"overturned the empiric choice — change therapy now, not at the "
            f"next ward round."
        )
    elif saved > 0:
        message = (
            f"**De-escalate.** {narrowest[0]} treats this isolate and is "
            f"{saved} spectrum {'band' if saved == 1 else 'bands'} narrower "
            f"than {current_drug}. Narrowing now is what keeps the broad agents "
            f"working for the patient who has no alternative."
        )
    else:
        message = (
            f"**Already appropriately narrow.** {current_drug} covers this "
            f"isolate and nothing narrower does. No change needed."
        )

    return DeEscalation(
        organism=organism,
        current=current_drug,
        current_works=current_works,
        recommended=narrowest[0],
        recommended_probability=narrowest[1],
        spectrum_saved=max(saved, 0),
        rupees_saved=0.0,      # filled in by the caller, which knows the duration
        options=effective[:8],
        lab_confirmed=bool(lab_set),
        message=message,
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

    organism_index, columns, matrix = _matrix(setting, year)
    priors = _prior_vector(site, setting, year)
    positions = [columns.index(a) for a in antibiotics if a in columns]
    if not positions:
        raise KeyError(f"No formulary agent among: {antibiotics}")

    # Covered if ANY agent covers it, organism by organism.
    best = matrix[:, positions].max(axis=1)
    contributions = priors * best
    baseline = float(contributions.sum())

    reverse = {i: name for name, i in organism_index.items()}
    breakdown = [
        OrganismContribution(reverse[i], float(priors[i]), float(best[i] * 100),
                             float(contributions[i]))
        for i in range(len(priors)) if priors[i] > 0
    ]
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

    Every unordered pair of the formulary is scored. Among pairs within a
    whisker of the best coverage the narrower one wins, so the answer is not
    simply 'add another last-line drug'.
    """
    singles = rank_antibiotics(site, setting, selected_factors, year)
    best_single = singles[0]

    _, columns, matrix = _matrix(setting, year)
    priors = _prior_vector(site, setting, year)
    spectra = np.array(
        [int(data.drug_row(name)["spectrum"]) for name in columns], dtype=float
    )

    anchors = [columns.index(anchor)] if anchor and anchor in columns else range(len(columns))

    best_pair, best_score, best_spectrum = None, -1.0, 99
    for i in anchors:
        # Every partner at once: max against column i, then one product.
        pair_matrix = np.maximum(matrix[:, [i]], matrix)
        coverages = priors @ pair_matrix
        widths = np.maximum(spectra[i], spectra)
        for j in np.argsort(-coverages):
            if j == i:
                continue
            score, width = float(coverages[j]), int(widths[j])
            # Prefer the narrower pairing among those within a whisker.
            if score > best_score + 0.015 or (
                score >= best_score - 0.015 and width < best_spectrum
            ):
                best_pair, best_score, best_spectrum = (columns[i], columns[j]), score, width
            break

    if best_pair is None:
        return best_single, best_single
    return (
        score_combination(list(best_pair), site, setting, selected_factors, year),
        best_single,
    )


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
