# 5-minute demo script

**Target: 4:30.** Leaves headroom. Record at 1440×900 or larger, browser
zoomed to ~90% so the four check tiles sit on one row.

**Before you hit record**, set the sidebar to the opening state:

| Field | Value |
|---|---|
| Age | 68 |
| Sex | Female |
| Weight | 52 kg |
| Creatinine | 1.9 |
| Infection site | Urinary tract infection |
| Setting | OPD |
| Days of therapy | 7 |
| Risk factors | Indwelling urinary catheter |
| Current medication | Tab Sertraline 50 mg / Tab Ramipril 5 mg |
| Oral agents only | ✅ checked |

---

## 0:00 – 0:35 · The problem

> *Parchi* is what every Indian patient calls the slip the doctor hands them.
>
> A government hospital OPD doctor in India sees a hundred to two hundred
> patients a day. About two minutes each. In that time they have to choose a
> drug — and a culture test takes two to three days and comes out of the
> patient's own pocket, so most of the time it's never sent at all.
>
> So every antibiotic decision is a bet placed blind. This is a cockpit for
> that decision.

*(On screen: the consult tab, already loaded.)*

---

## 0:35 – 1:30 · The draft and the four checks

> Here's a 68-year-old woman, urinary tract infection, outpatient.
>
> Parchi has drafted a prescription — and notice it says *drafted*. It doesn't
> prescribe. It drafts, shows its working, and waits.

*(Point at the four tiles, left to right.)*

> Four checks fire. **Will it work** — this is the probability the drug kills
> whatever's actually causing her infection, in an Indian outpatient, this
> year. **Right dose** — **Can she pay** — **Is it safe.**

*(Hover the dose tile.)*

> And here's the first thing a two-minute consult misses. Her creatinine is
> 1.9. Parchi computed her creatinine clearance — 23. Her kidneys are in
> severe failure and nobody typed that in; it came from her age, weight, sex
> and one lab value.
>
> Which matters, because the *best* drug for her infection is nitrofurantoin —
> and below a clearance of 30 it doesn't reach the bladder and accumulates
> instead. So Parchi removed it before ranking, not after. That's the alert
> below.

---

## 1:30 – 2:15 · Anti-black-box

*(Open the "Why this number" tab.)*

> No clinician should trust a number they can't interrogate. So — here's
> exactly where that coverage figure came from. Every organism that could
> plausibly have caused this infection, weighted by how likely it is, and how
> much of it this drug still covers. Green is covered. Red is what resistance
> has already taken.

*(Open "Resistance trajectory".)*

> And this is the part I didn't expect. There's a rule — from IDSA — that you
> shouldn't use a drug empirically unless local susceptibility is above 80%.
> Apply that rule honestly to Indian data and for several common infections
> **there is no oral drug left that qualifies.**

---

## 2:15 – 2:50 · Cost and safety

*(Point at the cost tile, then change setting to ICU / pick a costlier drug.)*

> Medicines are the largest single piece of out-of-pocket health spending in
> India, and prescriptions get written by brand name. Parchi prices the whole
> course three ways — brand, generic, and Jan Aushadhi, where the identical
> molecule sells for a fraction.

*(Point at the safety tile / alerts.)*

> And safety. She's on sertraline. The tool caught it — sertraline with
> linezolid is serotonin syndrome. It matched that even though the
> interaction table only says "SSRI" and her chart says "sertraline."
>
> It also knows CDSCO's banned combinations. Cefixime plus azithromycin is
> prohibited in India and still prescribed daily.

---

## 2:50 – 3:20 · The honest bit

*(Click Accept, then Reject, so the override counter appears.)*

> The clinician accepts or rejects. And Parchi counts how often it gets
> overruled — and says so on screen. A tool that's rejected most of the time
> is wrong about that population and should be retuned, not trusted harder.
>
> Same with the data. Every figure here is indicative, compiled from published
> ICMR, WHO GLASS, CDSCO and NPPA patterns. That banner is on every screen. I'd
> rather show you the limitation than imply a precision I don't have.

---

## 3:20 – 4:00 · Surge forecast

*(Switch to the Surge tab. Kerala, 12 months.)*

> Second screen. A dengue season isn't a surprise — the curve repeats every
> year and peaks in the same three months. Hospitals still meet it unprepared,
> because nobody turns an epidemic curve into the numbers an administrator can
> actually act on.
>
> So: the forecast, and underneath it — extra OPD screens, admissions,
> bed-days, and **platelet units**. Set your bed count and it tells you whether
> you survive the peak. Every conversion factor is exposed and editable.

*(Scroll to the seasonal index bar chart.)*

> And the seasonality is learned per state, not assumed — the model picks up
> each state's own rhythm.

---

## 4:00 – 4:30 · Escalation, and close

*(Switch to Escalation tab. **Referring from: Malkangiri** — a PHC. Emergency:
**Post-partum haemorrhage.** This combination is the one that lands: the
nearest blood bank is ~70 minutes against a 60-minute window. Compare against
**Kollam**, Kerala, where all six emergencies are reachable — the contrast is
the point.)*

> Last screen — the question a drug can't answer. This patient needs more than
> I have.
>
> "Nearest hospital" is the wrong question. Post-partum haemorrhage is the
> commonest cause of maternal death in India and survival depends on
> transfusion inside an hour. So the question is: where's the nearest facility
> with a **blood bank**, and does it beat the clock?
>
> These are live OpenStreetMap facilities. Capability comes from the facility's
> tier under Indian Public Health Standards — and only for public facilities,
> because open data genuinely can't tell you what a private nursing home can
> do, and I'd rather say that than make it up.

*(Close.)*

> Three screens, four engines, one idea: the data to make these decisions well
> already exists in India. It just never reaches the room where the decision
> gets made.
>
> That's Parchi.

---

## Recording notes

- **Don't narrate the code.** Judges score presentation on the demo, and the
  repo is linked for the technical read.
- If a chart takes a beat to draw, keep talking — don't wait in silence.
- The single strongest moment is the nitrofurantoin block at ~1:15. Slow down
  there.
- Second strongest is the override counter at 2:50. Don't rush past it.
- End on the closing line and stop. No "thanks for watching" trailing off.
