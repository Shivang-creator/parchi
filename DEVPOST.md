# Devpost submission — copy/paste ready

---

## Project name (60 char)

```
Parchi — prescription intelligence for Indian clinics
```

*(52 characters)*

---

## Elevator pitch (200 char)

```
An Indian doctor gets 120 seconds per patient. Parchi checks the prescription in that window: will this antibiotic still work here, is the dose right for these kidneys, can the patient afford it.
```

*(196 characters)*

---

## About the project

### Inspiration

*Parchi* is what every Indian patient calls the slip the doctor hands them.

A government-hospital OPD doctor in India sees 100 to 200 patients in a day —
roughly two minutes each. In that window they have to pick a drug. Culture and
sensitivity testing takes 48 to 72 hours and the patient pays for it out of
pocket, so in most consults it is simply never sent. Every antibiotic decision
is therefore a bet placed blind.

What struck me is that the information to make that bet well **already
exists** — it just never reaches the room where the decision happens. ICMR's
Antimicrobial Resistance Surveillance Network analyses around a hundred
thousand isolates a year and publishes it as an annual PDF. CDSCO publishes the
list of fixed-dose combinations it has banned. NPPA publishes ceiling prices.
Jan Aushadhi runs more than 15,000 outlets selling the identical molecules at a
fraction of branded prices. None of it is at the point of prescribing.

One detail decided the whole project: **ICMR reports resistance separately for
OPD, ward and ICU patients.** The same infection, treated with the same drug,
has a materially different chance of working depending on where the patient is
standing. No clinician carries that table in their head. That is a gap that
only shows up if you look at the data — which is exactly what this hackathon
asked for.

### What it does

Parchi is a prescription cockpit. It never prescribes — it drafts, shows its
full working, and waits for the clinician to accept or reject.

You enter the patient's body parameters and presentation. Parchi drafts a
prescription and fires four checks, each of which only speaks when it has
something actionable to say:

**Will it work?** The probability this agent kills whatever is actually causing
the infection, computed for this site, this setting, this year, then discounted
for the patient's own risk factors.

**Is the dose right for this body?** Cockcroft-Gault creatinine clearance from
age, sex, weight and serum creatinine, mapped to per-drug renal bands.
Contraindicated agents are removed *before* ranking, not flagged afterwards.

**Can the patient pay?** Brand vs generic vs Jan Aushadhi for the full course,
as a rupee figure the patient will actually face.

**Is the combination legal and safe?** CDSCO's banned and irrational fixed-dose
combinations, plus interactions against the patient's existing medication list.

Then two more screens. A **surge forecast** that turns a state's dengue
seasonality into the numbers an administrator can act on — extra OPD screens,
admissions, bed-days, platelet units — because a dengue season is not a
surprise and hospitals still meet it unprepared. And an **escalation map** that
answers the last question of a consult: this patient needs more than I have,
where do I send them, and will they survive the journey? Not the nearest
hospital — the nearest facility that can actually perform the specific thing
this emergency needs.

### How we built it

Python, pandas, NumPy, SciPy, Streamlit and Plotly. Four engine modules behind
three screens, with a hard separation between the data layer, the reasoning and
the UI. No API keys, no model server, no network calls at runtime — the whole
thing runs offline on a laptop, which is the point for a clinic with
intermittent connectivity.

The coverage model is a marginalisation over organisms:

    P(cover) = Σ P(organism | site, setting) × P(susceptible | organism, drug, setting, year)

Combination therapy is where it gets interesting. The naive approach is
1 − Π(1 − pᵢ), which treats the agents as independent — but they are not. Two
carbapenems fail on the *same* carbapenemase-producing isolate; their failures
are almost perfectly correlated. The correct decomposition works organism by
organism, taking the maximum susceptibility across agents. That is why the
model shows meropenem + colistin as worth far more than meropenem + imipenem in
an Indian ICU, which is exactly what the clinical literature says.

The surge forecast is multiplicative seasonal decomposition — a per-state
seasonal index learned from observed monthly shares, times a least-squares
annual trend, with uncertainty from an empirical residual quantile rather than
a distributional assumption. Deliberately the simplest defensible model: seven
annual data points do not earn anything fancier.

The escalation map pulls live facilities from the OpenStreetMap Overpass API
and infers capability from facility tier under Indian Public Health Standards.

### Challenges we ran into

**The stewardship recommender was confidently backwards.** The first version
ranked antibiotics by coverage and recommended the best one — which, for an
outpatient urinary infection, was *colistin*: a nephrotoxic, IV-only, last-line
agent. That is not a cosmetic bug. It is precisely the logic by which last-line
drugs get burned through in the real world. The fix was to invert the
objective: set an absolute adequacy bar per setting, following the IDSA rule
that empiric therapy should exceed ~80% local susceptibility, then pick the
**narrowest** agent that clears it, with WHO AWaRe *Reserve* agents excluded
from first-line unless nothing else qualifies.

**Double-counting risk.** Multiplying every risk factor at full strength gave a
ventilated ICU patient coverage numbers no real unit ever sees. A ventilated
patient has by definition had recent antibiotics and a central line — those are
one underlying exposure, not three independent hits. Factors now compound with
a decaying exponent, and the penalty is further damped in ICU because the ICU
susceptibility data was *already measured on exactly those patients*.

**Holes in the data that looked like bugs but weren't — and one that was.**
Carbapenems appeared to fail catastrophically in ICU sepsis until I realised
the susceptibility table had no entries for carbapenems against gram-positives,
which they do cover. Meanwhile vancomycin's missing gram-negative entries were
*correct* — it genuinely cannot touch them. Separating real intrinsic
resistance from missing data was the fiddliest part of the whole build.

**Overpass timed out on half the anchors**, twice, which is normal for a free
shared endpoint at 1am. Added retries with backoff and made the map degrade
gracefully rather than fail.

**Where to be honest rather than impressive.** OpenStreetMap tags a one-doctor
nursing home and a 900-bed tertiary centre identically as `amenity=hospital`.
Crediting every private facility with an ICU would have made the map look much
better and would have been fiction. Capability is now inferred only for public
tiers, where IPHS defines a mandated service package. Open data can describe
India's public health system; it cannot describe the private one.

### Accomplishments that we're proud of

The tool argues against itself in three separate places, and I think that is
the most valuable thing in it. It recommends the *weakest* adequate drug rather
than the strongest. It counts how often clinicians override it and says so on
screen, because a tool rejected most of the time is wrong about that population
and should be retuned rather than trusted harder. And it states its own data
provenance in plain language on every screen instead of implying a precision it
does not have.

Applying the IDSA 80% rule honestly to Indian resistance data also produced a
genuine finding I did not expect going in: for several common infections, there
is no longer an oral agent that qualifies for empiric use at all.

### What we learned

That the hard part of clinical decision support is not the model — it is
knowing what the model must refuse to do. Every real improvement in this build
came from *constraining* the recommender, not strengthening it.

Also, concretely: Cockcroft-Gault rather than CKD-EPI, because renal dosing
references are written against creatinine clearance and it needs only variables
a registration desk can capture. Why enterococci are intrinsically resistant to
every cephalosporin. Why an alert that always fires is an alert nobody reads —
which is why only major interactions surface by default.

### What's next for Parchi

Replace the curated susceptibility panel with a licensed ICMR-AMRSN feed, and
ultimately with **the hospital's own antibiogram** — the engine is already
parameterised for it, it only wants better numbers. SMART on FHIR so patient
parameters arrive from the EMR instead of being typed. Feed the accept/reject
decisions back as a live calibration signal so the tool measures its own
agreement with clinicians per cohort. And district-level rather than
state-level surge forecasting.

---

## Built with (tags)

```
python, pandas, numpy, scipy, streamlit, plotly, openstreetmap, overpass-api,
health, healthcare, medtech, data-science, antimicrobial-resistance,
clinical-decision-support, public-health, forecasting, geospatial, india,
bayesian-inference, time-series
```

---

## Try it out links

- GitHub repository: `<add repo URL>`

---

## Upload a file

Zip the repository (excluding `__pycache__` and `.git`) and upload — well under
the 35 MB limit.

---

## Image gallery suggestions (3:2 ratio)

1. Consult screen with the drafted prescription and all four check tiles visible
2. The "why this number" organism-contribution breakdown
3. Resistance trajectory chart with the 50% floor crossing
4. Surge forecast with the capacity-overshoot warning
5. Escalation map with the referral route drawn
