"""Parchi — the Indian OPD consult, instrumented.

A prescription cockpit. Four questions get answered at the moment the drug is
chosen, from the patient's own body parameters and India's own resistance,
price and safety data:

    will it work here   ·   is this the right dose for this body
    can the patient pay ·   is this combination legal and safe

Parchi drafts. The clinician decides.

Run:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Parchi — prescription intelligence for Indian clinics",
    page_icon="⚕",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui import consult, escalate, surge, theme  # noqa: E402

st.markdown(theme.CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="masthead">'
    '<div class="logo">पर्ची <span>/ Parchi</span></div>'
    '<div class="tag">the two-minute Indian consult, instrumented</div>'
    "</div>",
    unsafe_allow_html=True,
)

tab_consult, tab_surge, tab_escalate, tab_about = st.tabs(
    ["  Consult  ", "  Surge forecast  ", "  Escalation  ", "  Method & data  "]
)

with tab_consult:
    consult.render()

with tab_surge:
    surge.render()

with tab_escalate:
    escalate.render()

with tab_about:
    st.markdown(
        """
### What this is

Parchi sits at the single moment where Indian clinical medicine, drug
resistance and household finance all collide: a doctor with about two minutes
deciding what to write on a prescription slip.

It never prescribes. It drafts, shows its full working, and waits.

### The four engines

| Module | Question | Method |
|---|---|---|
| `engine/coverage.py` | Will this drug actually work? | `P(cover) = Σ P(organism \\| site, setting) × P(susceptible \\| organism, drug, setting, year)`. Combinations are scored organism-by-organism with a max across agents, not as independent failures. |
| `engine/dosing.py` | Is this the right dose for this body? | Cockcroft-Gault creatinine clearance from age, sex, weight and serum creatinine, then renal dose bands per drug. Contraindicated agents are removed *before* ranking. |
| `engine/safety.py` | Is this combination legal and safe? | CDSCO banned / irrational fixed-dose combinations, plus interaction matching that expands drug classes to their member molecules. Major-only by default — an alert that always fires is an alert nobody reads. |
| `engine/forecast.py` | What is coming in three weeks? | Multiplicative seasonal decomposition: a per-state seasonal index learned from observed monthly shares, times a least-squares annual trend. Uncertainty is an empirical residual quantile, not a distributional assumption. |

### Design decisions worth defending

**The stewardship pick is the narrowest adequate drug, never the strongest.**
Ranking by coverage alone recommends colistin for an outpatient cystitis. That
is how last-line agents get burned through. Parchi sets an absolute adequacy
bar per setting — following IDSA's rule that empiric therapy should exceed
~80% local susceptibility — and then picks the *least* aggressive agent that
clears it.

**Risk factors are not multiplied naively.** A ventilated ICU patient has by
definition had recent antibiotics and a central line; treating those as three
independent hits double-counts one underlying exposure. Factors compound with
a decaying exponent, and the penalty is further damped in ICU because the ICU
susceptibility data was already measured on exactly those patients.

**Absent drug–organism pairs mean zero cover, deliberately.** Vancomycin
genuinely cannot touch gram-negatives; colistin genuinely cannot touch
gram-positives; cephalosporins have no enterococcal activity. Those holes are
the model working, not missing data.

**Overrides are counted and shown.** A tool that is rejected most of the time
is wrong about that population. Parchi says so on screen rather than
recommending confidently into the void.

### Data provenance — stated plainly

Every figure in `data/` is **indicative**, compiled from published patterns in
the ICMR Antimicrobial Resistance Surveillance Network reports, WHO GLASS,
CDSCO's prohibited fixed-dose combination lists, NPPA ceiling-price structures
and NCVBDC dengue reporting. Susceptibility series are anchored at an early
and a recent endpoint with the intermediate years reconstructed — the
*direction and magnitude* of each trend are real, the individual year points
are not observations.

This is a demonstration build, not a clinical device. `build_data.py` is the
single source of every number; swap those CSVs for the licensed real series
and nothing downstream changes.

### Built on

Python · pandas · NumPy · SciPy · Streamlit · Plotly. No model server, no API
keys, no network calls at runtime — the whole thing runs offline on a laptop,
which is the point for a rural Indian clinic.
        """
    )
