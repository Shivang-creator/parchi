"""Parchi — the two-minute Indian consult, instrumented.

A prescription cockpit. Four questions get answered at the moment the drug is
chosen, from the patient's own body parameters and India's own resistance,
price and safety data:

    will it work here   ·   is this the right dose for this body
    is the course the right length   ·   can the patient pay for it

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
from ui import consult, culture, escalate, surge, theme  # noqa: E402

st.markdown(theme.CSS, unsafe_allow_html=True)

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

tab_consult, tab_culture, tab_surge, tab_escalate, tab_method = st.tabs(
    ["Consult", "Day 3 · Culture", "Surge", "Escalation", "Method"]
)

with tab_consult:
    consult.render()

with tab_culture:
    culture.render()

with tab_surge:
    surge.render()

with tab_escalate:
    escalate.render()

with tab_method:
    # ----------------------------------------------------------------------
    # Bring your own antibiogram
    # ----------------------------------------------------------------------
    st.markdown(c.label("Use your own hospital's antibiogram"), unsafe_allow_html=True)
    st.markdown(
        "National surveillance is a fallback. A hospital's own antibiogram beats "
        "it every time — it is the same organisms, in the same building, under "
        "the same prescribing pressure. Upload one and every screen in Parchi "
        "re-bases on it immediately."
    )

    up1, up2 = st.columns([2, 1])
    with up1:
        uploaded = st.file_uploader(
            "CSV with columns: organism, antibiotic, setting, year, percent_susceptible",
            type=["csv"], label_visibility="collapsed",
        )
        if uploaded is not None:
            try:
                frame = pd.read_csv(uploaded, comment="#")
            except Exception as exc:                      # noqa: BLE001
                st.error(f"Could not read that file: {exc}")
            else:
                ok, message = data.load_antibiogram(frame)
                (st.success if ok else st.error)(message)

    with up2:
        if data.using_custom_antibiogram():
            st.markdown(c.stamp("CUSTOM ANTIBIOGRAM ACTIVE", theme.SAFE),
                        unsafe_allow_html=True)
            if st.button("Revert to national data", width="stretch"):
                data.clear_antibiogram()
                st.rerun()
        else:
            st.markdown(c.stamp("NATIONAL PATTERN", theme.INK_3),
                        unsafe_allow_html=True)

        template = data.susceptibility().head(200).to_csv(index=False)
        st.download_button(
            "Download a template", template, "antibiogram_template.csv",
            "text/csv", width="stretch",
        )

    st.markdown(c.rule(), unsafe_allow_html=True)

    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown(
            f"""
### What this is

Parchi sits at the single moment where Indian clinical medicine, drug
resistance and household finance all collide: a doctor with about two minutes
deciding what to write on a prescription slip.

It never prescribes. It drafts, shows its full working, and waits.

### The engines

**`coverage.py` — will this drug actually work?**

$$P(\\text{{cover}}) = \\sum_{{\\text{{organism}}}} P(\\text{{organism}} \\mid \\text{{site, setting}}) \\times P(\\text{{susceptible}} \\mid \\text{{organism, drug, setting, year}})$$

Combinations are scored organism-by-organism, taking the maximum susceptibility
across agents — **not** as `1 − Π(1 − pᵢ)`, which would assume the agents fail
independently. They do not: two carbapenems fail on the same carbapenemase.

**`dosing.py` — is this the right dose for this body?** Cockcroft-Gault
creatinine clearance from age, sex, weight and serum creatinine, then per-drug
renal bands. Contraindicated agents are removed *before* ranking. Course length
is checked against evidence-based durations, because the commonest overuse in
Indian prescribing is not the wrong drug, it is too many days of the right one.

**`safety.py` — is this combination legal and safe?** CDSCO's banned and
irrational fixed-dose combinations, plus interaction matching that expands drug
classes to their member molecules, so a chart saying "sertraline" still matches
a table saying "SSRI". Major-only by default: an alert that always fires is an
alert nobody reads.

**`forecast.py` — what is coming in three weeks?** Multiplicative seasonal
decomposition — a per-state seasonal index learned from observed monthly
shares, times an annual trend fitted **in log space**. Uncertainty is an
empirical residual quantile, not a distributional assumption.

**`geo.py` — if this patient needs more than we have, how far is help?**
Golden-hour reachability by *capability*, from a live OpenStreetMap extract.

### Decisions worth defending

**The recommendation is the narrowest adequate drug, never the strongest.**
Ranking by coverage alone recommends colistin for an outpatient cystitis — an
actual bug during development, and exactly how last-line agents get burned
through in the real world. Parchi sets an absolute adequacy bar per setting,
following the IDSA rule that empiric therapy should exceed ~80% local
susceptibility, then picks the *least* aggressive agent clearing it.

**Risk factors compound with a decaying exponent, not naively.** A ventilated
ICU patient has by definition had recent antibiotics and a central line.
Multiplying all three at full strength double-counts one exposure. The penalty
is damped further in ICU, because the ICU susceptibility data was already
measured on precisely those patients.

**Absent drug–organism pairs mean zero cover, deliberately.** Vancomycin cannot
touch gram-negatives. Colistin cannot touch gram-positives. Cephalosporins have
no enterococcal activity. Atypical pneumonia pathogens have no cell wall, so
every beta-lactam fails against them — which is exactly why a beta-lactam alone
under-covers community pneumonia in the combination panel. Those holes are the
model working.

**Overrides are counted and displayed.** A tool rejected most of the time is
wrong about that population and should be retuned, not trusted harder.
            """
        )

    with right:
        st.markdown(c.label("Data layer"), unsafe_allow_html=True)
        st.dataframe(
            [
                {"Table": "Susceptibility", "Rows": f"{len(data.susceptibility()):,}"},
                {"Table": "Formulary", "Rows": f"{len(data.drugs()):,}"},
                {"Table": "Organism priors", "Rows": f"{len(data.priors()):,}"},
                {"Table": "Renal bands", "Rows": f"{len(data.renal_rules()):,}"},
                {"Table": "Banned FDCs", "Rows": f"{len(data.fdc_flags()):,}"},
                {"Table": "Interactions", "Rows": f"{len(data.interactions()):,}"},
                {"Table": "Durations", "Rows": f"{len(data.durations()):,}"},
                {"Table": "Disease burden", "Rows": f"{len(data.burden()):,}"},
            ],
            width="stretch", hide_index=True,
        )
        st.markdown(
            f"""
<div style="font-size:12.5px;color:{theme.INK_2};line-height:1.65;padding-top:14px">
<b>{len(data.antibiotic_names())}</b> antibiotics ·
<b>{len(data.organisms())}</b> organisms ·
<b>{len(data.infection_sites())}</b> infection sites ·
<b>{len(data.diseases())}</b> vector-borne diseases across
<b>{len(data.states())}</b> states
</div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(c.rule(soft=True), unsafe_allow_html=True)
        st.markdown(c.label("Provenance"), unsafe_allow_html=True)
        st.markdown(
            f"""
<div style="font-size:12.5px;color:{theme.INK_2};line-height:1.7">
Every curated figure is <b style="color:{theme.RX}">indicative</b>, compiled
from published patterns in the ICMR Antimicrobial Resistance Surveillance
Network reports, WHO GLASS, CDSCO's prohibited fixed-dose-combination lists,
NPPA ceiling-price structures and NCVBDC vector-borne disease reporting.
<br><br>
Susceptibility series are anchored at an earlier and a recent endpoint with
intermediate years reconstructed — the <b>direction and magnitude</b> of each
trend are real; the individual year points are not observations.
<br><br>
<code>data/facilities.csv</code> is the exception: a <b>live OpenStreetMap
extract</b>. Facility locations are real. Capability is inferred from tier
under Indian Public Health Standards, and only for public facilities —
OpenStreetMap tags a one-doctor nursing home and a 900-bed tertiary centre
identically, so crediting every private hospital with an ICU would be fiction.
Open data can describe India's public health system; it cannot describe the
private one.
<br><br>
<code>build_data.py</code> is the single source of every curated number.
</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='padding-top:16px'>{c.stamp('NOT A CLINICAL DEVICE', theme.RX)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:12px;color:{theme.INK_3};letter-spacing:0.04em'>"
        "Python · pandas · NumPy · SciPy · Streamlit · Plotly · OpenStreetMap "
        "Overpass. No API keys, no model server, no network calls at runtime — "
        "the whole thing runs offline on a laptop, which is the point for a "
        "clinic with intermittent connectivity."
        "</div>",
        unsafe_allow_html=True,
    )
