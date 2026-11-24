"""Day three — the culture comes back.

Empiric therapy is a bet placed blind. Forty-eight hours later the culture
settles it, and the single most valuable thing anyone can do is go back and
narrow the drug. Almost nobody does. The patient finishes a week of meropenem
for an organism a five-rupee tablet would have killed, and the carbapenem gets
a little less useful for everyone else.

This screen exists because de-escalation is the highest-value, most reliably
skipped action in antibiotic stewardship.
"""

from __future__ import annotations

import html

import streamlit as st

from engine import coverage, data, dosing

from . import components as c
from . import theme


def render() -> None:
    st.markdown(
        "Empiric therapy is a bet placed blind. The culture settles it — and "
        "de-escalating is the single most valuable step in stewardship, and the "
        "one most reliably skipped."
    )
    st.markdown(c.rule(soft=True), unsafe_allow_html=True)

    col_org, col_drug, col_set = st.columns([1.5, 1.3, 1])
    organism = col_org.selectbox("Organism isolated", data.organisms())
    current = col_drug.selectbox(
        "Currently on", data.antibiotic_names(),
        index=data.antibiotic_names().index("Meropenem"),
    )
    setting = col_set.selectbox("Setting", data.SETTINGS, index=2)

    # Offer only agents with any recorded activity against THIS organism.
    # Pre-selecting fosfomycin for an Acinetobacter isolate would be nonsense
    # on the face of it, and the lab list is treated as authoritative.
    plausible = coverage.active_agents(organism, setting)
    col_lab, col_days = st.columns([2.2, 1])
    lab = col_lab.multiselect(
        "Agents the lab reported susceptible (leave empty if the sensitivity "
        "report has not arrived)",
        plausible or data.antibiotic_names(),
        default=list(plausible[:4]),
        key=f"lab_{organism}_{setting}",
    )
    days_left = col_days.number_input("Days of therapy remaining", 1, 21, 5)

    result = coverage.deescalate(organism, current, setting, lab)

    st.markdown(c.rule(), unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # verdict
    # ------------------------------------------------------------------
    if result.recommended is None:
        accent = theme.DANGER
    elif not result.current_works:
        accent = theme.DANGER
    elif result.spectrum_saved > 0:
        accent = theme.SAFE
    else:
        accent = theme.STAMP

    left, right = st.columns([2.35, 1], gap="medium")

    with left:
        if result.recommended:
            new_dose = data.drug_row(result.recommended)
            sig = f"{new_dose['adult_dose']} × {int(new_dose['doses_per_day'])}/day   ·   {days_left} days remaining"
            source = (
                "lab sensitivity report" if result.lab_confirmed
                else f"{setting} surveillance, no sensitivity report yet"
            )
            st.markdown(
                c.slip(
                    drug=result.recommended,
                    sig=sig,
                    # The organism name can come from an uploaded antibiogram,
                    # and these two fields are rendered as raw HTML.
                    who=f"<b>{html.escape(organism)}</b> &nbsp;·&nbsp; isolated from a "
                        f"{setting} patient &nbsp;·&nbsp; currently on {current}",
                    why=html.escape(result.message.replace("**", "")),
                    accent=accent,
                    marks=[
                        ("Spectrum", c.spectrum_mark(int(new_dose["spectrum"]))),
                        ("WHO AWaRe", c.aware_mark(str(new_dose["who_aware"]))),
                        ("Evidence", source),
                    ],
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                c.note("NO NARROW OPTION", f"{organism}",
                       html.escape(result.message.replace("**", "")), theme.DANGER),
                unsafe_allow_html=True,
            )

    with right:
        old_cost = dosing.course_cost(current, int(days_left))
        if result.recommended:
            new_cost = dosing.course_cost(result.recommended, int(days_left))
            saved = old_cost.best_total - new_cost.best_total
            st.metric("Spectrum bands narrowed", result.spectrum_saved,
                      f"from {int(data.drug_row(current)['spectrum'])} to "
                      f"{int(data.drug_row(result.recommended)['spectrum'])}",
                      delta_color="off")
            st.metric("Cost of the remaining course", f"₹{new_cost.best_total:,.0f}",
                      f"₹{saved:,.0f} saved" if saved > 0 else "no change",
                      delta_color="normal" if saved > 0 else "off")
            st.markdown(
                c.stamp(
                    "DE-ESCALATE" if result.spectrum_saved > 0
                    else "ALREADY NARROW" if result.current_works
                    else "CHANGE REQUIRED",
                    accent,
                ),
                unsafe_allow_html=True,
            )
        else:
            st.metric("Cost of the remaining course", f"₹{old_cost.best_total:,.0f}")

    # ------------------------------------------------------------------
    # the options
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(c.label("Every agent active against this isolate, narrowest first"),
                unsafe_allow_html=True)

    if result.options:
        rows = []
        for drug, probability, spectrum in result.options:
            cost = dosing.course_cost(drug, int(days_left))
            meta = data.drug_row(drug)
            rows.append({
                "Antibiotic": drug,
                "Susceptible": ("confirmed by lab" if result.lab_confirmed
                                else f"{probability:.0f}% expected"),
                "Spectrum": "▪" * spectrum + "▫" * (5 - spectrum),
                "AWaRe": str(meta["who_aware"]),
                "Route": str(meta["route"]),
                "Remaining course ₹": f"{cost.best_total:,.0f}",
            })
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("No active agent in the formulary for this isolate.")

    st.markdown(
        c.caveat(
            "When the lab has reported sensitivities, that list is "
            "<b>authoritative</b> and overrides the surveillance estimate "
            "entirely — the isolate in front of you beats any population "
            "average. Without it, Parchi will not narrow on population data "
            "alone: that would be a guess dressed up as a recommendation."
        ),
        unsafe_allow_html=True,
    )
