"""The pharmacy counter — where a prescription becomes a bill.

This is the last place anything can be changed and the only place anyone finds
out what the slip actually costs. Medicines are the largest single component of
Indian out-of-pocket health spending, and out-of-pocket spending is the
mechanism by which illness becomes poverty.

The affordability model is the point of this screen. A course that costs four
days of income does not get half-taken — it gets abandoned, and a partial
antibiotic course is worse than none, because it selects for resistance without
curing anything.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import data, pharmacy as rx, safety

from . import components as c
from . import theme


def _price_chart(review: rx.DispensingReview) -> go.Figure:
    """Brand against cheapest equivalent, line by line."""
    p = theme.palette()
    names = [line.antibiotic for line in review.lines]
    brand = [line.brand_total for line in review.lines]
    cheap = [line.cheapest_total for line in review.lines]

    fig = go.Figure()
    fig.add_bar(y=names, x=brand, orientation="h", name="As branded",
                marker_color=p.RX, opacity=0.55,
                hovertemplate="%{y}<br>₹%{x:,.0f} branded<extra></extra>")
    fig.add_bar(y=names, x=cheap, orientation="h", name="Cheapest equivalent",
                marker_color=p.SAFE,
                hovertemplate="%{y}<br>₹%{x:,.0f}<extra></extra>")
    fig.update_layout(**theme.layout(
        height=max(200, 46 * len(names) + 70), barmode="overlay", bargap=0.45,
        legend=dict(orientation="h", y=1.16, x=1, xanchor="right", font=dict(size=11)),
        xaxis=dict(title="Cost of the course (₹)"),
    ))
    fig.update_yaxes(autorange="reversed", ticksuffix="  ")
    return fig


def _stock_chart(rows: list[dict]) -> go.Figure:
    """Months of cover per agent, narrowest agents highlighted."""
    p = theme.palette()
    shown = rows[:14]
    names = [r["antibiotic"] for r in shown]
    cover = [min(r["months_of_cover"], 4) for r in shown]
    colours = [
        p.DANGER if r["months_of_cover"] < 1 else
        p.CAUTION if r["months_of_cover"] < 1.5 else p.SAFE
        for r in shown
    ]
    fig = go.Figure()
    fig.add_bar(y=names, x=cover, orientation="h", marker_color=colours,
                customdata=[[r["spectrum"], r["aware"]] for r in shown],
                hovertemplate="%{y}<br>%{x:.2f} months of cover"
                              "<br>spectrum %{customdata[0]} · %{customdata[1]}"
                              "<extra></extra>")
    fig.add_vline(x=1.0, line=dict(color=p.DANGER, width=1, dash="dash"))
    fig.update_layout(**theme.layout(
        height=max(240, 26 * len(shown) + 60), showlegend=False, bargap=0.3,
        xaxis=dict(title="Months of cover at current consumption"),
    ))
    fig.update_yaxes(autorange="reversed", ticksuffix="  ")
    return fig


def render() -> None:
    p = theme.palette()

    st.markdown(
        "The slip arrives at the counter. This is the last place anything can "
        "be changed — and the first place anyone finds out what it costs."
    )
    st.markdown(c.rule(soft=True), unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # The slip as presented
    # ------------------------------------------------------------------
    st.markdown(c.label("The slip as presented"), unsafe_allow_html=True)
    s1, s2, s3 = st.columns([2.2, 1, 1])
    drugs = s1.multiselect(
        "Drugs on the slip", data.antibiotic_names(),
        default=["Levofloxacin", "Linezolid"], label_visibility="collapsed",
    )
    days = s2.number_input("Days", 1, 28, 7)
    household = s3.selectbox("Household", list(data.affordability()["reference"]))

    o1, o2 = st.columns([1, 3])
    pregnant = o1.checkbox("Patient is pregnant", value=False)

    if not drugs:
        st.info("Add at least one drug to the slip.")
        return

    items = [(d, int(days), 1.0) for d in drugs]
    review = rx.review(items, pregnant=pregnant)
    money = rx.affordability(review.cheapest_total, household)
    money_branded = rx.affordability(review.brand_total, household)
    risk_colour = theme.risk_colors().get(money.risk, p.INK_3)
    alerts = safety.run_all(drugs, [], include_moderate=True)
    blocking = [a for a in alerts if a.is_blocking]

    # ------------------------------------------------------------------
    # The counter's verdict
    # ------------------------------------------------------------------
    left, right = st.columns([2.35, 1], gap="medium")

    with left:
        headline = (
            f"₹{review.cheapest_total:,.0f}" if review.saving > 0
            else f"₹{review.brand_total:,.0f}"
        )
        st.markdown(
            c.slip(
                drug=headline,
                sig=f"{len(review.lines)} item(s)   ·   {days} days   ·   "
                    f"substituted to {review.lines[0].cheapest_tier} where available",
                who=f"<b>Pharmacy counter</b> &nbsp;·&nbsp; {household} "
                    f"&nbsp;·&nbsp; ₹{money.daily_income:,.0f} per day",
                why=(
                    f"Dispensed as written this slip costs "
                    f"<b>₹{review.brand_total:,.0f}</b>. Substituting every line to "
                    f"the identical molecule at the cheapest available tier brings it "
                    f"to <b>₹{review.cheapest_total:,.0f}</b> — a saving of "
                    f"₹{review.saving:,.0f}, or {review.saving_pct:.0f}%. "
                    f"{money.guidance}"
                ),
                accent=risk_colour,
                marks=[
                    ("Days of household income", f"{money.days_of_income:.2f}"),
                    ("As branded", f"{money_branded.days_of_income:.2f} days"),
                    ("Abandonment risk", money.risk),
                ],
            ),
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            f'<div class="verdict" style="--c:{risk_colour}">'
            f'{c.label("Days of income")}'
            f'<div class="n">{money.days_of_income:.1f}</div>'
            f'<div class="bar"><i style="width:'
            f'{min(money.days_of_income / 4 * 100, 100):.0f}%"></i></div>'
            f'<div class="say"><b>{money.risk}</b> abandonment risk<br>'
            f'<span style="color:var(--ink-3)">₹{money.total_inr:,.0f} against '
            f'₹{money.daily_income:,.0f} a day</span></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Counter checks
    # ------------------------------------------------------------------
    stock_colour = theme.DANGER if review.out_of_stock else theme.SAFE
    preg_colour = (
        theme.DANGER if any(cat == "Avoid" for _, cat, _ in review.pregnancy_flags)
        else theme.CAUTION if review.pregnancy_flags else theme.SAFE
    )
    st.markdown(
        c.checks([
            ("Substitution", f"₹{review.saving:,.0f}",
             f"saved — {review.saving_pct:.0f}% off the branded slip",
             theme.SAFE if review.saving > 0 else theme.INK_3),
            ("Affordability", money.risk,
             f"{money.days_of_income:.2f} days of income at ₹{money.daily_income:,.0f}/day",
             risk_colour),
            ("On the shelf", "Out" if review.out_of_stock else "In stock",
             ", ".join(review.out_of_stock) if review.out_of_stock
             else "every line dispensable today", stock_colour),
            ("Safe to dispense", f"{len(alerts)}" if alerts else "Clear",
             f"{len(blocking)} blocking" if alerts
             else "no banned combination or major interaction",
             theme.DANGER if blocking else theme.CAUTION if alerts else theme.SAFE),
            ("Pregnancy", f"{len(review.pregnancy_flags)}" if pregnant else "n/a",
             "; ".join(f"{n} — {cat}" for n, cat, _ in review.pregnancy_flags)
             if review.pregnancy_flags else
             ("nothing flagged" if pregnant else "not applicable"),
             preg_colour if pregnant else theme.INK_3),
        ]),
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------
    notes = []
    if money.is_catastrophic:
        notes.append(c.note(
            "CATASTROPHIC", f"{money.days_of_income:.1f} days of income",
            "This is the point at which a course stops being completed. A "
            "partially taken antibiotic course is worse than none — it selects "
            "for resistance without curing the infection. Substitute, shorten "
            "where clinically safe, or refer to a Jan Aushadhi kendra before "
            "the patient leaves the counter.",
            theme.DANGER))
    for name, category, note_text in review.pregnancy_flags:
        notes.append(c.note(
            "PREGNANCY" if category == "Caution" else "CONTRAINDICATED",
            f"{name} — {category.lower()} in pregnancy", note_text,
            theme.DANGER if category == "Avoid" else theme.CAUTION))
    for alert in alerts:
        notes.append(c.note(alert.severity, alert.title, alert.detail))
    for name in review.out_of_stock:
        notes.append(c.note(
            "STOCK", f"{name} is not on the shelf in this quantity",
            "The prescriber cannot know this. A stock-out of a narrow agent is "
            "the quiet reason a broad-spectrum drug gets dispensed instead.",
            theme.CAUTION))

    if notes:
        st.markdown(c.label("Before it is handed over"), unsafe_allow_html=True)
        for note in notes:
            st.markdown(note, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Line by line
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Line by line", "What to tell the patient", "The shelf"])

    with t1:
        st.plotly_chart(_price_chart(review), width="stretch",
                        config={"displayModeBar": False})
        st.dataframe(
            [
                {
                    "Drug": line.antibiotic,
                    "Units": f"{line.units:.0f}",
                    "As branded ₹": f"{line.brand_total:,.0f}",
                    "Generic ₹": f"{line.generic_total:,.0f}",
                    "Jan Aushadhi ₹": (f"{line.janaushadhi_total:,.0f}"
                                       if line.janaushadhi_available else "—"),
                    "You pay ₹": f"{line.cheapest_total:,.0f}",
                    "Times cheaper": f"{line.multiple}×",
                    "Shelf": "yes" if line.in_stock else "OUT",
                }
                for line in review.lines
            ],
            width="stretch", hide_index=True,
        )
        st.markdown(
            c.caveat(
                "Jan Aushadhi kendras — more than 15,000 of them — sell the "
                "identical molecule at a fraction of the branded price. The "
                "prescription is written by brand name, so the patient buys the "
                "expensive one. Nothing about that is a clinical decision; it is "
                "a naming convention with a price attached."
            ),
            unsafe_allow_html=True,
        )

    with t2:
        if review.counselling:
            for name, timing, advice in review.counselling:
                st.markdown(
                    c.note("COUNSEL", f"{name} — {timing.lower()}", advice,
                           theme.STAMP),
                    unsafe_allow_html=True,
                )
            st.markdown(
                c.caveat(
                    "Counselling is the part of dispensing that is free, "
                    "evidence-based and almost never done. Doxycycline taken "
                    "lying down ulcerates the oesophagus; metronidazole with "
                    "alcohol causes a severe reaction; a fluoroquinolone taken "
                    "with an antacid is barely absorbed at all."
                ),
                unsafe_allow_html=True,
            )
        else:
            st.info("No counselling notes for these agents.")

    with t3:
        rows = rx.stock_pressure()
        st.plotly_chart(_stock_chart(rows), width="stretch",
                        config={"displayModeBar": False})
        at_risk = [r for r in rows if r["months_of_cover"] < 1.0]
        narrow_at_risk = [r for r in at_risk if r["spectrum"] <= 2]
        if narrow_at_risk:
            st.markdown(
                c.note(
                    "STEWARDSHIP", "The narrow agents are the ones running out",
                    f"{len(at_risk)} agents have under a month of cover, and "
                    f"{len(narrow_at_risk)} of those are narrow-spectrum: "
                    f"<b>{', '.join(r['antibiotic'] for r in narrow_at_risk)}</b>. "
                    f"A prescriber who cannot get the narrow drug writes the broad "
                    f"one, and every piece of stewardship advice upstream becomes "
                    f"theoretical. Supply is a stewardship intervention.",
                    theme.DANGER,
                ),
                unsafe_allow_html=True,
            )
