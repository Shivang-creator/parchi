"""The surge screen — what is walking through the door in three weeks.

A dengue season is not a surprise. The curve repeats every year and peaks in
the same three months. Hospitals still meet it unprepared, because nobody
converts an epidemiological curve into the two numbers an administrator can
act on: extra OPD footfall, and platelet units on the shelf.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import data, forecast

from . import theme


def render() -> None:
    left, mid, right = st.columns([1.4, 1, 1])
    state = left.selectbox("State", data.states(), index=data.states().index("Kerala"))
    horizon = mid.slider("Forecast horizon (months)", 6, 24, 12)
    beds = right.number_input("Dengue-capable beds", 5, 2000, 60, step=5)

    with st.expander("Conversion assumptions — every factor is yours to change"):
        a1, a2, a3 = st.columns(3)
        assumptions = forecast.SurgeAssumptions(
            febrile_opd_per_case=a1.slider("Febrile OPD screens per confirmed case", 2.0, 20.0, 8.0),
            admission_rate=a2.slider("Admission rate", 0.02, 0.40, 0.10),
            mean_stay_days=a3.slider("Mean stay (days)", 2.0, 10.0, 4.5),
            platelet_transfusion_rate=a1.slider("Of admissions, transfused", 0.05, 0.80, 0.32),
            units_per_transfused_patient=a2.slider("Units per transfused patient", 1.0, 12.0, 4.0),
        )
        st.caption(
            "Defaults sit in reported ranges for dengue admission and transfusion "
            "practice. A hospital plugs in its own audit numbers and the entire "
            "forecast re-bases — nothing here is hard-coded into the model."
        )

    fc = forecast.forecast_months(state, horizon)
    demand = forecast.demand_from_cases(fc, assumptions)
    peak = forecast.peak_row(demand)
    ratio = forecast.surge_ratio(fc)

    # ------------------------------------------------------------------
    # Headline
    # ------------------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Peak month", peak["label"], f"{peak['cases']:,.0f} cases")
    m2.metric("Peak-to-trough", f"{ratio}×", "seasonal swing")
    m3.metric("Extra OPD screens", f"{peak['opd_screens']:,.0f}", "in the peak month")
    m4.metric("Platelet units", f"{peak['platelet_units']:,.0f}", "needed in peak month")

    bed_days_available = beds * 30
    strain = peak["bed_days"] / bed_days_available if bed_days_available else 0
    if strain > 1:
        st.error(
            f"**Peak demand exceeds capacity.** {peak['bed_days']:,.0f} bed-days "
            f"needed in {peak['label']} against {bed_days_available:,.0f} available "
            f"from {beds} beds — a {strain:.1f}× overshoot. That gap is visible "
            f"today, months before the first admission."
        )
    else:
        st.success(
            f"Projected peak fits current capacity at {strain:.0%} occupancy "
            f"({peak['bed_days']:,.0f} of {bed_days_available:,.0f} bed-days)."
        )

    # ------------------------------------------------------------------
    # Forecast chart
    # ------------------------------------------------------------------
    history = forecast.state_series(state).tail(30)
    fig = go.Figure()
    fig.add_scatter(
        x=[f"{forecast.MONTH_NAMES[m - 1]} {y}" for m, y in
           zip(history["month"], history["year"])],
        y=history["cases"], mode="lines", name="Observed",
        line=dict(color=theme.ACCENT, width=2.5),
    )
    labels = list(demand["label"])
    fig.add_scatter(
        x=labels, y=demand["upper"], mode="lines", name="80% band",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    )
    fig.add_scatter(
        x=labels, y=demand["lower"], mode="lines", name="80% band",
        line=dict(width=0), fill="tonexty",
        fillcolor="rgba(232,163,61,0.16)", hoverinfo="skip",
    )
    fig.add_scatter(
        x=labels, y=demand["cases"], mode="lines+markers", name="Forecast",
        line=dict(color=theme.WARN, width=2.5, dash="dot"), marker=dict(size=6),
    )
    fig.update_layout(
        **theme.PLOTLY_LAYOUT, height=340,
        title=dict(text=f"Dengue cases — {state}", font=dict(size=15)),
        legend=dict(orientation="h", y=1.14, x=0, font=dict(size=11)),
        yaxis_title="Monthly cases",
    )
    fig.update_xaxes(tickangle=-45, nticks=14)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    # ------------------------------------------------------------------
    # Demand table + method
    # ------------------------------------------------------------------
    c1, c2 = st.columns([1.5, 1])

    with c1:
        st.markdown('<div class="card-label">Month-by-month requirement</div>',
                    unsafe_allow_html=True)
        st.dataframe(
            [
                {
                    "Month": r["label"],
                    "Cases": f"{r['cases']:,.0f}",
                    "OPD screens": f"{r['opd_screens']:,.0f}",
                    "Admissions": f"{r['admissions']:,.0f}",
                    "Bed-days": f"{r['bed_days']:,.0f}",
                    "Platelet units": f"{r['platelet_units']:,.0f}",
                }
                for _, r in demand.iterrows()
            ],
            width='stretch', hide_index=True, height=330,
        )

    with c2:
        st.markdown('<div class="card-label">Seasonal index — learned, not assumed</div>',
                    unsafe_allow_html=True)
        index = forecast.seasonal_index(state)
        bar = go.Figure()
        bar.add_bar(
            x=forecast.MONTH_NAMES, y=index.values * 100,
            marker_color=[
                theme.BAD if v == index.max() else theme.ACCENT for v in index.values
            ],
        )
        bar.update_layout(
            **theme.PLOTLY_LAYOUT, height=250,
            yaxis_title="% of annual cases", showlegend=False,
        )
        st.plotly_chart(bar, width='stretch', config={"displayModeBar": False})
        top3 = index.sort_values(ascending=False).head(3)
        st.caption(
            f"**{', '.join(forecast.MONTH_NAMES[m - 1] for m in top3.index)}** carry "
            f"{top3.sum():.0%} of {state}'s annual dengue burden. "
            "The index is the average monthly share across every observed year — "
            "the model learns each state's own rhythm rather than assuming one."
        )

    # ------------------------------------------------------------------
    # National roster view
    # ------------------------------------------------------------------
    st.write("")
    st.markdown('<div class="card-label">When each state peaks — the roster view</div>',
                unsafe_allow_html=True)
    calendar = forecast.national_peak_calendar()
    heat = go.Figure()
    heat.add_bar(
        x=calendar["state"], y=calendar["annual_cases_latest"],
        marker_color=[
            theme.BAD if s == state else theme.LINE for s in calendar["state"]
        ],
        customdata=calendar["peak_month_name"],
        hovertemplate="%{x}<br>%{y:,.0f} cases<br>peaks in %{customdata}<extra></extra>",
    )
    heat.update_layout(
        **theme.PLOTLY_LAYOUT, height=260,
        yaxis_title="Latest-year cases", showlegend=False,
    )
    heat.update_xaxes(tickangle=-40)
    st.plotly_chart(heat, width='stretch', config={"displayModeBar": False})
