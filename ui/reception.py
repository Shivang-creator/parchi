"""The registration desk — where acuity is currently decided by arrival order.

An Indian OPD is a queue. Patients travel before dawn, arrive together, and
are seen in the order they reached the window, so the person having a heart
attack waits behind the person with a rash.

They do not need much to fix that. NEWS2 is six measurements and ninety
seconds, and it is what turns a queue into triage.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import data, triage

from . import components as c
from . import theme


def _news2_chart(result: triage.Triage) -> go.Figure:
    """Each parameter's contribution, so the score is never a bare number."""
    p = theme.palette()
    rows = [o for o in result.observations]
    labels = [o.parameter for o in rows]
    points = [o.points for o in rows]
    colours = [
        p.DANGER if o.points >= 3 else p.CAUTION if o.points >= 1 else p.SAFE
        for o in rows
    ]
    text = [
        f"{o.value}{(' ' + o.unit) if o.unit else ''}" for o in rows
    ]

    fig = go.Figure()
    fig.add_bar(
        y=labels, x=points, orientation="h", marker_color=colours,
        text=text, textposition="outside",
        textfont=dict(family="'IBM Plex Mono', monospace", size=11, color=p.INK_2),
        hovertemplate="%{y}<br>%{x} point(s)<extra></extra>",
    )
    fig.update_layout(**theme.layout(
        height=max(210, 30 * len(rows) + 60), showlegend=False, bargap=0.35,
        xaxis=dict(title="NEWS2 points", range=[0, 3.9], dtick=1),
    ))
    fig.update_yaxes(autorange="reversed", ticksuffix="  ")
    return fig


def _day_chart(projection, department: str) -> go.Figure:
    p = theme.palette()
    fig = go.Figure()
    fig.add_bar(x=projection["hour"], y=projection["arrivals"], name="Arriving",
                marker_color=p.STAMP, opacity=0.85)
    fig.add_scatter(x=projection["hour"], y=projection["capacity"], mode="lines",
                    name="Capacity", line=dict(color=p.INK_3, width=1.6, dash="dash"))
    fig.add_scatter(x=projection["hour"], y=projection["waiting"], mode="lines+markers",
                    name="Still waiting", line=dict(color=p.RX, width=2.4),
                    marker=dict(size=5.5))
    fig.update_layout(**theme.layout(
        height=300,
        title=theme.chart_title(f"{department} — one OPD day"),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=11)),
        margin=dict(l=8, r=8, t=52, b=8),
        yaxis=dict(title="Patients"),
    ))
    return fig


def render() -> None:
    p = theme.palette()

    st.markdown(
        "A patient walks up to the window. Right now the only thing that decides "
        "when they are seen is what time they got here. Six measurements and "
        "ninety seconds change that."
    )
    st.markdown(c.rule(soft=True), unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Vitals at the window
    # ------------------------------------------------------------------
    st.markdown(c.label("Vitals at the window"), unsafe_allow_html=True)
    v1, v2, v3, v4 = st.columns(4)
    resp = v1.number_input("Respiration /min", 4, 60, 28)
    spo2 = v2.number_input("SpO₂ %", 50, 100, 89)
    sbp = v3.number_input("Systolic BP", 50, 260, 88)
    pulse = v4.number_input("Pulse /min", 25, 220, 124)

    v5, v6, v7, v8 = st.columns(4)
    temp = v5.number_input("Temperature °C", 32.0, 43.0, 39.2, step=0.1)
    conscious = v6.selectbox("Consciousness", list(triage.CONSCIOUSNESS))
    on_oxygen = v7.checkbox("On supplemental oxygen", value=True)
    department = v8.selectbox("Department", list(data.departments()["department"]))

    result = triage.score(resp, spo2, sbp, pulse, temp, conscious, on_oxygen)
    band_colour = theme.risk_colors().get(result.band, p.INK_3)

    # ------------------------------------------------------------------
    # The verdict
    # ------------------------------------------------------------------
    left, right = st.columns([2.35, 1], gap="medium")

    with left:
        flags = (
            ", ".join(o.parameter.lower() for o in result.red_flags)
            if result.red_flags else "none"
        )
        st.markdown(
            c.slip(
                drug=f"Priority {result.priority} — {result.band.lower()}",
                sig=f"NEWS2 {result.score}   ·   review within "
                    f"{result.minutes_to_review} min   ·   {department}",
                who=f"<b>Registration desk</b> &nbsp;·&nbsp; National Early Warning "
                    f"Score 2 &nbsp;·&nbsp; six parameters",
                why=result.response,
                accent=band_colour,
                marks=[
                    ("Parameters scoring 3", flags),
                    ("Total", f"{result.score} points"),
                    ("Instrument", "NEWS2 (RCP, validated)"),
                ],
            ),
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            c.verdict(
                min(result.score / 20 * 100, 100),
                f"NEWS2 <b>{result.score}</b><br>"
                f"<span style='color:var(--ink-3)'>{result.band} risk · "
                f"seen within {result.minutes_to_review} min</span>",
                band_colour,
            ).replace(f"{min(result.score / 20 * 100, 100):.0f}<span class=\"pct\">%</span>",
                      f"{result.score}<span class=\"pct\"> pts</span>")
             .replace("Expected coverage", "Early warning score"),
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Where they land in the queue
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    q1, q2 = st.columns([1, 1.6], gap="medium")

    with q1:
        st.markdown(c.label("Today's waiting room"), unsafe_allow_html=True)
        size = st.slider("Patients currently waiting", 10, 200, 60, key="queue_size")
        queue = triage.synthetic_queue(size)
        dept_queue = queue[queue["department"] == department]

        arrival_position = len(dept_queue)
        triage_position = triage.triage_adjusted_position(result.priority, dept_queue)

        wait_by_arrival = triage.expected_wait_minutes(department, arrival_position)
        wait_by_triage = triage.expected_wait_minutes(department, triage_position)

        st.markdown(
            c.meter("Seen by arrival order", wait_by_arrival, max(wait_by_arrival, 1),
                    p.INK_3, f"{wait_by_arrival:.0f} min",
                    f"{arrival_position} people ahead"),
            unsafe_allow_html=True,
        )
        st.markdown(
            c.meter("Seen by acuity", wait_by_triage, max(wait_by_arrival, 1),
                    band_colour, f"{wait_by_triage:.0f} min",
                    f"{triage_position} people of higher acuity ahead"),
            unsafe_allow_html=True,
        )
        saved = wait_by_arrival - wait_by_triage
        if saved > 1:
            st.markdown(
                c.note("TRIAGE", f"{saved:.0f} minutes earlier",
                       f"Sorting this queue by acuity instead of arrival time moves "
                       f"this patient forward by {arrival_position - triage_position} "
                       f"places. Nothing was bought, hired or built to do that.",
                       theme.SAFE),
                unsafe_allow_html=True,
            )

    with q2:
        st.markdown(c.label("Why the score is what it is"), unsafe_allow_html=True)
        st.plotly_chart(_news2_chart(result), width="stretch",
                        config={"displayModeBar": False})
        st.markdown(
            c.caveat(
                "NEWS2 escalates on <b>any single parameter scoring 3</b>, whatever "
                "the total. That rule is the part people get wrong: a patient can "
                "total 3 and still need urgent review, because one system being "
                "that deranged means something is badly wrong on its own."
            ),
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # The day
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(c.label("The crush is predictable the day before"),
                unsafe_allow_html=True)

    d1, d2 = st.columns([1.7, 1], gap="medium")
    with d2:
        arrivals = st.number_input("Expected OPD arrivals today", 100, 3000, 900,
                                   step=50)
        target = st.slider("Acceptable worst wait (min)", 15, 180, 60)
        projection = triage.day_projection(int(arrivals), department)
        worst = projection["wait_minutes"].max()
        worst_hour = projection.loc[projection["wait_minutes"].idxmax(), "hour"]
        needed = triage.staffing_to_clear(int(arrivals), department, target)
        current = int(
            data.departments()
            .set_index("department")
            .loc[department, "doctors"]
        )

        st.metric("Worst wait today", f"{worst:.0f} min", f"at {worst_hour}",
                  delta_color="off")
        st.metric("Doctors to hold the target", needed,
                  f"{needed - current:+d} vs the {current} rostered",
                  delta_color="inverse" if needed > current else "normal")

        if needed > current:
            st.markdown(
                c.note("ROSTER", f"{needed - current} more doctor(s) in {department}",
                       f"Demand is front-loaded into the 8–11am window because "
                       f"patients travel at dawn and arrive together. Capacity is "
                       f"flat across the day. That mismatch is what the queue is — "
                       f"and it is visible the evening before.",
                       theme.CAUTION),
                unsafe_allow_html=True,
            )

    with d1:
        st.plotly_chart(_day_chart(projection, department), width="stretch",
                        config={"displayModeBar": False})

    # ------------------------------------------------------------------
    # The room, sorted
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(c.label("The waiting room, sorted by acuity instead of arrival"),
                unsafe_allow_html=True)

    sorted_queue = queue.sort_values(["priority", "arrived"]).head(14)
    moved = int((sorted_queue["arrived"].to_numpy()
                 > list(range(len(sorted_queue)))).sum())
    st.dataframe(
        [
            {
                "Token": int(r["token"]),
                "Arrived": f"{int(r['arrived']) + 1}th",
                "Now seen": f"{i + 1}",
                "Department": r["department"],
                "Age": int(r["age"]),
                "NEWS2": int(r["news2"]),
                "Priority": int(r["priority"]),
                "Band": r["band"],
            }
            for i, (_, r) in enumerate(sorted_queue.iterrows())
        ],
        width="stretch", hide_index=True, height=min(520, 38 * len(sorted_queue) + 40),
    )
    st.markdown(
        c.caveat(
            f"Of the first fourteen now called, <b>{moved}</b> arrived later than "
            f"someone they are now seen before. Vitals here are simulated to "
            f"demonstrate the sort — the scoring instrument and the queue model "
            f"are real, and would run identically on a desk's own readings."
        ),
        unsafe_allow_html=True,
    )
