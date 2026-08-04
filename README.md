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

Parchi is not five tools. It is **one patient's walk through a building**, and
the navigation says so:

| Stop | Decides | Engine |
|---|---|---|
| **Reception** | *when* they are seen | NEWS2 triage + a queue model |
| **Doctor** | *what* they are given | coverage, dosing, duration, safety |
| **Pharmacy** | whether they can actually take it | substitution, affordability, stock |
| **Hospital** | whether the building was ready at all | surge forecast, escalation map |

### 1 · Reception — turning a queue into triage

An Indian OPD is a queue. Patients travel before dawn, arrive together, and are
seen in the order they reached the window — so the person having a heart attack
waits behind the person with a rash.

Fixing that needs no equipment. **NEWS2** — the National Early Warning Score 2 —
is six measurements and ninety seconds, and it is a real validated instrument.
Parchi scores it (including the single-parameter escalation rule that most
implementations get wrong), shows every parameter's contribution, and then
re-sorts the waiting room by acuity, reporting how many places the patient
moves and how many minutes that saves.

It also models the day. Demand is front-loaded into the 8–11am crush while
capacity is flat across nine hours, and that mismatch **is** the queue —
visible the evening before. The output is not a wait time, it is a roster
decision: *this department needs five doctors today, not three.*

### 2 · Doctor — the prescription cockpit

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

### 3 · Day 3 · Culture — the step everyone skips

Forty-eight hours later the culture settles the bet. De-escalating to the
narrowest agent that treats the actual isolate is the single highest-value
action in stewardship, and the one most reliably skipped — so the patient
finishes a week of meropenem for an organism a five-rupee tablet would have
killed. This screen does that one thing. When the lab has reported
sensitivities that list is **authoritative** and overrides the surveillance
estimate; without it, Parchi refuses to narrow on population data alone,
because that would be a guess dressed as a recommendation.

### 4 · Pharmacy — where a prescription becomes a bill

The last place anything can be changed, and the only place anyone finds out
what the slip actually costs.

- **Substitution** across brand, generic and Jan Aushadhi tiers.
- **Affordability**, priced in **days of that household's income** rather than
  rupees — because ₹1,400 is a routine expense for a salaried family and *five
  days of earnings* on the MGNREGA wage, and only the second one gets abandoned
  half-way. A partially taken antibiotic course is worse than none: it selects
  for resistance without curing anything.
- **Stock**, because a prescriber who cannot get nitrofurantoin writes a
  fluoroquinolone. Supply is a stewardship intervention, and the narrow agents
  are the ones running out.
- **Pregnancy safety** and **counselling** — the part of dispensing that is
  free, evidence-based and almost never done.

### 5 · Surge forecast — what is walking through the door in three weeks

A dengue season is not a surprise. The curve repeats annually and peaks in the
same three months. Hospitals still meet it unprepared, because nobody converts
an epidemiological curve into the numbers an administrator can act on. Parchi
forecasts state-level cases across dengue, malaria and chikungunya and
translates them into **extra OPD screens, admissions, bed-days and platelet
units** — then tells you whether your bed count survives the peak, and stacks
every disease together because a hospital does not get one outbreak at a time.

Dengue burden is **real**: state-wise counts published by the National Center
for Vector Borne Diseases Control (NCVBDC), Ministry of Health & Family
Welfare — 35 states, 2021–2025, fetched live by `fetch_ncvbdc.py`. Malaria and
chikungunya remain indicative and are labelled as such **on screen, per series**.

The forecast is **backtested**: refit on data up to a cutoff, then asked to
predict twelve months it never saw, scored against the baseline every
administrator already has — *assume this month looks like the same month last
year*.

**It beats that baseline on about a third of real state series, and the app
says so.** An earlier build scored 15 of 18 — against reconstructed data that
was smooth by construction. Swapping in the real national series, that result
did not survive, and the honest number replaced it. Real dengue is
boom-and-bust: a national peak of 290,618 cases in 2023 falling to 122,456 by
2025. A damped trend cannot anticipate a swing like that, and for a strongly
seasonal disease *same month last year* is a hard baseline.

That does not undermine what the screen is for. It converts *whatever* case
forecast you trust into bed-days, staffing and platelet units; substitute your
own state projection and every downstream number re-bases.

**Deliberately not reported: peak-month accuracy.** The real series gives
annual totals and the monthly split applies a fixed documented profile, so
recovering the peak month is a round trip through our own assumption rather
than a prediction. Only the annual level is observed, so only the annual level
is scored. A test asserts the metric is never surfaced under a quotable name.

### 6 · Escalation — the nearest facility that can actually treat this

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
  triage.py      NEWS2 scoring, queue model, staffing recommendation
  coverage.py    empiric coverage, combinations, de-escalation, trajectory
  dosing.py      Cockcroft-Gault, renal bands, paediatric mg/kg, duration, cost
  safety.py      banned FDCs, class-expanded interaction matching
  pharmacy.py    substitution, affordability, stock pressure, counselling
  forecast.py    seasonal decomposition, demand conversion, backtesting
  geo.py         golden-hour reachability by capability

ui/
  theme.py       two palettes, the type scale, the Plotly layout, the nav rail
  components.py  every piece of raw markup, plus the SVG icon set
  reception.py   triage and the queue
  consult.py     the prescription cockpit
  culture.py     de-escalation on day three
  pharmacy.py    the dispensing counter
  surge.py       the forecast screen
  escalate.py    the referral map
  method.py      provenance, model notes, antibiogram upload
tests/           53 engine tests
tools/shoot.py   screenshots the running app, stop by stop, in either palette
app.py           role router
```

**Scale:** 31 antibiotics · 17 organisms · 11 infection sites · 8 OPD
departments · 3 vector-borne diseases across 20 states · 19 data tables ·
5,271 susceptibility rows · ~6,600 lines of Python · 53 tests.

### Design

The app is a *document*, not a dashboard — because a **parchi** is a piece of
paper. Warm stock with a fine grain, warm near-black ink, one signature ℞ red,
hairline rules instead of boxes, 3px radii, a Newsreader/IBM Plex pairing, and
the recommendation rendered as an actual prescription slip with a signature
rule. Committing to that metaphor is what keeps it from looking like every
other generated dashboard: charcoal-with-a-blue-accent and a six-colour
semantic rainbow is a costume, not a design.

**Two palettes, one object.** *Paper* is a slip on a desk; *Ink* is the same
slip under a reading lamp at 2am — warm near-black ground, cream ink, the same
℞ red lifted for contrast. Dark mode here is deliberately not "the blue-grey
one".

The switch is implemented through PEP 562 module `__getattr__`: colour tokens
resolve at *render* time, so every existing `theme.SAFE` call site kept working
untouched instead of every screen having to thread a palette object through.

**The nav is one control, not two.** A decorative rail plus a button row to
click is duplicated navigation and duplicated vertical space, so the buttons
*are* the rail — icon painted on as a background image, subtitle injected
through `::after`, because a Streamlit button label is plain text. (A side
effect worth knowing: CSS generated content is folded into the accessible name,
which is why `tools/shoot.py` selects nav by position rather than by label.)

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

**Two series are real, not indicative.** `data/burden_dengue.csv` is fetched
live from NCVBDC (Ministry of Health & Family Welfare) — state-wise dengue
cases and deaths, 2021–2026, with provisional part-years excluded from every
model. `data/burden_source.json` records the URL and retrieval date. The app
badges provenance per disease, so a viewer is never left guessing which
numbers are observed.

`data/facilities.csv` is likewise real: a **live OpenStreetMap extract**,
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
pip install -r requirements.txt        # runtime only
pip install -r requirements-dev.txt    # + pytest, ruff, playwright

python fetch_ncvbdc.py        # real dengue burden, live from the health ministry
python build_data.py          # emits the curated CSVs (already committed)
python fetch_facilities.py    # optional: live OSM facility extract
streamlit run app.py

python -m pytest tests -q     # 53 engine tests
python tools/shoot.py --theme Ink   # optional: screenshot every stop
```

### Tests

53 tests covering the invariants where a silent regression would produce a
*confident wrong answer* rather than a crash. Several encode bugs that actually
happened: the stewardship picker recommending colistin for outpatient cystitis,
the malaria forecast collapsing to zeros, the banned-FDC checker never firing.

The suite was mutation-checked — deliberately breaking `crcl *= 0.85`,
`TREND_DAMPING` and the Reserve-agent guard to confirm the tests fail. The third
mutation initially *passed*, which exposed that the colistin test was filtering
to oral agents and therefore excluding colistin on route alone. It now asserts
across every site and setting.

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
