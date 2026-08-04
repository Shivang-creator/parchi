# 5-minute demo script

**Target: 4:40.** Record at 1500×1000 or larger, browser at ~90% zoom so the
four check tiles sit on one row and the slip stays above the fold.

## Before you hit record

Sidebar (drives the Consult tab):

| Field | Value |
|---|---|
| Age | 68 · Female · 52 kg |
| Creatinine | 1.9 |
| Infection | Urinary tract infection |
| Setting | OPD |
| Days of therapy | 5 |
| Risk factors | Indwelling urinary catheter |
| Already taking | Tab Sertraline 50 mg / Tab Ramipril 5 mg |
| Also prescribing | *(empty — you add one live)* |
| Oral agents only | ✅ |

Other tabs, pre-set before recording so you never fumble a dropdown on camera:

- **Day 3 · Culture** — organism *Acinetobacter baumannii*, currently on
  *Meropenem*, setting *ICU*
- **Surge** — Dengue, Kerala, 12 months, 60 beds
- **Escalation** — *Myocardial infarction (STEMI)*, area **Gadchiroli**

---

## 0:00 – 0:30 · The problem

> *Parchi* is what every Indian patient calls the slip the doctor hands them.
>
> A government hospital OPD doctor in India sees a hundred to two hundred
> patients a day — about two minutes each. In that time they pick a drug. And a
> culture test takes two to three days and comes out of the patient's own
> pocket, so most of the time it's never sent at all.
>
> So every antibiotic decision is a bet placed blind. This is a cockpit for
> that bet.

---

## 0:30 – 1:20 · The draft, and the thing a two-minute consult misses

> Sixty-eight-year-old woman, urinary tract infection, outpatient. Parchi has
> drafted a prescription — and note the word *drafted*. It never prescribes. It
> drafts, shows its working, and waits.

*(Point across the four checks.)*

> Will it work. Right dose. Right length. What it costs.

*(Slow down here — this is the strongest moment in the video.)*

> Her creatinine is 1.9. Parchi computed her creatinine clearance — 23. Her
> kidneys are in severe failure, and nobody typed that in; it came from her age,
> weight, sex and one lab value.
>
> Which matters, because the standard drug for her infection is nitrofurantoin
> — and below a clearance of 30 it doesn't reach the bladder and accumulates
> instead. So Parchi removed it **before ranking**, not after. That's the note
> at the bottom.

---

## 1:20 – 2:00 · Anti-black-box

*(Open "Why this number".)*

> No clinician should trust a number they can't interrogate. So: every organism
> that could plausibly have caused this, weighted by how likely it is, and how
> much of it this drug still covers. Green is covered. Red is what resistance
> has already taken.

*(Open "Is it still working".)*

> And here's what I didn't expect going in. There's an IDSA rule — don't use a
> drug empirically unless local susceptibility is above 80%. Apply that rule
> honestly to Indian data and for several common infections **there is no oral
> drug left that qualifies.**

---

## 2:00 – 2:35 · Cost, safety, and the honest bit

*(Add **Cefixime** and **Azithromycin** in the sidebar "Also prescribing".)*

> Real prescriptions have several lines. Watch what happens when I add two.
>
> Cefixime plus azithromycin is a **banned** fixed-dose combination in India —
> CDSCO prohibited it — and it's still prescribed daily. And she's on
> sertraline, so anything I add gets checked against that too.

*(Point at the cost tile.)*

> Medicines are the largest single piece of out-of-pocket health spending in
> India, and prescriptions get written by brand name. Parchi prices the whole
> slip three ways — brand, generic, and Jan Aushadhi.

*(Click Sign, then Override.)*

> The clinician decides. And Parchi counts how often it gets overruled and says
> so on screen — because a tool that's rejected most of the time is wrong about
> that population and should be retuned, not trusted harder.

---

## 2:35 – 3:10 · Day 3 — the step everyone skips

*(Switch to **Day 3 · Culture**.)*

> Forty-eight hours later the culture comes back and the bet can be settled. De-
> escalating to the narrowest drug that actually treats the isolate is the
> single highest-value action in stewardship — and the one most reliably
> skipped. So the patient finishes a week of meropenem for an organism a five-
> rupee tablet would have killed.
>
> This screen does that one thing. And when the lab has reported sensitivities,
> that list is authoritative — it overrides the national estimate, because the
> isolate in front of you beats any population average.

---

## 3:10 – 3:55 · Surge, and does it actually work

*(Switch to **Surge**.)*

> A dengue season isn't a surprise. The curve repeats every year and peaks in
> the same three months. Hospitals still meet it unprepared, because nobody
> turns an epidemic curve into the numbers an administrator can act on.
>
> So: extra OPD screens, admissions, bed-days, and **platelet units**. Set your
> bed count and it tells you whether you survive the peak.

*(Scroll to the backtest panel.)*

> And a forecast nobody has scored is just an opinion. So I held out the last
> twelve months, refit the model on everything before that, and asked it to
> predict months it had never seen — against the baseline every administrator
> already has: assume this month looks like the same month last year.
>
> It beats that baseline on fifteen of eighteen series. **It loses on three** —
> states whose annual total jumped by an order of magnitude between years, which
> no seasonal model catches. That's on screen too. I'd rather show you where it
> fails.

---

## 3:55 – 4:30 · Escalation

*(Switch to **Escalation**. Gadchiroli, STEMI.)*

> Last screen — the question a drug can't answer. This patient needs more than I
> have.
>
> "Nearest hospital" is the wrong question. A heart attack needs a
> catheterisation lab, not a signboard. So: from this primary health sub-centre
> in Gadchiroli, where's the nearest facility that can actually open the artery?
>
> **Ten and a half hours.** Against a two-hour window. From an equivalent
> facility in Kerala it's twenty-one minutes.
>
> These are real coordinates, live from OpenStreetMap. Capability comes from the
> facility's tier under Indian Public Health Standards — and only for public
> facilities, because open data genuinely can't tell you what a private nursing
> home can do, and I'd rather say that than make it up.

---

## 4:30 – 4:40 · Close

> Every figure in here is indicative, compiled from published ICMR, WHO GLASS,
> CDSCO and NPPA patterns — that's stated on every screen. Point it at a real
> antibiogram and nothing downstream changes; there's an upload for exactly
> that.
>
> Three engines, five screens, one idea: the data to make these decisions well
> already exists in India. It just never reaches the room where the decision
> gets made.
>
> That's Parchi.

---

## Recording notes

- **Don't narrate the code.** Presentation is scored on the demo; the repo is
  linked for the technical read.
- Strongest three moments, in order: the nitrofurantoin renal block (~1:00),
  the banned FDC firing live (~2:05), and 606 minutes in Gadchiroli (~4:05).
  Slow down at each.
- Second-strongest is the backtest admitting it loses on three series. Judges
  notice honesty; do not rush it.
- If a chart takes a beat to draw, keep talking. Never wait in silence.
- End on "That's Parchi" and stop. No trailing thanks.
