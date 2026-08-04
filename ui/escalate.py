"""The escalation screen — when this clinic is not enough.

The last question of a consult is the one Parchi cannot answer with a drug:
this patient needs more than I have. Where do I send them, and will they
survive the journey?
"""

from __future__ import annotations

import math

import plotly.graph_objects as go
import streamlit as st

from engine import geo

from . import theme

TIER_COLOR = {
    "Medical College": theme.GOOD,
    "District Hospital": theme.ACCENT,
    "Private Multispeciality": theme.RESERVE,
    "CHC": theme.WARN,
    "PHC": theme.MUTED,
    "Private Clinic / Nursing home": theme.LINE,
    "Sub-centre": theme.LINE,
    "Clinic": theme.LINE,
}


def render() -> None:
    if not geo.available():
        st.warning(
            "No facility data present. Run `python fetch_facilities.py` to pull a "
            "live OpenStreetMap extract, then reload this tab."
        )
        return

    frame = geo.facilities()

    c1, c2, c3 = st.columns([1.4, 1, 1])
    emergency = c1.selectbox("Presenting emergency", list(geo.EMERGENCIES))
    anchors = sorted(frame["anchor"].unique())
    origin_area = c2.selectbox("Referring from (area)", anchors)

    area_rows = frame[frame["anchor"] == origin_area]
    origin_name = c3.selectbox(
        "Referring facility",
        list(area_rows.sort_values("tier_rank")["name"].head(40)),
    )
    origin = area_rows[area_rows["name"] == origin_name].iloc[0]

    spec = geo.EMERGENCIES[emergency]
    result = geo.assess(
        float(origin["latitude"]), float(origin["longitude"]), emergency,
        exclude_name=origin["name"],
    )

    st.caption(spec["note"])

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Needs", spec["capability"])
    m2.metric("Clock", f"{spec['window_min']} min")
    m3.metric(
        "Nearest facility of any kind",
        f"{result.minutes_to_any:.0f} min",
        result.nearest_any["tier"],
    )
    if result.nearest_capable is not None:
        m4.metric(
            "Nearest that can treat it",
            f"{result.minutes_to_capable:.0f} min",
            f"+{result.minutes_to_capable - result.minutes_to_any:.0f} min further",
            delta_color="inverse",
        )
    else:
        m4.metric("Nearest that can treat it", "none", "not in dataset")

    if result.reachable:
        st.success(
            f"**Reachable in time.** {result.nearest_capable['name']} "
            f"({result.nearest_capable['tier']}) is about "
            f"{result.minutes_to_capable:.0f} minutes away, inside the "
            f"{spec['window_min']}-minute window. Send directly — do not route "
            f"through a facility that cannot provide {spec['capability'].lower()}."
        )
    elif result.nearest_capable is not None:
        over = result.minutes_to_capable - spec["window_min"]
        st.error(
            f"**Outside the window.** The nearest facility able to provide "
            f"{spec['capability'].lower()} is {result.nearest_capable['name']}, "
            f"about {result.minutes_to_capable:.0f} minutes away — "
            f"{over:.0f} minutes past the {spec['window_min']}-minute limit. "
            f"For this emergency, at this location, geography is the clinical "
            f"problem. Stabilise, call ahead, and start transfer immediately."
        )
    else:
        st.error(
            f"No facility in this dataset provides {spec['capability'].lower()}."
        )

    if result.wasted_minutes > 0 and result.nearest_capable is not None:
        st.markdown(
            f'<div class="alert" style="--c:{theme.WARN}">'
            f'<span class="pill" style="--c:{theme.WARN}">ROUTING</span>'
            f'<span class="t">Do not stop at the nearest facility first</span>'
            f'<div class="b">The closest facility is '
            f"<b>{result.nearest_any['name']}</b> ({result.nearest_any['tier']}), "
            f"{result.minutes_to_any:.0f} minutes away — and it cannot provide "
            f"{spec['capability'].lower()}. Taking the patient there and "
            f"re-referring costs roughly <b>{result.wasted_minutes:.0f} extra "
            f"minutes</b> of the {spec['window_min']}-minute window. This is the "
            f"commonest avoidable delay in Indian emergency referral."
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Map
    # ------------------------------------------------------------------
    nearby = geo.nearest_table(
        float(origin["latitude"]), float(origin["longitude"]), limit=250
    )
    fig = go.Figure()
    for tier, group in nearby.groupby("tier"):
        fig.add_scattermap(
            lat=group["latitude"], lon=group["longitude"], mode="markers",
            name=tier,
            marker=dict(size=9, color=TIER_COLOR.get(tier, theme.MUTED)),
            text=group["name"],
            customdata=group[["tier", "minutes"]],
            hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>"
                          "%{customdata[1]:.0f} min away<extra></extra>",
        )
    fig.add_scattermap(
        lat=[origin["latitude"]], lon=[origin["longitude"]], mode="markers",
        name="Referring from",
        marker=dict(size=16, color=theme.BAD),
        text=[origin["name"]], hovertemplate="<b>%{text}</b><extra></extra>",
    )
    if result.nearest_capable is not None:
        fig.add_scattermap(
            lat=[origin["latitude"], result.nearest_capable["latitude"]],
            lon=[origin["longitude"], result.nearest_capable["longitude"]],
            mode="lines", name="Referral route",
            line=dict(width=3, color=theme.GOOD),
            hoverinfo="skip",
        )

    fig.update_layout(
        map=dict(
            style="carto-darkmatter",
            center=dict(lat=float(origin["latitude"]), lon=float(origin["longitude"])),
            zoom=8.2,
        ),
        height=460,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=theme.TEXT, size=12),
        legend=dict(orientation="h", y=-0.04, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ------------------------------------------------------------------
    # Full profile of this location
    # ------------------------------------------------------------------
    st.markdown(
        '<div class="card-label">Every emergency, scored from this location</div>',
        unsafe_allow_html=True,
    )
    profile = geo.coverage_by_emergency(
        float(origin["latitude"]), float(origin["longitude"]), origin["name"]
    )
    st.dataframe(profile, width="stretch", hide_index=True)

    survivable = (profile["Survivable"] == "yes").sum()
    st.caption(
        f"**{survivable} of {len(profile)}** emergency types are reachable in time "
        f"from {origin['name']}. Travel time assumes {geo.ROAD_SPEED_KMH:.0f} km/h "
        f"average road speed and a {geo.ROUTE_FACTOR:.2f}× detour over straight-line "
        f"distance — deliberately conservative, and still optimistic about a rural "
        f"ambulance at night. Facility locations are a live OpenStreetMap extract; "
        f"capability is inferred from the facility's tier under Indian Public "
        f"Health Standards, not from a per-facility audit."
    )
