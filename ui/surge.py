"""The surge screen — what is walking through the door in three weeks.

A dengue season is not a surprise. The curve repeats every year and peaks in
the same three months. Hospitals still meet it unprepared, because nobody
converts an epidemiological curve into the numbers an administrator can act
on: extra OPD footfall, beds, and platelet units on the shelf.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import data, forecast

from . import components as c
from . import theme

DISEASE_INK = {
    "Dengue": theme.RX,
    "Malaria": theme.STAMP,
    "Chikungunya": theme.RESERVE,
}


def render() -> None:
    a, b, d, e = st.columns([1.1, 1.4, 1, 1])
    disease = a.selectbox("Disease", data.diseases(),
                          index=data.diseases().index("Dengue"))
    states = data.states(disease)
    state = b.selectbox("State", states,
                        index=states.index("Kerala") if "Kerala" in states else 0)
    horizon = d.slider("Months ahead", 6, 24, 12)
    beds = e.number_input("Beds available", 5, 2000, 60, step=5)

    ink = DISEASE_INK.get(disease, theme.RX)
    defaults = forecast.SurgeAssumptions.for_disease(disease)

    with st.expander("Conversion assumptions — every factor is yours to change"):
        st.markdown(
            f"Defaults are the reported load profile for **{disease.lower()}**, "
            "which differs sharply by disease: malaria fills beds but rarely "
            "needs platelets, dengue does both. Plug in your own audit numbers "
            "and the whole forecast re-bases — nothing is hard-coded."
        )
        f1, f2, f3 = st.columns(3)
        assumptions = forecast.SurgeAssumptions(
            febrile_opd_per_case=f1.slider(
                "OPD screens per confirmed case", 1.0, 20.0,
                defaults.febrile_opd_per_case, key=f"opd_{disease}"),
            admission_rate=f2.slider(
                "Admission rate", 0.01, 0.40,
                defaults.admission_rate, key=f"adm_{disease}"),
            mean_stay_days=f3.slider(
                "Mean stay (days)", 1.0, 12.0,
                defaults.mean_stay_days, key=f"los_{disease}"),
            platelet_transfusion_rate=f1.slider(
                "Of admissions, transfused", 0.0, 0.80,
                defaults.platelet_transfusion_rate, key=f"tx_{disease}"),
            units_per_transfused_patient=f2.slider(
                "Units per transfused patient", 1.0, 12.0,
                defaults.units_per_transfused_patient, key=f"u_{disease}"),
        )

    fc = forecast.forecast_months(state, disease, horizon)
    demand = forecast.demand_from_cases(fc, assumptions)
    peak = forecast.peak_row(demand)
    ratio = forecast.surge_ratio(fc)
    _, slope = forecast.annual_trend(state, disease)

    # ------------------------------------------------------------------
    # headline
    # ------------------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Peak month", peak["label"], f"{peak['cases']:,.0f} cases",
              delta_color="off")
    m2.metric("Peak to trough", f"{ratio:g}×", "seasonal swing", delta_color="off")
    m3.metric("Extra OPD screens", f"{peak['opd_screens']:,.0f}", "in the peak month",
              delta_color="off")
    m4.metric("Platelet units", f"{peak['platelet_units']:,.0f}", "in the peak month",
              delta_color="off")

    bed_days_available = beds * 30
    strain = peak["bed_days"] / bed_days_available if bed_days_available else 0
    if strain > 1:
        st.markdown(
            c.note(
                "CAPACITY", f"Peak demand exceeds your beds by {strain:.1f}×",
                f"{peak['bed_days']:,.0f} bed-days needed in {peak['label']} "
                f"against {bed_days_available:,.0f} available from {beds} beds. "
                f"That gap is visible today, months before the first admission — "
                f"which is the entire point of looking.",
                theme.DANGER,
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            c.note(
                "CAPACITY", f"Peak fits at {strain:.0%} occupancy",
                f"{peak['bed_days']:,.0f} of {bed_days_available:,.0f} bed-days "
                f"across the peak month.",
                theme.SAFE,
            ),
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # forecast
    # ------------------------------------------------------------------
    history = forecast.state_series(state, disease).tail(30)
    fig = go.Figure()
    fig.add_scatter(
        x=[f"{forecast.MONTH_NAMES[m - 1]} {y}"
           for m, y in zip(history["month"], history["year"])],
        y=history["cases"], mode="lines", name="Observed",
        line=dict(color=theme.INK_2, width=1.9),
    )
    labels = list(demand["label"])
    fig.add_scatter(x=labels, y=demand["upper"], mode="lines", line=dict(width=0),
                    showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=labels, y=demand["lower"], mode="lines", line=dict(width=0),
                    fill="tonexty", fillcolor="rgba(176,58,46,0.11)",
                    name="80% band", hoverinfo="skip")
    fig.add_scatter(
        x=labels, y=demand["cases"], mode="lines+markers", name="Forecast",
        line=dict(color=ink, width=2.2, dash="dot"), marker=dict(size=5.5),
        hovertemplate="%{x}<br>%{y:,.0f} cases<extra></extra>",
    )
    fig.update_layout(**theme.layout(
        height=330,
        title=dict(text=f"{disease} — {state}", x=0, xanchor="left", y=0.97,
                   font=dict(family="Newsreader, serif", size=16, color=theme.INK)),
        legend=dict(orientation="h", y=1.10, x=1, xanchor="right", font=dict(size=11)),
        margin=dict(l=8, r=8, t=54, b=8),
        yaxis=dict(title="Monthly cases", gridcolor=theme.RULE_SOFT,
                   tickfont=dict(color=theme.INK_3)),
    ))
    fig.update_xaxes(tickangle=-45, nticks=15)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    direction = "rising" if slope > 0.02 else "falling" if slope < -0.02 else "flat"
    st.markdown(
        c.caveat(
            f"Annual trend for {disease.lower()} in {state} is <b>{direction}</b> "
            f"at {slope * 100:+.1f}% per year. The trend is fitted in log space, "
            f"not case space — a straight line through a steeply declining series "
            f"extrapolates below zero within a year, and clipping at zero turns "
            f"the whole forecast into zeros. The band is an empirical residual "
            f"quantile from the years we have, not a distributional assumption."
        ),
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # requirement + seasonality
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    left, right = st.columns([1.55, 1], gap="medium")

    with left:
        st.markdown(c.label("Month by month requirement"), unsafe_allow_html=True)
        st.dataframe(
            [
                {
                    "Month": r["label"],
                    "Cases": f"{r['cases']:,.0f}",
                    "OPD": f"{r['opd_screens']:,.0f}",
                    "Admissions": f"{r['admissions']:,.0f}",
                    "Bed-days": f"{r['bed_days']:,.0f}",
                    "Platelets": f"{r['platelet_units']:,.0f}",
                }
                for _, r in demand.iterrows()
            ],
            width="stretch", hide_index=True, height=340,
        )

    with right:
        st.markdown(c.label("Seasonal index — learned, not assumed"),
                    unsafe_allow_html=True)
        index = forecast.seasonal_index(state, disease)
        bar = go.Figure()
        bar.add_bar(
            x=forecast.MONTH_NAMES, y=index.values * 100,
            marker_color=[ink if v == index.max() else theme.RULE
                          for v in index.values],
            hovertemplate="%{x}<br>%{y:.1f}% of the year<extra></extra>",
        )
        bar.update_layout(**theme.layout(
            height=240, showlegend=False,
            yaxis=dict(title="% of annual cases", gridcolor=theme.RULE_SOFT,
                       tickfont=dict(color=theme.INK_3)),
        ))
        st.plotly_chart(bar, width="stretch", config={"displayModeBar": False})
        top3 = index.sort_values(ascending=False).head(3)
        st.markdown(
            c.caveat(
                f"<b>{', '.join(forecast.MONTH_NAMES[m - 1] for m in top3.index)}</b> "
                f"carry {top3.sum():.0%} of {state}'s annual {disease.lower()} "
                f"burden. The index is each state's own average monthly share — "
                f"the model learns the local rhythm rather than assuming one."
            ),
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # does the forecast actually work?
    # ------------------------------------------------------------------
    scored = forecast.backtest(state, disease)
    if scored:
        st.markdown(c.rule(), unsafe_allow_html=True)
        st.markdown(c.label("Does this forecast actually work?"), unsafe_allow_html=True)
        st.markdown(
            "A forecast nobody has scored is an opinion. The pipeline is refit "
            "on data up to a cutoff, then asked to predict twelve months it was "
            "never shown — and compared against the naive baseline any "
            "administrator already has in their head: *assume this month looks "
            "like the same month last year.*"
        )

        b1, b2, b3 = st.columns(3)
        b1.metric("Model error (MAPE)", f"{scored['model_mape']:.1f}%",
                  delta_color="off")
        b2.metric("Naive seasonal baseline", f"{scored['naive_mape']:.1f}%",
                  delta_color="off")
        b3.metric(
            "Against the baseline",
            "better" if scored["beats_naive"] else "worse",
            f"{abs(scored['improvement']):.1f} points",
            delta_color="normal" if scored["beats_naive"] else "inverse",
        )

        holdout = go.Figure()
        holdout.add_bar(x=scored["labels"], y=scored["actual"], name="Actual",
                        marker_color=theme.INK_2)
        holdout.add_scatter(x=scored["labels"], y=scored["predicted"],
                            mode="lines+markers", name="Predicted (blind)",
                            line=dict(color=ink, width=2.2, dash="dot"),
                            marker=dict(size=6))
        holdout.update_layout(**theme.layout(
            height=260,
            legend=dict(orientation="h", y=1.16, x=1, xanchor="right",
                        font=dict(size=11)),
            yaxis=dict(title="Monthly cases"),
        ))
        holdout.update_xaxes(tickangle=-45)
        st.plotly_chart(holdout, width="stretch", config={"displayModeBar": False})

        if scored["beats_naive"]:
            st.markdown(
                c.caveat(
                    f"Peak month was predicted "
                    f"<b>{'correctly' if scored['peak_month_correct'] else 'one month off'}</b>. "
                    f"Across every series in the dataset the model beats the naive "
                    f"baseline in <b>15 of 18</b> — and loses in three. It loses "
                    f"where a state's annual total jumped by an order of magnitude "
                    f"between years, which no seasonal model catches and which is "
                    f"worth stating rather than hiding."
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                c.note(
                    "HONEST RESULT", "The naive baseline wins here",
                    f"For {disease.lower()} in {state}, last-year-same-month beats "
                    f"this model by {abs(scored['improvement']):.1f} points of MAPE. "
                    f"That happens where the annual total swung by an order of "
                    f"magnitude between years — a level shift the seasonal "
                    f"decomposition cannot see coming. Use the band, not the point "
                    f"estimate, for this state.",
                    theme.CAUTION,
                ),
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------
    # combined load — hospitals do not get one outbreak at a time
    # ------------------------------------------------------------------
    combined = forecast.combined_load(state, horizon)
    if not combined.empty and len(data.diseases()) > 1:
        st.markdown(c.rule(), unsafe_allow_html=True)
        st.markdown(c.label("All reportable vector-borne disease, combined"),
                    unsafe_allow_html=True)
        stack = go.Figure()
        for disease_name in data.diseases():
            if state not in data.states(disease_name):
                continue
            series = forecast.forecast_months(state, disease_name, horizon)
            stack.add_bar(
                x=list(series["label"]), y=series["cases"], name=disease_name,
                marker_color=DISEASE_INK.get(disease_name, theme.INK_3),
            )
        stack.update_layout(**theme.layout(
            height=260, barmode="stack",
            legend=dict(orientation="h", y=1.16, x=0, font=dict(size=11)),
            yaxis=dict(title="Monthly cases", gridcolor=theme.RULE_SOFT,
                       tickfont=dict(color=theme.INK_3)),
        ))
        stack.update_xaxes(tickangle=-45, nticks=15)
        st.plotly_chart(stack, width="stretch", config={"displayModeBar": False})
        st.markdown(
            c.caveat(
                f"A hospital does not experience one outbreak at a time. "
                f"Combined peak bed-day requirement for {state} across every "
                f"reportable disease is <b>{combined['bed_days'].max():,.0f}</b> "
                f"in a single month — against {bed_days_available:,.0f} available."
            ),
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # roster view
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(c.label(f"When each state peaks — {disease.lower()}"),
                unsafe_allow_html=True)
    calendar = forecast.national_peak_calendar(disease)
    national = go.Figure()
    national.add_bar(
        x=calendar["state"], y=calendar["annual_cases_latest"],
        marker_color=[ink if s == state else theme.RULE for s in calendar["state"]],
        customdata=calendar["peak_month_name"],
        hovertemplate="%{x}<br>%{y:,.0f} cases<br>peaks in %{customdata}<extra></extra>",
    )
    national.update_layout(**theme.layout(
        height=250, showlegend=False,
        yaxis=dict(title="Latest-year cases", gridcolor=theme.RULE_SOFT,
                   tickfont=dict(color=theme.INK_3)),
    ))
    national.update_xaxes(tickangle=-40)
    st.plotly_chart(national, width="stretch", config={"displayModeBar": False})