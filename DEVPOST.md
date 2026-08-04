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
An Indian doctor gets 120 seconds per patient. Parchi follows that patient through the building — triage at reception, the prescription itself, and what it costs at the pharmacy counter.
```

*(186 characters)*

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

Parchi is not five tools with a shared logo. It follows **one patient through
a building**, and the navigation is that walk:

**Reception** decides *when* they are seen. An Indian OPD is a queue: patients
travel before dawn, arrive together, and are seen in the order they reached the
window — so the person having a heart attack waits behind the person with a
rash. Fixing that needs no equipment, only NEWS2: six measurements, ninety
seconds, a real validated instrument. Parchi scores it, re-sorts the waiting
room by acuity, and reports how many places the patient moved. It also models
the day, because demand is front-loaded into the 8–11am crush while capacity is
flat across nine hours — and that mismatch *is* the queue, visible the evening
before. The output is a roster decision, not a wait time.

**The doctor** decides *what* they are given. That is the prescription cockpit
below.

**The pharmacy** decides whether they can actually take it. Substitution across
brand, generic and Jan Aushadhi tiers — then affordability priced in **days of
that household's income**, because ₹1,400 is a routine expense for a salaried
family and *five days of earnings* on the MGNREGA rural wage, and only the
second one gets abandoned half-way. A partially taken antibiotic course is
worse than none: it selects for resistance without curing anything. The screen
also shows which shelves are emptying, because a prescriber who cannot get
nitrofurantoin writes a fluoroquinolone. Supply is a stewardship intervention.

**The hospital** screens ask whether the building was ready at all.

It never prescribes. It drafts, shows its full working, and waits for the
clinician to accept or reject.

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

There is a fifth check, and it is the one Indian prescribing gets wrong most
often: **is the course the right length?** Not the wrong drug — too many days
of the right one.

Then three more screens. **Day 3 · Culture** exists because de-escalation is
the highest-value action in stewardship and the one most reliably skipped: the
culture comes back, nobody goes and narrows, and the patient finishes a week of
meropenem for an organism a five-rupee tablet would have killed. A **surge
forecast** turns a state's dengue, malaria and chikungunya seasonality into the
numbers an administrator can act on — extra OPD screens, admissions, bed-days,
platelet units — because a season is not a surprise and hospitals still meet it
unprepared. And an **escalation map** answers the last question of a consult:
this patient needs more than I have, where do I send them, and will they
survive the journey? Not the nearest hospital — the nearest facility that can
actually perform the specific thing this emergency needs.

Every screen can also be re-based on a hospital's **own antibiogram**: upload a
CSV and national surveillance is replaced wholesale.

### How we built it

Python, pandas, NumPy, SciPy, Streamlit and Plotly. **Eight engine modules
behind seven screens**, with a hard separation between the data layer, the
reasoning and the UI: `engine/` never imports Streamlit, `ui/` never opens a
file, and `engine/data.py` is the only module that touches disk. 19 curated
data tables, ~6,600 lines of Python, 53 tests. No API keys, no model server, no
network calls at runtime — the whole thing runs offline on a laptop, which is
the point for a clinic with intermittent connectivity.

Reception runs **NEWS2** as published, including the single-parameter
escalation rule that most implementations get wrong: a patient can total 3 and
still need urgent review, because one system deranged enough to score 3 by
itself means something is badly wrong. The queue is a deterministic model —
arrivals against per-department throughput — which converts a wait into a
staffing number.

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
seasonal index learned from observed monthly shares, times an annual trend
fitted in log space, with uncertainty from an empirical residual quantile
rather than a distributional assumption. Deliberately the simplest defensible
model: seven annual data points do not earn anything fancier.

And it is **backtested**. Refit on data up to a cutoff, then asked to predict
twelve months it never saw, and scored against the baseline every administrator
already carries in their head — *assume this month looks like the same month
last year*. It beats that baseline on 15 of 18 series. It loses on three, all
of them states whose annual total jumped by an order of magnitude between
years, which no seasonal model catches. The app reports the losses on screen.

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

**A forecast that quietly collapsed to zero.** Malaria has declined so steeply
in India that a straight-line fit through the annual totals extrapolates below
zero within a year — and clipping at zero turned entire state forecasts into
rows of zeros. Case counts are non-negative and move multiplicatively, so the
trend belongs in log space, where a declining series decays toward zero
asymptotically instead of crashing through it.

**The banned-combination checker was dead code.** It could match a prohibited
FDC like cefixime + azithromycin perfectly well — but the UI only ever handed
it one drug, so it could never fire. Real prescriptions have several lines on
them. Adding the rest of the slip to the check brought the whole feature to
life, and immediately surfaced the nephrotoxic triples too.

**A second-long lag on every keystroke.** Scoring every drug and then every
pair of drugs, one organism at a time through pandas `.loc`, took 1.27 seconds
— and Streamlit re-runs the entire script on every interaction. The whole
calculation is a matrix product: pivot susceptibility once into an
organism × drug array and coverage for the entire formulary is `priors @ matrix`.
Same arithmetic, agreement to 3×10⁻¹⁶, 200× faster.

**The `background:` shorthand tiled an icon across a whole button.** In dark
mode the active nav segment rendered its icon about forty times. The active-state
rule set `background: <colour>`, and that shorthand silently resets
`background-repeat` to its initial value. Longhand everywhere fixed it.

**A test that passed for the wrong reason.** After writing 53 tests I
mutation-checked the suite — deliberately breaking three engine constants to
confirm the tests would fail. Two were caught. The third, flipping the guard
that keeps WHO *Reserve* agents out of first-line therapy, **survived** — because
the colistin regression test filtered to oral agents, and colistin is IV-only,
so it was excluded on route rather than on stewardship. The test now asserts
across every site and setting, and the mutation is caught.

**Overpass timed out on half the anchors**, twice, which is normal for a free
shared endpoint at 1am. Added retries with backoff and made the map degrade
gracefully rather than fail.

**Where to be honest rather than impressive.** OpenStreetMap tags a one-doctor
nursing home and a 900-bed tertiary centre identically as `amenity=hospital`.
Crediting every private facility with an ICU would have made the map look much
better and would have been fiction. Capability is now inferred only for public
tiers, where IPHS defines a mandated service package. Open data can describe
India's public health system; it cannot describe the private one.

### Design

The first version looked like every other generated dashboard: charcoal ground,
blue accent, a six-colour semantic rainbow, everything in equal rounded boxes.
That is a costume, not a design — it has no point of view.

The fix was sitting in the name. A *parchi* is a piece of paper, so the app is a
**document**: warm stock with a fine grain, warm near-black ink rather than
pure black, one signature ℞ red, hairline rules instead of boxes, 3px radii
because paper does not have 14px rounded corners, and a Newsreader/IBM Plex
pairing doing the work that boxes and gradients usually do badly. The
recommendation renders as an actual prescription slip — ℞ glyph, spectrum and
AWaRe marks along the foot, a dotted signature rule. Icons are inline SVG at
the same 1.5px stroke weight as the hairlines, never emoji: emoji are somebody
else's illustration style, render differently on every platform, and cannot
take the ink colour.

**Two palettes, one object.** *Paper* is a slip on a desk; *Ink* is the same
slip under a reading lamp at 2am — warm near-black ground, cream ink, the same
℞ red lifted for contrast. Dark mode here is deliberately not "the blue-grey
one", because adopting the standard dark-dashboard palette would throw away the
only thing that makes this look designed.

Implementing it cleanly was the interesting part. Colour tokens resolve at
*render* time through PEP 562 module `__getattr__`, so `theme.SAFE` silently
means one thing in Paper and another in Ink — and not one of the several
hundred existing call sites had to be rewritten to thread a palette object
through.

**The UX flow was the thing that actually needed fixing.** The old build had
five tabs and a global sidebar that said "The patient" while you were looking
at a state dengue forecast. Reframing it as one patient's walk through a
building — reception, doctor, pharmacy — made the navigation mean something.
And the nav is now one control rather than two: the buttons *are* the rail,
with the icon painted on as a background image and the subtitle injected
through `::after`, because a Streamlit button label is plain text.

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

The escalation map produced the other one. From a primary health sub-centre in
Gadchiroli — a real facility, real coordinates, live from OpenStreetMap — the
nearest catheterisation lab is about **ten and a half hours** away against a
120-minute window for a heart attack. From an equivalent facility in Kerala it
is twenty-one minutes. That gap is not a modelling artefact; it is the map.

### What we learned

That the hard part of clinical decision support is not the model — it is
knowing what the model must refuse to do. Every real improvement in this build
came from *constraining* the recommender, not strengthening it.

And that a test suite is worth exactly as much as its worst test. Mutation
checking took ten minutes and found that one of the tests I was proudest of was
green for a reason that had nothing to do with what it claimed to verify.

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
python, pandas, numpy, scipy, streamlit, plotly, pytest, playwright,
openstreetmap, overpass-api, health, healthcare, medtech, data-science,
antimicrobial-resistance, clinical-decision-support, public-health,
forecasting, geospatial, india, triage, news2, antibiotic-stewardship
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

1. Doctor — the prescription slip, coverage verdict, all four checks
2. Reception — NEWS2 triage and the waiting room re-sorted by acuity
3. Pharmacy — days-of-income affordability and the substitution saving
4. The resistance heatmap — the whole organism × antibiotic panel
5. Day 3 · Culture — de-escalation from meropenem, spectrum bands saved
6. Surge forecast with the capacity-overshoot warning and the backtest
7. Escalation map with the referral route drawn across Gadchiroli
8. The same screen in the Ink palette, to show both themes
