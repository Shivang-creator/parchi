"""The escalation screen — when this clinic is not enough.

The last question of a consult is the one Parchi cannot answer with a drug:
this patient needs more than I have. Where do I send them, and will they
survive the journey?
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import geo

from . import components as c
from . import theme

TIER_COLOR = {
    "Medical College": theme.SAFE,
    "District Hospital": theme.STAMP,
    "Private Multispeciality": theme.RESERVE,
    "CHC": theme.CAUTION,
    "PHC": theme.INK_3,
    "Private Clinic / Nursing home": theme.RULE,
    "Sub-centre": theme.RULE,
    "Clinic": theme.RULE,
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

    # A referral starts at a small PUBLIC facility — that is the whole scenario.
    # Sorting the raw list put private paediatric clinics at the top, which made
    # the default a children's clinic receiving a heart attack.
    area_rows = frame[frame["anchor"] == origin_area]
    referrers = area_rows[area_rows["tier"].isin(["PHC", "CHC", "Sub-centre"])]
    if referrers.empty:
        referrers = area_rows
    origin_name = c3.selectbox(
        "Referring facility",
        list(referrers.sort_values(["tier_rank", "name"])["name"].head(40)),
    )
    origin = referrers[referrers["name"] == origin_name].iloc[0]

    spec = geo.EMERGENCIES[emergency]
    result = geo.assess(
        float(origin["latitude"]), float(origin["longitude"]), emergency,
        exclude_name=origin["name"],
    )

    st.markdown(c.caveat(spec["note"]), unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    m1, m2, m3 = st.columns(3)
    m1.metric("Clock", f"{spec['window_min']} min", spec["capability"],
              delta_color="off")
    m2.metric("Nearest facility", f"{result.minutes_to_any:.0f} min",
              result.nearest_any["tier"], delta_color="off")
    if result.nearest_capable is not None:
        m3.metric(
            "Nearest that can treat it",
            f"{result.minutes_to_capable:.0f} min",
            f"{result.minutes_to_capable - result.minutes_to_any:+.0f} min further",
            delta_color="inverse",
        )
    else:
        m3.metric("Nearest that can treat it", "none", "not in this extract",
                  delta_color="off")

    if result.reachable:
        st.markdown(c.note(
            "REACHABLE", f"{result.nearest_capable['name']} — "
            f"{result.minutes_to_capable:.0f} minutes",
            f"A {result.nearest_capable['tier'].lower()}, inside the "
            f"{spec['window_min']}-minute window. Send <b>directly</b> — do not "
            f"route through a facility that cannot provide "
            f"{spec['capability'].lower()}.",
            theme.SAFE), unsafe_allow_html=True)
    elif result.nearest_capable is not None:
        over = result.minutes_to_capable - spec["window_min"]
        st.markdown(c.note(
            "OUTSIDE THE WINDOW",
            f"{over:.0f} minutes past the limit",
            f"The nearest facility able to provide {spec['capability'].lower()} "
            f"is <b>{result.nearest_capable['name']}</b>, about "
            f"{result.minutes_to_capable:.0f} minutes away, against a "
            f"{spec['window_min']}-minute window. For this emergency at this "
            f"location, geography <i>is</i> the clinical problem. Stabilise, "
            f"call ahead, and start the transfer now.",
            theme.DANGER), unsafe_allow_html=True)
    else:
        st.markdown(c.note(
            "NO CAPABILITY", f"Nothing in range provides {spec['capability'].lower()}",
            "No facility in this extract carries that capability at any distance.",
            theme.DANGER), unsafe_allow_html=True)

    if result.wasted_minutes > 0 and result.nearest_capable is not None:
        st.markdown(c.note(
            "ROUTING", "Do not stop at the nearest facility first",
            f"The closest facility is <b>{result.nearest_any['name']}</b> "
            f"({result.nearest_any['tier']}), {result.minutes_to_any:.0f} minutes "
            f"away — and it cannot provide {spec['capability'].lower()}. Taking "
            f"the patient there and re-referring costs roughly "
            f"<b>{result.wasted_minutes:.0f} extra minutes</b> of a "
            f"{spec['window_min']}-minute window. This is the commonest "
            f"avoidable delay in Indian emergency referral.",
            theme.CAUTION), unsafe_allow_html=True)

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
            marker=dict(size=9, color=TIER_COLOR.get(tier, theme.INK_3)),
            text=group["name"],
            customdata=group[["tier", "minutes"]],
            hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>"
                          "%{customdata[1]:.0f} min away<extra></extra>",
        )
    fig.add_scattermap(
        lat=[origin["latitude"]], lon=[origin["longitude"]], mode="markers",
        name="Referring from",
        marker=dict(size=15, color=theme.RX),
        text=[origin["name"]], hovertemplate="<b>%{text}</b><extra></extra>",
    )
    if result.nearest_capable is not None:
        fig.add_scattermap(
            lat=[origin["latitude"], result.nearest_capable["latitude"]],
            lon=[origin["longitude"], result.nearest_capable["longitude"]],
            mode="lines", name="Referral route",
            line=dict(width=2.5, color=theme.SAFE),
            hoverinfo="skip",
        )

    fig.update_layout(
        map=dict(
            style="carto-positron",
            center=dict(lat=float(origin["latitude"]), lon=float(origin["longitude"])),
            zoom=8.2,
        ),
        height=460,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=theme.INK_2, size=11.5),
        legend=dict(orientation="h", y=-0.04, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ------------------------------------------------------------------
    # Full profile of this location
    # ------------------------------------------------------------------
    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(c.label("Every emergency, scored from this location"),
                unsafe_allow_html=True)
    profile = geo.coverage_by_emergency(
        float(origin["latitude"]), float(origin["longitude"]), origin["name"]
    )
    st.dataframe(profile, width="stretch", hide_index=True)

    survivable = (profile["Survivable"] == "yes").sum()
    st.markdown(c.caveat(
        f"<b>{survivable} of {len(profile)}</b> emergency types are reachable in time "
        f"from {origin['name']}. Travel time assumes {geo.ROAD_SPEED_KMH:.0f} km/h "
        f"average road speed and a {geo.ROUTE_FACTOR:.2f}× detour over straight-line "
        f"distance — deliberately conservative, and still optimistic about a rural "
        f"ambulance at night. Facility locations are a live OpenStreetMap extract; "
        f"capability is inferred from the facility's tier under Indian Public "
        f"Health Standards, not from a per-facility audit."
    ), unsafe_allow_html=True)
