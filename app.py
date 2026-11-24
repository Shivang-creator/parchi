"""Parchi — the two-minute Indian consult, instrumented.

Not five tools. One patient's walk through a building:

    Reception   six measurements turn a queue into triage
    Doctor      the prescription, and the four questions nobody has time for
    Pharmacy    what the slip actually costs, against what this family earns
    Hospital    what is coming in three weeks, and where to send who you cannot treat

Parchi drafts. The clinician decides.

Run:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Parchi — prescription intelligence for Indian clinics",
    page_icon="℞",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd  # noqa: E402

from engine import data  # noqa: E402
from ui import components as c  # noqa: E402
from ui import (  # noqa: E402
    consult, culture, escalate, method, pharmacy, reception, surge, theme,
)

# --------------------------------------------------------------------------
# The journey
# --------------------------------------------------------------------------
STOPS = [
    ("reception", "reception", "Reception", "triage the queue"),
    ("doctor", "doctor", "Doctor", "choose the drug"),
    ("pharmacy", "pharmacy", "Pharmacy", "price the slip"),
    ("hospital", "hospital", "Hospital", "what is coming"),
    ("method", "method", "Method", "data and model"),
]

st.session_state.setdefault("stop", "doctor")

# The server process is shared by every visitor. Point the engines at THIS
# session's antibiogram (or the national panel) before anything reads it.
data.use_antibiogram(st.session_state.get("antibiogram"))
st.session_state.setdefault("theme_name", "Paper")

# CSS first: every screen below reads colours from the active palette.
st.markdown(theme.css(), unsafe_allow_html=True)

palette = theme.palette()

other = "Ink" if st.session_state["theme_name"] == "Paper" else "Paper"

st.markdown(
    c.masthead(
        standfirst="A prescription is a bet placed blind. This one shows its odds.",
        left="Antimicrobial stewardship · India",
        right=(
            "Hospital antibiogram loaded"
            if data.using_custom_antibiogram()
            else "ICMR-AMRSN pattern · indicative data"
        ),
    ),
    unsafe_allow_html=True,
)

# The palette switch sits with the masthead, not in the journey rail — it is a
# preference about the room's lighting, not a stop on the patient's walk.
_, toggle = st.columns([6, 1])
with toggle:
    if st.button(f"{other} theme", key="theme_toggle", width="stretch"):
        st.session_state["theme_name"] = other
        st.rerun()

# --------------------------------------------------------------------------
# Navigation. The buttons ARE the rail — icon, title and subtitle are painted
# on in CSS (see theme._nav_css), because a Streamlit button label is plain
# text and a separate decorative rail would be duplicated navigation.
# --------------------------------------------------------------------------
with st.container(key="railnav"):
    nav = st.columns(len(STOPS))
    for column, (key, _, title, _) in zip(nav, STOPS):
        if column.button(
            title, key=f"nav_{key}", width="stretch",
            type="primary" if st.session_state["stop"] == key else "secondary",
        ):
            st.session_state["stop"] = key
            st.rerun()

# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------
stop = st.session_state["stop"]

if stop == "reception":
    reception.render()

elif stop == "doctor":
    tab_consult, tab_culture = st.tabs(["The consult", "Day 3 · culture"])
    with tab_consult:
        consult.render()
    with tab_culture:
        culture.render()

elif stop == "pharmacy":
    pharmacy.render()

elif stop == "hospital":
    tab_surge, tab_escalate = st.tabs(["Surge forecast", "Escalation"])
    with tab_surge:
        surge.render()
    with tab_escalate:
        escalate.render()

elif stop == "method":
    method.render(pd)
