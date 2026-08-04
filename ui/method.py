"""Method — what the numbers are, where they came from, and what they are not.

Kept as its own screen rather than a footnote because provenance is not a
disclaimer here; it is part of the argument. A tool that will not say how
confident it is has no business advising on antibiotics.
"""

from __future__ import annotations

import streamlit as st

from engine import data

from . import components as c
from . import theme


def render(pd) -> None:
    p = theme.palette()

    # ------------------------------------------------------------------
    # Bring your own antibiogram
    # ------------------------------------------------------------------
    st.markdown(c.label("Use your own hospital's antibiogram"), unsafe_allow_html=True)
    st.markdown(
        "National surveillance is a fallback. A hospital's own antibiogram beats "
        "it every time — same organisms, same building, same prescribing "
        "pressure. Upload one and every screen re-bases on it immediately."
    )

    up1, up2 = st.columns([2, 1])
    with up1:
        uploaded = st.file_uploader(
            "CSV: organism, antibiotic, setting, year, percent_susceptible",
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
            st.markdown(c.stamp("CUSTOM ANTIBIOGRAM ACTIVE", p.SAFE),
                        unsafe_allow_html=True)
            if st.button("Revert to national data", width="stretch"):
                data.clear_antibiogram()
                st.rerun()
        else:
            st.markdown(c.stamp("NATIONAL PATTERN", p.INK_3), unsafe_allow_html=True)

        st.download_button(
            "Download a template",
            data.susceptibility().head(200).to_csv(index=False),
            "antibiogram_template.csv", "text/csv", width="stretch",
        )

    st.markdown(c.rule(), unsafe_allow_html=True)

    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown(
            r"""
### What this is

Parchi follows one patient through a building. Reception decides *when* they
are seen, the doctor decides *what* they are given, the pharmacy decides
whether they can actually take it — and the hospital-level screens decide
whether the building was ready for them at all.

It never prescribes. It drafts, shows its full working, and waits.

### The engines

**`triage.py` — who should be seen first?** NEWS2, the National Early Warning
Score 2: six measured parameters plus consciousness, each banded and summed,
with the single-parameter escalation rule that most implementations get wrong.
Then a deterministic queue model — arrivals against per-department throughput —
which turns a wait into a roster decision.

**`coverage.py` — will this drug actually work?**

$$P(\text{cover}) = \sum_{\text{organism}} P(\text{organism} \mid \text{site, setting}) \times P(\text{susceptible} \mid \text{organism, drug, setting, year})$$

Combinations are scored organism-by-organism, taking the maximum susceptibility
across agents — **not** as $1 - \prod_i (1 - p_i)$, which assumes the agents
fail independently. They do not: two carbapenems fail on the same
carbapenemase.

**`dosing.py` — is this right for this body?** Cockcroft-Gault creatinine
clearance, then per-drug renal bands. Contraindicated agents are removed
*before* ranking. Course length is checked against evidence-based durations.

**`safety.py` — is it legal and safe?** CDSCO's banned fixed-dose combinations
plus interaction matching that expands drug classes to their member molecules,
so a chart saying "sertraline" matches a table saying "SSRI". Major-only by
default: an alert that always fires is an alert nobody reads.

**`pharmacy.py` — can they pay for it?** Substitution across brand, generic and
Jan Aushadhi tiers, priced in **days of that household's income** rather than
rupees — because ₹1,400 is a routine expense for one family and five days of
earnings for another, and only the second one gets abandoned half-way.

**`forecast.py` — what is coming in three weeks?** Multiplicative seasonal
decomposition: a per-state seasonal index learned from observed monthly shares,
times an annual trend fitted in log space. Backtested against a naive seasonal
baseline, and it reports the series where it loses.

**`geo.py` — how far is help?** Golden-hour reachability by *capability*, from
a live OpenStreetMap extract.

### Decisions worth defending

**The recommendation is the narrowest adequate drug, never the strongest.**
Ranking by coverage alone recommends colistin for an outpatient cystitis — an
actual bug during development, and exactly how last-line agents get burned
through. Parchi sets an absolute adequacy bar per setting, following the IDSA
rule that empiric therapy should exceed ~80% local susceptibility, then picks
the *least* aggressive agent clearing it.

**Risk factors compound with a decaying exponent.** A ventilated ICU patient
has by definition had recent antibiotics and a central line; multiplying all
three at full strength double-counts one exposure. The penalty is damped
further in ICU, because that data was already measured on those patients.

**Absent drug–organism pairs mean zero cover, deliberately.** Vancomycin cannot
touch gram-negatives. Colistin cannot touch gram-positives. Cephalosporins have
no enterococcal activity. Atypical pneumonia pathogens have no cell wall, so
every beta-lactam fails against them — which is why a beta-lactam alone
under-covers community pneumonia in the combination panel. Those holes are the
model working.

**Overrides are counted and displayed.** A tool rejected most of the time is
wrong about that population and should be retuned, not trusted harder.

**Supply is treated as a stewardship variable.** A prescriber who cannot get
nitrofurantoin writes a fluoroquinolone, so the pharmacy screen shows which
shelves are emptying and flags when the *narrow* agents are the ones running
out.
            """
        )

    with right:
        st.markdown(c.label("Data layer"), unsafe_allow_html=True)
        tables = [
            ("Susceptibility", data.susceptibility()),
            ("Formulary", data.drugs()),
            ("Organism priors", data.priors()),
            ("Renal bands", data.renal_rules()),
            ("Banned FDCs", data.fdc_flags()),
            ("Interactions", data.interactions()),
            ("Durations", data.durations()),
            ("NEWS2 bands", data.news2_bands()),
            ("Departments", data.departments()),
            ("Counselling", data.counselling()),
            ("Pregnancy safety", data.pregnancy()),
            ("Pharmacy stock", data.stock()),
            ("Disease burden", data.burden()),
        ]
        st.dataframe(
            [{"Table": name, "Rows": f"{len(frame):,}"} for name, frame in tables],
            width="stretch", hide_index=True, height=490,
        )
        st.markdown(
            f"""
<div style="font-size:12.5px;color:{p.INK_2};line-height:1.7;padding-top:12px">
<b>{len(data.antibiotic_names())}</b> antibiotics ·
<b>{len(data.organisms())}</b> organisms ·
<b>{len(data.infection_sites())}</b> infection sites ·
<b>{len(data.departments())}</b> OPD departments ·
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
<div style="font-size:12.5px;color:{p.INK_2};line-height:1.72">
Every curated figure is <b style="color:{p.RX}">indicative</b>, compiled from
published patterns in the ICMR Antimicrobial Resistance Surveillance Network
reports, WHO GLASS, CDSCO's prohibited fixed-dose-combination lists, NPPA
ceiling-price structures and NCVBDC vector-borne disease reporting.
<br><br>
Susceptibility series are anchored at an earlier and a recent endpoint with
intermediate years reconstructed — the <b>direction and magnitude</b> of each
trend are real; the individual year points are not observations.
<br><br>
NEWS2 and Cockcroft-Gault are used as published, unmodified.
<br><br>
<code>data/facilities.csv</code> is the exception: a <b>live OpenStreetMap
extract</b>. Facility locations are real. Capability is inferred from tier
under Indian Public Health Standards, and only for public facilities —
OpenStreetMap tags a one-doctor nursing home and a 900-bed tertiary centre
identically, so crediting every private hospital with an ICU would be fiction.
Open data can describe India's public health system; it cannot describe the
private one.
<br><br>
Waiting-room vitals on the Reception screen are simulated to demonstrate the
sort; the scoring instrument and the queue model are real.
<br><br>
<code>build_data.py</code> is the single source of every curated number.
</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='padding-top:16px'>{c.stamp('NOT A CLINICAL DEVICE', p.RX)}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(c.rule(), unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:12px;color:{p.INK_3};letter-spacing:0.04em'>"
        "Python · pandas · NumPy · SciPy · Streamlit · Plotly · OpenStreetMap "
        "Overpass · pytest. No API keys, no model server, no network calls at "
        "runtime — the whole thing runs offline on a laptop, which is the point "
        "for a clinic with intermittent connectivity."
        "</div>",
        unsafe_allow_html=True,
    )
