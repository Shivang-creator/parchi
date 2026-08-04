"""The consult screen — one patient, one prescription, four checks.

Parchi never prescribes. It drafts, shows its working, and waits for the
clinician to accept or reject. Every rejection is recorded, because a tool
that is routinely overruled needs to say so out loud rather than keep
recommending confidently into the void.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import coverage, data, dosing, safety

from . import theme


def _chip(label: str, value: str) -> str:
    return f'<span class="chip">{label} <b>{value}</b></span>'


def _check_tile(header: str, value: str, detail: str, colour: str) -> str:
    return (
        f'<div class="check" style="--c:{colour}">'
        f'<div class="h">{header}</div>'
        f'<div class="v">{value}</div>'
        f'<div class="d">{detail}</div>'
        f"</div>"
    )


def _alert_card(severity: str, title: str, body: str) -> str:
    colour = theme.SEVERITY_COLOR.get(severity, theme.MUTED)
    return (
        f'<div class="alert" style="--c:{colour}">'
        f'<span class="pill" style="--c:{colour}">{severity}</span>'
        f'<span class="t">{title}</span>'
        f'<div class="b">{body}</div>'
        f"</div>"
    )


def _contribution_chart(result: coverage.CoverageResult) -> go.Figure:
    """Where the coverage number came from, organism by organism.

    This is the anti-black-box panel. A clinician who cannot see why a score
    is what it is will, correctly, ignore the score.
    """
    rows = [c for c in result.breakdown if c.prior > 0.005][:8]
    labels = [c.organism.replace(" ", "<br>", 1) for c in rows]
    values = [c.contribution * 100 for c in rows]
    lost = [(c.prior * 100) - (c.contribution * 100) for c in rows]

    fig = go.Figure()
    fig.add_bar(
        y=labels, x=values, orientation="h", name="Covered",
        marker_color=theme.GOOD,
        hovertemplate="%{y}<br>covered: %{x:.1f} pts<extra></extra>",
    )
    fig.add_bar(
        y=labels, x=lost, orientation="h", name="Not covered",
        marker_color="rgba(229,72,77,0.35)",
        hovertemplate="%{y}<br>lost to resistance: %{x:.1f} pts<extra></extra>",
    )
    fig.update_layout(
        **theme.PLOTLY_LAYOUT,
        barmode="stack",
        height=max(220, 34 * len(rows) + 70),
        showlegend=True,
        legend=dict(orientation="h", y=1.14, x=0, font=dict(size=11)),
        xaxis_title="Contribution to coverage (percentage points)",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def _trend_chart(trend, projection, threshold: float, drug: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=trend["year"], y=trend["coverage"], mode="lines+markers",
        name="Observed", line=dict(color=theme.ACCENT, width=3),
        marker=dict(size=7),
    )
    fig.add_scatter(
        x=projection["year"], y=projection["coverage"], mode="lines",
        name="Projected", line=dict(color=theme.WARN, width=2, dash="dot"),
    )
    fig.add_hline(
        y=threshold, line=dict(color=theme.BAD, width=1.5, dash="dash"),
        annotation_text=f"{threshold:.0f}% empiric floor",
        annotation_font_color=theme.BAD, annotation_font_size=11,
    )
    fig.update_layout(
        **theme.PLOTLY_LAYOUT, height=280,
        title=dict(text=f"{drug} — expected coverage over time", font=dict(size=14)),
        legend=dict(orientation="h", y=1.16, x=0, font=dict(size=11)),
        yaxis_title="Coverage %", yaxis_range=[0, 100],
    )
    return fig


def render() -> None:
    st.markdown(
        '<div class="disclaimer"><b>Demonstration build.</b> Every figure is '
        "indicative, compiled from published ICMR-AMRSN / WHO GLASS / CDSCO / NPPA "
        "patterns to exercise the engines end to end. Not a clinical device and "
        "not for patient care.</div>",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Patient parameters
    # ------------------------------------------------------------------
    with st.sidebar:
        st.markdown("#### Patient")
        c1, c2 = st.columns(2)
        age = c1.number_input("Age", 0, 110, 68)
        sex = c2.selectbox("Sex", ["Female", "Male"])
        c3, c4 = st.columns(2)
        weight = c3.number_input("Weight (kg)", 2.0, 200.0, 52.0, step=0.5)
        creatinine = c4.number_input("Creatinine", 0.1, 15.0, 1.9, step=0.1,
                                     help="Serum creatinine, mg/dL")

        st.markdown("#### Presentation")
        site = st.selectbox("Infection site", data.infection_sites(), index=5)
        setting = st.selectbox("Setting", ["OPD", "Ward", "ICU"])
        days = st.slider("Days of therapy", 3, 21, 7)

        st.markdown("#### Risk factors")
        factors = st.multiselect(
            "Present in this patient",
            list(data.risk_factors()["factor"]),
            default=["Indwelling urinary catheter"],
            label_visibility="collapsed",
        )

        st.markdown("#### Current medication")
        current_meds_raw = st.text_area(
            "One per line",
            value="Tab Sertraline 50 mg\nTab Ramipril 5 mg",
            height=90,
            label_visibility="collapsed",
        )
        current_meds = [m.strip() for m in current_meds_raw.splitlines() if m.strip()]

        oral_only = st.checkbox("Oral agents only", value=(setting == "OPD"))
        show_moderate = st.checkbox("Include moderate interactions", value=False)

    patient = dosing.Patient(
        age=int(age), sex=sex, weight_kg=float(weight),
        serum_creatinine=float(creatinine), setting=setting,
    )
    crcl = dosing.cockcroft_gault(patient)

    # ------------------------------------------------------------------
    # Engines
    # ------------------------------------------------------------------
    ranked = coverage.rank_antibiotics(
        site, setting, factors, route_filter="PO" if oral_only else None
    )
    if not ranked:
        st.error("No formulary agent matches that route filter.")
        return

    # Anything contraindicated at this renal function is not a candidate.
    viable, blocked_by_renal = [], []
    for result in ranked:
        if dosing.dose_for(result.antibiotic, patient).blocked:
            blocked_by_renal.append(result)
        else:
            viable.append(result)

    recommendation = coverage.stewardship_choice(viable or ranked, setting)
    choice = recommendation.choice
    dose = dosing.dose_for(choice.antibiotic, patient)
    cost = dosing.course_cost(choice.antibiotic, days, dose.dose_fraction)
    tier = coverage.adequacy_tier(choice.coverage, setting)
    colour = theme.tier_style(tier)

    alerts = safety.run_all([choice.antibiotic], current_meds, show_moderate)

    # ------------------------------------------------------------------
    # Patient strip
    # ------------------------------------------------------------------
    chips = (
        _chip("Age", f"{age}")
        + _chip("Weight", f"{weight:.0f} kg")
        + _chip("Creatinine", f"{creatinine:.1f}")
        + _chip("CrCl", f"{crcl:.0f} mL/min")
        + _chip("Renal", dose.ckd_stage)
        + _chip("Setting", setting)
    )
    st.markdown(chips, unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([2.6, 1])

    with left:
        st.markdown(
            f'<div class="draft" style="--tier:{colour}">'
            f'<div class="card-label">Parchi drafts — awaiting your approval</div>'
            f'<div class="drug">{choice.antibiotic}</div>'
            f'<div class="dose">{dose.dose_text} &nbsp;·&nbsp; {days} days &nbsp;·&nbsp; {choice.route}</div>'
            f'<div class="rationale">{recommendation.rationale}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f'<div class="card" style="--tier:{colour};text-align:center">'
            f'<div class="card-label">Expected coverage</div>'
            f'<div class="bignum" style="--tier:{colour}">{choice.coverage_pct:.0f}<span style="font-size:20px">%</span></div>'
            f'<div class="bignum-sub">{theme.TIER_LABEL[tier]}<br>'
            f"bar for {setting}: {recommendation.target:.0%}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # The four checks
    # ------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            _check_tile(
                "Will it work",
                f"{choice.coverage_pct:.0f}%",
                f"{choice.gap_pct:.0f} points of that lost to this patient's "
                f"risk factors alone." if choice.gap_pct > 0.5
                else "No risk-factor penalty applied.",
                colour,
            ),
            unsafe_allow_html=True,
        )

    with k2:
        dose_colour = (
            theme.BAD if dose.blocked else theme.WARN if dose.adjusted else theme.GOOD
        )
        st.markdown(
            _check_tile(
                "Right dose",
                dose.action.title(),
                f"CrCl {crcl:.0f} — {dose.guidance}",
                dose_colour,
            ),
            unsafe_allow_html=True,
        )

    with k3:
        cost_colour = theme.WARN if cost.multiple >= 3 else theme.GOOD
        cheapest = "Jan Aushadhi" if cost.janaushadhi_available else "generic"
        st.markdown(
            _check_tile(
                "Can they pay",
                f"₹{cost.best_total:,.0f}",
                f"Branded course ₹{cost.brand_total:,.0f} — "
                f"{cost.multiple}× the {cheapest} price. Saves ₹{cost.saving:,.0f}.",
                cost_colour,
            ),
            unsafe_allow_html=True,
        )

    with k4:
        blocking = [a for a in alerts if a.is_blocking]
        safety_colour = theme.BAD if blocking else theme.WARN if alerts else theme.GOOD
        st.markdown(
            _check_tile(
                "Is it safe",
                f"{len(alerts)}" if alerts else "Clear",
                f"{len(blocking)} blocking, {len(alerts) - len(blocking)} advisory."
                if alerts else "No banned combination or major interaction.",
                safety_colour,
            ),
            unsafe_allow_html=True,
        )

    st.write("")

    # ------------------------------------------------------------------
    # Alerts — only what is actionable
    # ------------------------------------------------------------------
    if alerts:
        st.markdown('<div class="card-label">Alerts</div>', unsafe_allow_html=True)
        for alert in alerts:
            st.markdown(
                _alert_card(alert.severity, alert.title, alert.detail),
                unsafe_allow_html=True,
            )

    if blocked_by_renal:
        names = ", ".join(r.antibiotic for r in blocked_by_renal[:4])
        st.markdown(
            _alert_card(
                "MAJOR",
                f"Excluded at CrCl {crcl:.0f}: {names}",
                "These were removed from consideration before ranking — "
                "contraindicated at this renal function regardless of how well "
                "they cover.",
            ),
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Human in the loop
    # ------------------------------------------------------------------
    st.write("")
    a1, a2, a3 = st.columns([1, 1, 3])
    if a1.button("Accept prescription", type="primary", width='stretch'):
        st.session_state.setdefault("decisions", []).append((choice.antibiotic, "accepted"))
        st.success(f"{choice.antibiotic} accepted and written to the parchi.")
    if a2.button("Reject / override", width='stretch'):
        st.session_state.setdefault("decisions", []).append((choice.antibiotic, "rejected"))
        st.warning("Rejection logged. Pick an alternative from the table below.")

    decisions = st.session_state.get("decisions", [])
    if decisions:
        rejected = sum(1 for _, d in decisions if d == "rejected")
        st.caption(
            f"This session: {len(decisions)} decisions, {rejected} overrides "
            f"({rejected / len(decisions):.0%}). A tool overruled this often is "
            f"wrong about this population and should be retuned, not trusted harder."
        )

    # ------------------------------------------------------------------
    # Show the working
    # ------------------------------------------------------------------
    st.write("")
    t1, t2, t3, t4 = st.tabs(
        ["Why this number", "Alternatives", "Resistance trajectory", "Combination therapy"]
    )

    with t1:
        st.markdown(
            f"Coverage is the probability that **{choice.antibiotic}** kills whatever "
            f"is actually causing a **{site.lower()}** in a **{setting}** patient — "
            "summed over every organism that plausibly caused it, weighted by how "
            "likely each one is here."
        )
        st.plotly_chart(
            _contribution_chart(choice), width='stretch',
            config={"displayModeBar": False},
        )
        if choice.risk_penalty < 1:
            st.caption(
                f"Risk-factor multiplier applied: ×{choice.risk_penalty:.2f} "
                f"({len(factors)} factor(s) selected). Before adjustment this drug "
                f"covered {choice.baseline_coverage * 100:.1f}%."
            )

    with t2:
        rows = []
        for r in (viable or ranked)[:12]:
            d = dosing.dose_for(r.antibiotic, patient)
            c = dosing.course_cost(r.antibiotic, days, d.dose_fraction)
            rows.append(
                {
                    "Antibiotic": r.antibiotic,
                    "Coverage %": round(r.coverage_pct, 1),
                    "Spectrum": "▮" * r.spectrum,
                    "AWaRe": r.who_aware,
                    "Route": r.route,
                    "Dose action": d.action.title(),
                    f"Course ₹ ({days}d)": round(c.best_total),
                    "Brand ₹": round(c.brand_total),
                }
            )
        st.dataframe(rows, width='stretch', hide_index=True)
        st.caption(
            "Ranked by coverage, but the draft above deliberately picks the "
            "*narrowest* agent that clears the bar — not the strongest one."
        )

    with t3:
        trend = coverage.coverage_trend(choice.antibiotic, site, setting, factors)
        projection, expiry = coverage.project_expiry(trend, threshold=50.0)
        st.plotly_chart(
            _trend_chart(trend, projection, 50.0, choice.antibiotic),
            width='stretch', config={"displayModeBar": False},
        )
        if expiry and expiry <= data.LATEST_YEAR:
            st.error(
                f"**{choice.antibiotic} fell below 50% coverage for this "
                f"indication in {expiry}.** It is still routinely prescribed."
            )
        elif expiry:
            st.warning(
                f"On the current trajectory, **{choice.antibiotic} drops below "
                f"50% coverage for this indication around {expiry}** — "
                f"{expiry - data.LATEST_YEAR} years from the latest surveillance year."
            )
        else:
            st.info("No downward crossing projected within the modelled horizon.")

    with t4:
        st.markdown(
            "For a patient this sick, monotherapy may not be the right question. "
            "A combination is scored organism-by-organism — it covers a bug if "
            "*either* agent does — which is why adding a second carbapenem buys "
            "almost nothing and adding colistin buys a great deal."
        )
        best_pair, best_single = coverage.best_combination(site, setting, factors)
        cc1, cc2 = st.columns(2)
        cc1.metric("Best single agent", best_single.antibiotic,
                   f"{best_single.coverage_pct:.0f}% coverage")
        cc2.metric("Best pairing", best_pair.antibiotic,
                   f"+{best_pair.coverage_pct - best_single.coverage_pct:.0f} points")

        pairs = [
            ["Meropenem", "Colistin"],
            ["Meropenem", "Imipenem-Cilastatin"],
            ["Meropenem", "Vancomycin"],
            ["Piperacillin-Tazobactam", "Amikacin"],
        ]
        st.dataframe(
            [
                {
                    "Combination": " + ".join(p),
                    "Coverage %": round(
                        coverage.score_combination(p, site, setting, factors).coverage_pct, 1
                    ),
                }
                for p in pairs
            ],
            width='stretch', hide_index=True,
        )
