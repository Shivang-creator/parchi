"""The consult — one patient, one prescription, four checks.

Parchi never prescribes. It drafts, shows its working, and waits for the
clinician to accept or reject. Every override is recorded, because a tool that
is routinely overruled needs to say so out loud rather than keep recommending
confidently into the void.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import coverage, data, dosing, safety

from . import components as c
from . import theme

ROUTE_WORDS = {"PO": "oral", "IV": "intravenous", "PO/IV": "oral or IV"}

ADJUNCT_CHOICES = [
    "Paracetamol", "Metronidazole", "Ondansetron", "Pantoprazole",
    "Diclofenac", "Azithromycin", "Cefixime", "Ciprofloxacin",
    "Doxycycline", "Amoxicillin-Clavulanate", "Levofloxacin", "Linezolid",
]


# --------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------
def _contribution_chart(result: coverage.CoverageResult) -> go.Figure:
    """Where the coverage number came from, organism by organism.

    The anti-black-box panel. A clinician who cannot see why a score is what it
    is will, correctly, ignore the score.
    """
    rows = [x for x in result.breakdown if x.prior > 0.004][:9]
    labels = [x.organism for x in rows]
    covered = [x.contribution * 100 for x in rows]
    lost = [(x.prior * 100) - (x.contribution * 100) for x in rows]

    fig = go.Figure()
    fig.add_bar(
        y=labels, x=covered, orientation="h", name="Covered",
        marker_color=theme.SAFE,
        hovertemplate="%{y}<br>covered: %{x:.1f} points<extra></extra>",
    )
    fig.add_bar(
        y=labels, x=lost, orientation="h", name="Lost to resistance",
        marker_color="rgba(163,43,34,0.30)",
        marker_line=dict(color="rgba(163,43,34,0.55)", width=1),
        hovertemplate="%{y}<br>lost: %{x:.1f} points<extra></extra>",
    )
    fig.update_layout(**theme.layout(
        barmode="stack",
        height=max(210, 30 * len(rows) + 72), showlegend=True,
        legend=dict(orientation="h", y=1.16, x=0, font=dict(size=11)),
        xaxis_title="Share of expected coverage (percentage points)",
        bargap=0.34,
    ))
    fig.update_yaxes(autorange="reversed", ticksuffix="  ")
    return fig


def _trend_chart(trend, projection, floor: float, drug: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=trend["year"], y=trend["coverage"], mode="lines+markers",
        name="Observed", line=dict(color=theme.STAMP, width=2.4),
        marker=dict(size=6.5),
    )
    fig.add_scatter(
        x=projection["year"], y=projection["coverage"], mode="lines",
        name="Projected", line=dict(color=theme.RX, width=1.8, dash="dot"),
    )
    fig.add_hline(
        y=floor, line=dict(color=theme.INK_3, width=1, dash="dash"),
        annotation_text=f"{floor:.0f}% — below this, empiric use is a guess",
        annotation_font=dict(color=theme.INK_3, size=10.5),
        annotation_position="bottom right",
    )
    fig.update_layout(**theme.layout(
        height=280, showlegend=True,
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=11)),
        title=dict(text=f"{drug} — expected coverage, {trend['year'].min()} onward",
                   x=0, xanchor="left", y=0.97,
                   font=dict(family="Newsreader, serif", size=15, color=theme.INK)),
        margin=dict(l=8, r=8, t=52, b=8),
        yaxis=dict(title="Coverage %", range=[0, 100],
                   gridcolor=theme.RULE_SOFT, tickfont=dict(color=theme.INK_3)),
    ))
    return fig


# --------------------------------------------------------------------------
# intake
# --------------------------------------------------------------------------
def _intake() -> dict:
    with st.sidebar:
        st.markdown(c.label("The patient"), unsafe_allow_html=True)
        a, b = st.columns(2)
        age = a.number_input("Age", 0, 110, 68)
        sex = b.selectbox("Sex", ["Female", "Male"])
        d, e = st.columns(2)
        weight = d.number_input("Weight (kg)", 2.0, 200.0, 52.0, step=0.5)
        creatinine = e.number_input(
            "Creatinine", 0.1, 15.0, 1.9, step=0.1,
            help="Serum creatinine in mg/dL. Drives every dose on this screen.",
        )

        st.markdown("#### Presentation")
        sites = data.infection_sites()
        site = st.selectbox("Infection", sites,
                            index=sites.index("Urinary tract infection"))
        allowed = data.settings_for(site)
        setting = st.selectbox(
            "Setting", allowed,
            help="Resistance differs sharply between outpatients, wards and ICU.",
        )

        advice_row = data.duration_for(site)
        default_days = int(advice_row["typical_days"]) if advice_row is not None else 7
        days = st.slider("Days of therapy", 1, 28, default_days)

        st.markdown("#### Risk factors")
        factors = st.multiselect(
            "Risk factors", list(data.risk_factors()["factor"]),
            default=["Indwelling urinary catheter"], label_visibility="collapsed",
        )

        st.markdown("#### Already taking")
        meds_raw = st.text_area(
            "Current medication", value="Tab Sertraline 50 mg\nTab Ramipril 5 mg",
            height=88, label_visibility="collapsed",
            help="Free text — brand or molecule, one per line.",
        )

        st.markdown("#### Also prescribing")
        adjuncts = st.multiselect(
            "Adjuncts", ADJUNCT_CHOICES, default=[], label_visibility="collapsed",
            help="Anything else going on the same slip. Checked together with "
                 "the antibiotic for banned combinations and interactions.",
        )

        st.markdown("#### Options")
        oral_only = st.checkbox(
            "Oral agents only", value=(setting == "OPD"), key="oral_only",
            help="An outpatient cannot be given an intravenous drug.",
        )
        show_moderate = st.checkbox("Include moderate interactions", value=False)

    return dict(
        age=int(age), sex=sex, weight=float(weight), creatinine=float(creatinine),
        site=site, setting=setting, days=int(days), factors=factors,
        meds=[m.strip() for m in meds_raw.splitlines() if m.strip()],
        adjuncts=adjuncts, oral_only=oral_only, show_moderate=show_moderate,
    )


# --------------------------------------------------------------------------
# screen
# --------------------------------------------------------------------------
def render() -> None:
    form = _intake()

    patient = dosing.Patient(
        age=form["age"], sex=form["sex"], weight_kg=form["weight"],
        serum_creatinine=form["creatinine"], setting=form["setting"],
    )
    crcl = dosing.cockcroft_gault(patient)

    ranked = coverage.rank_antibiotics(
        form["site"], form["setting"], form["factors"],
        route_filter="PO" if form["oral_only"] else None,
    )
    if not ranked:
        st.error("No agent in the formulary matches that route filter.")
        return

    # Contraindicated at this renal function is not a candidate — remove before
    # ranking, not flag after.
    viable, renal_blocked = [], []
    for result in ranked:
        if dosing.dose_for(result.antibiotic, patient).blocked:
            renal_blocked.append(result)
        else:
            viable.append(result)

    recommendation = coverage.stewardship_choice(viable or ranked, form["setting"])
    choice = recommendation.choice
    dose = dosing.dose_for(choice.antibiotic, patient)
    cost = dosing.course_cost(choice.antibiotic, form["days"], dose.dose_fraction)
    tier = coverage.adequacy_tier(choice.coverage, form["setting"])
    colour = theme.tier_style(tier)

    regimen = [choice.antibiotic] + form["adjuncts"]
    alerts = safety.run_all(regimen, form["meds"], form["show_moderate"])
    blocking = [a for a in alerts if a.is_blocking]
    duration = dosing.duration_advice(form["site"], form["days"])

    brand_total, cheap_total, saving = dosing.regimen_cost(
        [(choice.antibiotic, form["days"], dose.dose_fraction)]
        + [(a, form["days"], 1.0) for a in form["adjuncts"]]
    )

    # ---------------- patient strip ----------------
    st.markdown(
        c.patient_strip([
            ("Patient", f"{form['age']} · {form['sex'][0]}", f"{form['weight']:.0f} kg"),
            ("Creatinine", f"{form['creatinine']:.1f}", "mg/dL"),
            ("Creatinine clearance", f"{crcl:.0f}", "mL/min"),
            ("Renal function", dose.ckd_stage, ""),
            ("Presenting", form["site"], form["setting"]),
        ]),
        unsafe_allow_html=True,
    )

    # ---------------- the slip ----------------
    left, right = st.columns([2.35, 1], gap="medium")

    with left:
        who = (
            f"<b>{form['age']}-year-old {form['sex'].lower()}</b> &nbsp;·&nbsp; "
            f"{form['site'].lower()} &nbsp;·&nbsp; {form['setting']} &nbsp;·&nbsp; "
            f"CrCl {crcl:.0f}"
        )
        adjunct_lines = [f"+ {a} — {form['days']} days" for a in form["adjuncts"]]
        route_word = ROUTE_WORDS.get(choice.route, choice.route)
        st.markdown(
            c.slip(
                drug=choice.antibiotic,
                sig=f"{dose.dose_text}   ·   {form['days']} days   ·   {route_word}",
                who=who,
                why=recommendation.rationale,
                accent=colour,
                adjuncts=adjunct_lines,
                marks=[
                    ("Spectrum", c.spectrum_mark(choice.spectrum)),
                    ("WHO AWaRe", c.aware_mark(choice.who_aware)),
                    ("Class", str(data.drug_row(choice.antibiotic)["drug_class"])),
                ],
            ),
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            c.verdict(
                choice.coverage_pct,
                f"{theme.TIER_LABEL[tier]}<br>"
                f"<span style='color:{theme.INK_3}'>bar for {form['setting']} "
                f"is {recommendation.target:.0%}</span>",
                colour,
                target=recommendation.target,
            ),
            unsafe_allow_html=True,
        )

    # ---------------- the four checks ----------------
    dose_colour = (
        theme.DANGER if dose.blocked
        else theme.CAUTION if dose.adjusted else theme.SAFE
    )
    cost_ratio = (brand_total / cheap_total) if cheap_total else 0
    cost_colour = theme.CAUTION if cost_ratio >= 2.5 else theme.SAFE
    safety_colour = (
        theme.DANGER if blocking else theme.CAUTION if alerts else theme.SAFE
    )
    dur_colour = (
        theme.SAFE if not duration or duration.verdict == "APPROPRIATE"
        else theme.CAUTION
    )

    st.markdown(
        c.checks([
            (
                "Will it work",
                f"{choice.coverage_pct:.0f}%",
                (f"{choice.gap_pct:.0f} points of that lost to this patient's "
                 f"risk factors" if choice.gap_pct > 0.5
                 else "no risk-factor penalty applied"),
                colour,
            ),
            (
                "Right dose",
                dose.action.title(),
                f"CrCl {crcl:.0f} — {dose.guidance}",
                dose_colour,
            ),
            (
                "Right length",
                f"{form['days']}d" if not duration else duration.verdict.title(),
                (f"typical course is {duration.typical} days"
                 + (f"; {duration.excess_days} more than needed"
                    if duration.excess_days else "")
                 ) if duration else "no duration guidance for this site",
                dur_colour,
            ),
            (
                "What it costs",
                f"₹{cheap_total:,.0f}",
                (f"₹{brand_total:,.0f} as branded — {cost_ratio:.1f}× more, "
                 f"₹{saving:,.0f} saved" if saving > 0
                 else "no cheaper equivalent on the list"),
                cost_colour,
            ),
        ]),
        unsafe_allow_html=True,
    )

    # ---------------- annotations ----------------
    annotations: list[str] = []

    if renal_blocked:
        names = ", ".join(r.antibiotic for r in renal_blocked[:4])
        best_blocked = max(renal_blocked, key=lambda r: r.coverage)
        # Only claim it would have been the top choice if it actually beats
        # everything still standing.
        beat_the_field = best_blocked.coverage > choice.coverage
        annotations.append(c.note(
            "RENAL", f"Excluded at CrCl {crcl:.0f}: {names}",
            f"Removed before ranking, not flagged after. "
            f"{best_blocked.antibiotic} covers {best_blocked.coverage_pct:.0f}% "
            + (f"— <b>better than anything still available</b> — but is "
               f"contraindicated at this renal function."
               if beat_the_field else
               f"and is contraindicated at this renal function."),
            theme.DANGER,
        ))

    for alert in alerts:
        annotations.append(c.note(alert.severity, alert.title, alert.detail))

    if duration and duration.verdict in ("TOO LONG", "LONGER THAN NEEDED"):
        annotations.append(c.note(
            "DURATION", f"{form['days']} days is longer than the evidence supports",
            f"{duration.guidance} Shortening to {duration.typical} days removes "
            f"{duration.excess_days} days of selection pressure at no cost to cure.",
            theme.CAUTION,
        ))

    if recommendation.escalated and tier == "INADEQUATE":
        annotations.append(c.note(
            "ESCALATE", "No single agent is adequate here",
            "Send cultures before the first dose and consider combination "
            "therapy — see the combination panel below.",
            theme.DANGER,
        ))

    if annotations:
        st.markdown(c.label("Notes"), unsafe_allow_html=True)
        for item in annotations:
            st.markdown(item, unsafe_allow_html=True)
    else:
        st.markdown(
            c.note("CLEAR", "Nothing to flag",
                   "No banned combination, no major interaction, dose and "
                   "duration both appropriate for this patient.", theme.SAFE),
            unsafe_allow_html=True,
        )

    # ---------------- the decision ----------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    d1, d2, d3 = st.columns([1, 1, 2.4])
    if d1.button("Sign the parchi", type="primary", width="stretch"):
        st.session_state.setdefault("decisions", []).append((choice.antibiotic, "accepted"))
    if d2.button("Override", width="stretch"):
        st.session_state.setdefault("decisions", []).append((choice.antibiotic, "rejected"))

    decisions = st.session_state.get("decisions", [])
    with d3:
        if decisions:
            rejected = sum(1 for _, verdict in decisions if verdict == "rejected")
            rate = rejected / len(decisions)
            st.markdown(
                f"<div style='padding-top:6px;font-size:12.5px;color:{theme.INK_2}'>"
                f"{len(decisions)} decisions this session · "
                f"<b style='color:{theme.RX if rate > 0.4 else theme.INK}'>"
                f"{rate:.0%} overridden</b>. "
                f"{'A tool overruled this often is wrong about this population and should be retuned, not trusted harder.' if rate > 0.4 else 'Overrides are logged and reported — silence would be the failure mode.'}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ---------------- show the working ----------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(
        ["Why this number", "What else was considered", "Is it still working",
         "Two drugs instead of one"]
    )

    with t1:
        st.markdown(
            f"Coverage is the probability that **{choice.antibiotic}** kills "
            f"whatever is *actually* causing a {form['site'].lower()} in a "
            f"{form['setting']} patient — summed across every organism that "
            f"plausibly caused it, weighted by how likely each one is here."
        )
        # rank_antibiotics scores the whole formulary as one matrix product and
        # skips the per-organism detail; build it for the one drug we chose.
        detailed = coverage.score_antibiotic(
            choice.antibiotic, form["site"], form["setting"], form["factors"]
        )
        st.plotly_chart(_contribution_chart(detailed), width="stretch",
                        config={"displayModeBar": False})
        if choice.risk_penalty < 1:
            st.markdown(
                c.caveat(
                    f"Risk multiplier ×{choice.risk_penalty:.2f} applied from "
                    f"{len(form['factors'])} selected factor(s). Before adjustment "
                    f"this agent covered {choice.baseline_coverage * 100:.1f}%. "
                    f"Factors compound with a decaying exponent rather than "
                    f"multiplying naively — a ventilated patient has by definition "
                    f"had recent antibiotics, and counting both at full strength "
                    f"would be double-counting one exposure."
                ),
                unsafe_allow_html=True,
            )

    with t2:
        rows = []
        for r in (viable or ranked)[:14]:
            rd = dosing.dose_for(r.antibiotic, patient)
            rc = dosing.course_cost(r.antibiotic, form["days"], rd.dose_fraction)
            rows.append({
                "Antibiotic": r.antibiotic,
                "Coverage": f"{r.coverage_pct:.1f}%",
                "Spectrum": "▪" * r.spectrum + "▫" * (5 - r.spectrum),
                "AWaRe": r.who_aware,
                "Route": r.route,
                "Dose": rd.action.title(),
                f"Course ₹": f"{rc.best_total:,.0f}",
            })
        st.dataframe(rows, width="stretch", hide_index=True, height=min(520, 38 * len(rows) + 40))
        st.markdown(
            c.caveat(
                "Ranked by coverage — but the slip above deliberately picks the "
                "<b>narrowest</b> agent clearing the bar, not the strongest. "
                "Ranking by strength alone recommends colistin for an outpatient "
                "cystitis, which is precisely how last-line drugs get burned through."
            ),
            unsafe_allow_html=True,
        )

    with t3:
        trend = coverage.coverage_trend(
            choice.antibiotic, form["site"], form["setting"], form["factors"]
        )
        projection, expiry = coverage.project_expiry(trend, threshold=50.0)
        st.plotly_chart(_trend_chart(trend, projection, 50.0, choice.antibiotic),
                        width="stretch", config={"displayModeBar": False})
        if expiry and expiry <= data.LATEST_YEAR:
            st.markdown(c.note(
                "EXPIRED", f"Fell below 50% coverage in {expiry}",
                f"{choice.antibiotic} stopped being a reliable empiric choice for "
                f"this indication years ago. It is still routinely prescribed.",
                theme.DANGER), unsafe_allow_html=True)
        elif expiry:
            st.markdown(c.note(
                "EXPIRING", f"Projected below 50% around {expiry}",
                f"That is {expiry - data.LATEST_YEAR} years from the latest "
                f"surveillance year, on the current trajectory.",
                theme.CAUTION), unsafe_allow_html=True)
        else:
            st.markdown(c.note(
                "STABLE", "No downward crossing projected",
                "Coverage for this agent is holding within the modelled horizon.",
                theme.SAFE), unsafe_allow_html=True)

    with t4:
        st.markdown(
            "A combination is scored organism by organism — it covers a bug if "
            "*either* agent does. The naive alternative, `1 − Π(1 − pᵢ)`, assumes "
            "the agents fail independently. They do not: two carbapenems fail on "
            "the same carbapenemase. That is why adding a second carbapenem buys "
            "almost nothing and adding colistin buys a great deal."
        )
        pair, single = coverage.best_combination(
            form["site"], form["setting"], form["factors"]
        )
        k1, k2 = st.columns(2)
        k1.metric("Best single agent", single.antibiotic, f"{single.coverage_pct:.0f}% coverage")
        k2.metric("Best pairing", pair.antibiotic,
                  f"+{pair.coverage_pct - single.coverage_pct:.0f} points")

        candidates = [
            [choice.antibiotic, "Colistin"],
            [choice.antibiotic, "Amikacin"],
            [choice.antibiotic, "Vancomycin"],
            [choice.antibiotic, "Azithromycin"],
            ["Meropenem", "Colistin"],
            ["Meropenem", "Imipenem-Cilastatin"],
        ]
        seen, pairs = set(), []
        for combo in candidates:
            key = tuple(sorted(combo))
            if key in seen or combo[0] == combo[1]:
                continue
            seen.add(key)
            scored = coverage.score_combination(
                combo, form["site"], form["setting"], form["factors"]
            )
            pairs.append({
                "Combination": " + ".join(combo),
                "Coverage": f"{scored.coverage_pct:.1f}%",
                "Gain over best single": f"{scored.coverage_pct - single.coverage_pct:+.1f}",
            })
        st.dataframe(pairs, width="stretch", hide_index=True)