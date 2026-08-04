# पर्ची · Parchi

**The two-minute Indian consult, instrumented.**

*Parchi* is what every Indian patient calls the slip the doctor hands them. This
is a prescription cockpit for the moment that slip gets written — the single
point where clinical medicine, drug resistance, household finance and
geography all collide, and where an Indian doctor has roughly 120 seconds to
decide.

Built for **Vitalitics 2026** (MedTech × Data Science).

---

## The problem

A government-hospital OPD doctor in India sees 100–200 patients a day. Culture
and sensitivity testing takes 48–72 hours and is paid for out of pocket, so in
most consults it is never sent at all. Every antibiotic decision is therefore a
**bet placed blind** — and four things about that bet go unchecked:

| | What goes wrong | Scale |
|---|---|---|
| **Will it work?** | India is the world's largest consumer of antibiotics and a global epicentre of resistance. The drug most likely to be reached for often has a coin-flip chance of working — and the doctor has no way to know the local number. | ICMR-AMRSN surveillance covers ~100k isolates a year and almost none of it reaches the point of prescribing |
| **Is the dose right for this body?** | Normal adult doses given to patients with quietly impaired kidneys. Nobody computes creatinine clearance in a two-minute consult. | Among the commonest and most invisible prescribing errors |
| **Can the patient pay?** | Prescriptions are written by brand name. The identical molecule sits at a fraction of the price as a generic or at a Jan Aushadhi kendra. | Medicines are the largest single component of Indian out-of-pocket health spending |
| **Is the combination legal?** | India's market carries thousands of fixed-dose combinations; CDSCO has formally prohibited hundreds. They are still prescribed daily. | e.g. cefixime + azithromycin — two broad agents welded together, no evidence, resistance pressure on both |

Parchi answers all four at the moment of prescribing, from data that already
exists but never reaches the consulting room.

**It never prescribes. It drafts, shows its full working, and waits for the
clinician to accept or reject.**

---

## What it does

Five screens following the arc of a real episode of care: choose the drug,
settle the bet when the culture returns, prepare for what is coming, and know
where to send the patient you cannot treat.

### 1 · Consult — the prescription cockpit

Enter the patient's body parameters and presentation. Parchi drafts a
prescription and fires four checks, each of which only speaks when it has
something actionable to say:

- **Coverage** — the probability this agent kills whatever is actually causing
  the infection, computed for this infection site, this care setting and this
  year, then discounted for the patient's own risk factors.
- **Dose** — Cockcroft-Gault creatinine clearance from age, sex, weight and
  serum creatinine, mapped to per-drug renal bands. **Contraindicated agents
  are removed before ranking, not flagged after.**
- **Cost** — brand vs generic vs Jan Aushadhi for the full course, as a rupee
  figure the patient will actually face.
- **Duration** — course length against evidence-based durations. The commonest
  overuse in Indian prescribing is not the wrong drug, it is too many days of
  the right one.
- **Safety** — CDSCO banned and irrational fixed-dose combinations, plus
  interactions against the patient's existing medication list. Checked across
  the *whole* slip, not just the antibiotic.

Then it shows its working: which organism contributed what to the coverage
number, what the alternatives were, how this drug's effectiveness has moved
over seven years of surveillance, and whether a combination would do better.

### 2 · Day 3 · Culture — the step everyone skips

Forty-eight hours later the culture settles the bet. De-escalating to the
narrowest agent that treats the actual isolate is the single highest-value
action in stewardship, and the one most reliably skipped — so the patient
finishes a week of meropenem for an organism a five-rupee tablet would have
killed. This screen does that one thing. When the lab has reported
sensitivities that list is **authoritative** and overrides the surveillance
estimate; without it, Parchi refuses to narrow on population data alone,
because that would be a guess dressed as a recommendation.

### 3 · Surge forecast — what is walking through the door in three weeks

A dengue season is not a surprise. The curve repeats annually and peaks in the
same three months. Hospitals still meet it unprepared, because nobody converts
an epidemiological curve into the numbers an administrator can act on. Parchi
forecasts state-level cases across dengue, malaria and chikungunya and
translates them into **extra OPD screens, admissions, bed-days and platelet
units** — then tells you whether your bed count survives the peak, and stacks
every disease together because a hospital does not get one outbreak at a time.

The forecast is **backtested**: refit on data up to a cutoff, then asked to
predict twelve months it never saw, scored against the baseline every
administrator already has — *assume this month looks like the same month last
year*. It beats that baseline on **15 of 18 series**, and loses on three. It
loses where a state's annual total jumped by an order of magnitude between
years, which no seasonal model catches. The app says so on screen rather than
reporting only the wins.

### 4 · Escalation — the nearest facility that can actually treat this

"Nearest hospital" is the wrong question. A myocardial infarction needs a
catheterisation lab; an obstructed labour needs a theatre and blood; a stroke
needs thrombolysis inside 4.5 hours. Parchi maps live OpenStreetMap facilities,
infers capability from the facility's tier under Indian Public Health
Standards, and answers: **from here, can this specific emergency be reached in
time — and how many minutes are wasted by stopping at the closest signboard
first?**

---

## How it works

```
build_data.py          curated data layer -> data/*.csv
fetch_facilities.py    live OpenStreetMap extract -> data/facilities.csv
tools/shoot.py         screenshots the running app, tab by tab

engine/
  data.py        cached loaders; hospital-antibiogram override
  coverage.py    empiric coverage, combinations, de-escalation, trajectory
  dosing.py      Cockcroft-Gault, renal bands, paediatric mg/kg, duration, cost
  safety.py      banned FDCs, class-expanded interaction matching
  forecast.py    seasonal decomposition, demand conversion, backtesting
  geo.py         golden-hour reachability by capability

ui/
  theme.py       every colour, the type scale, the Plotly layout
  components.py  every piece of raw markup
  consult.py     the prescription cockpit
  culture.py     de-escalation on day three
  surge.py       the forecast screen
  escalate.py    the referral map
app.py           tab shell + antibiogram upload + method
```

**Scale:** 31 antibiotics · 17 organisms · 11 infection sites · 3 vector-borne
diseases across 20 states · 5,271 susceptibility rows · ~5,000 lines of Python.

### Design

The app is a *document*, not a dashboard — because a **parchi** is a piece of
paper. Warm stock with a fine grain, warm near-black ink, one signature ℞ red,
hairline rules instead of boxes, 3px radii, a Newsreader/IBM Plex pairing, and
the recommendation rendered as an actual prescription slip with a signature
rule. Committing to that metaphor is also what keeps it from looking like every
other generated dashboard: charcoal-with-a-blue-accent and a six-colour
semantic rainbow is a costume, not a design.

### The coverage model

```
P(cover) = Σ  P(organism | site, setting) × P(susceptible | organism, drug, setting, year)
        organisms
```

Combinations are **not** scored as `1 − Π(1 − pᵢ)`. That treats the agents as
independent, and they are not — two carbapenems fail on the *same*
carbapenemase-producing isolate. The correct decomposition works organism by
organism, taking the maximum susceptibility across agents:

```
P(cover) = Σ  P(organism) × max  P(susceptible | organism, drug)
        organisms            drugs
```

This is why meropenem + colistin is worth so much more than meropenem +
imipenem in an Indian ICU, and the model shows it.

### Four decisions worth defending

**The recommendation is the narrowest adequate drug, never the strongest.**
Ranking by coverage alone recommends *colistin for an outpatient cystitis* —
this was an actual bug during development, and it is exactly how last-line
agents get burned through in the real world. Parchi sets an absolute adequacy
bar per setting, following the IDSA rule that empiric therapy should exceed
~80% local susceptibility, then picks the **least** aggressive agent clearing
it. WHO AWaRe *Reserve* agents are excluded from first-line unless nothing else
qualifies — and then it says so out loud.

**Risk factors are not multiplied naively.** A ventilated ICU patient has by
definition had recent antibiotics and a central line; treating those as three
independent hits double-counts one underlying exposure and drives coverage to
numbers no real unit sees. Factors compound with a decaying exponent, and the
penalty is further damped in ICU because the ICU susceptibility data was
already measured on precisely those patients.

**Absent drug–organism pairs mean zero cover, deliberately.** Vancomycin
genuinely cannot touch gram-negatives; colistin genuinely cannot touch
gram-positives; cephalosporins have no enterococcal activity. Those holes are
the model working, not missing data.

**Overrides are counted and displayed.** A tool rejected most of the time is
wrong about that population and should be retuned, not trusted harder.

**The forecast is scored, including where it loses.** A forecast nobody has
backtested is an opinion.

**Absent infections are absent from the dropdown.** A ventilator-associated
pneumonia has no outpatient form, so OPD is not offered for it — a nonsense
query would otherwise return a confident nonsense answer. Parchi
reports its own override rate on screen.

---

## Data provenance — stated plainly

Every figure in `data/` is **indicative**, compiled from published patterns in
the ICMR Antimicrobial Resistance Surveillance Network reports, WHO GLASS,
CDSCO's prohibited fixed-dose-combination lists, NPPA ceiling-price structures
and NCVBDC dengue reporting. Susceptibility series are anchored at an early and
a recent endpoint with intermediate years reconstructed — **the direction and
magnitude of each trend are real; the individual year points are not
observations.**

`data/facilities.csv` is the exception: it is a **live OpenStreetMap extract**,
fetched at build time. Facility *locations* are real. Facility *capability* is
inferred from tier under IPHS norms — and only for public facilities, because
OpenStreetMap tags a one-doctor nursing home and a 900-bed tertiary centre
identically. Private facilities are credited with no capability unless their
name carries a scale marker. Open data can describe India's public health
system; it cannot describe the private one, and pretending otherwise would be
fiction.

`build_data.py` is the single source of every curated number. Swap those CSVs
for the licensed real series and nothing downstream changes.

> **This is a demonstration build, not a clinical device, and not for patient
> care.** The banner saying so is visible on every screen.

---

## Running it

```bash
pip install -r requirements.txt
python build_data.py          # emits the curated CSVs
python fetch_facilities.py    # optional: live OSM facility extract
streamlit run app.py
```

No API keys, no model server, no network calls at runtime. The whole thing runs
offline on a laptop — which is the point, for a clinic with intermittent
connectivity.

## Built with

Python 3.13 · pandas · NumPy · SciPy · Streamlit · Plotly · OpenStreetMap
Overpass API

## What's next

- Replace the curated susceptibility panel with a licensed ICMR-AMRSN feed. The
  **hospital's own antibiogram** already works today: upload a CSV on the
  Method tab and every engine re-bases on it immediately.
- SMART on FHIR so the patient parameters arrive from the EMR instead of being
  typed.
- Feed accept/reject decisions back as a live calibration signal, so the tool
  measures its own agreement with clinicians per cohort rather than assuming it.
- District-level rather than state-level surge forecasting.
