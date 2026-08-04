# 5-minute demo script

**Target 4:40.** Record at 1560×1000 or larger, browser at ~90% zoom so the
check row sits on one line and the slip stays above the fold.

The structure of the video is the structure of the app: **you walk one patient
through a building.** Say that early and the whole thing hangs together.

## Before you hit record

Open the app, then set each stop up once so you never fumble a dropdown on
camera. Leave it on **Doctor** when you start.

| Stop | Set to |
|---|---|
| **Reception** | defaults are already the sick patient (RR 28, SpO₂ 89, BP 88, pulse 124, 39.2 °C, on oxygen, General Medicine) |
| **Doctor** | 68 · Female · 52 kg · creatinine **1.9** · UTI · **OPD** · 5 days · risk factor "Indwelling urinary catheter" · already taking Sertraline + Ramipril · **Also prescribing: empty** |
| **Pharmacy** | Levofloxacin + Linezolid · 7 days · household **MGNREGA rural daily wage** |
| **Hospital** | Dengue · Kerala · 12 months · 60 beds; second tab Escalation → **Gadchiroli**, *Myocardial infarction (STEMI)* |

---

## 0:00 – 0:25 · The problem

> *Parchi* is what every Indian patient calls the slip the doctor hands them.
>
> A government hospital OPD doctor in India sees a hundred to two hundred
> patients a day — about two minutes each. This isn't a dashboard. It follows
> **one patient through the building**: the desk that decides when they're seen,
> the doctor who decides what they get, and the counter that decides whether
> they can actually afford to take it.

---

## 0:25 – 1:15 · Reception

*(Click **Reception**.)*

> An Indian OPD is a queue. Patients travel before dawn, arrive together, and
> get seen in the order they reached the window. So the person having a heart
> attack waits behind the person with a rash.
>
> Fixing that needs no equipment. This is NEWS2 — a real, validated early
> warning score. Six measurements, ninety seconds.

*(Point at the score, then the parameter chart.)*

> This patient scores 15. Priority one, seen immediately. And you can see
> exactly why — three parameters are deranged badly enough to score three on
> their own.

*(Point at the two meters.)*

> By arrival order they'd wait. Sorted by acuity, they're seen now.

*(Scroll to the day chart.)*

> And the crush is predictable. Demand piles into 8 to 11am because people
> travel at dawn; capacity is flat all day. That mismatch **is** the queue — and
> it's visible the evening before. So the output isn't a wait time, it's a
> roster: this department needs five doctors today, not three.

---

## 1:15 – 2:15 · Doctor — the prescription

*(Click **Doctor**.)*

> Now the consult. Sixty-eight-year-old woman, urinary infection. Parchi has
> **drafted** a prescription — it never prescribes. It drafts, shows its
> working, and waits.
>
> Four checks: will it work, right dose, right length, what it costs.

*(Slow down — strongest moment in the video.)*

> Her creatinine is 1.9. Parchi computed her creatinine clearance: 23. Her
> kidneys are in severe failure, and nobody typed that in — it came from her
> age, weight, sex and one lab value.
>
> Which matters, because the standard drug for her infection is nitrofurantoin,
> and below a clearance of 30 it doesn't reach the bladder and accumulates
> instead. So it was removed **before ranking**, not flagged after.

*(Open "Why this number", then "The whole panel".)*

> Every coverage number opens up. And this is the whole surveillance panel at
> once — organisms down, drugs across. Read it by rows: *Acinetobacter* and
> *Klebsiella* are dark nearly all the way across. That's what it means to say
> India has a resistance crisis rather than a drug problem.

*(Add **Cefixime** and **Azithromycin** in the sidebar "Also prescribing".)*

> Real slips have several lines. Watch — cefixime plus azithromycin is a
> **banned** fixed-dose combination in India, and it's still prescribed daily.

---

## 2:15 – 2:50 · Pharmacy

*(Click **Pharmacy**.)*

> The slip reaches the counter. This is the last place anything can change, and
> the first place anyone finds out what it costs.
>
> As written: ₹1,456. Substituted to the identical molecules at Jan Aushadhi
> prices: ₹287. Same drugs — the prescription was just written by brand name.

*(Point at the days-of-income card.)*

> But rupees mean nothing on their own. Priced against what this household
> actually earns, the branded slip is **five and a half days of income**.
>
> That's the number that matters, because a course costing five days of earnings
> doesn't get half-taken — it gets abandoned. And a partly-taken antibiotic
> course is worse than none: it breeds resistance without curing anything.

*(Open "The shelf".)*

> And supply is a stewardship problem. Fosfomycin — the *narrowest* drug for
> this infection — has under half a month of stock. A prescriber who can't get
> the narrow drug writes the broad one, and everything upstream becomes
> theoretical.

---

## 2:50 – 3:15 · Day 3 — the step everyone skips

*(Click **Doctor** → **Day 3 · culture** tab.)*

> Forty-eight hours later the culture settles the bet. De-escalating to the
> narrowest drug that treats the actual isolate is the highest-value action in
> stewardship — and the one most reliably skipped.
>
> When the lab has reported sensitivities, that list is authoritative. It
> overrides the national estimate, because the isolate in front of you beats any
> population average.

---

## 3:15 – 4:00 · Hospital — and does the forecast work

*(Click **Hospital**.)*

> A dengue season isn't a surprise. It peaks in the same three months every
> year, and hospitals still meet it unprepared — because nobody turns an
> epidemic curve into numbers an administrator can act on.
>
> Extra OPD screens, admissions, bed-days, and platelet units. Set your bed
> count and it tells you whether you survive the peak.

*(Scroll to the backtest.)*

> And a forecast nobody has scored is an opinion. So I held out the last twelve
> months, refit on everything before, and predicted months the model had never
> seen — against the baseline every administrator already carries: assume this
> month looks like last year's.
>
> It beats that baseline on fifteen of eighteen series. **It loses on three** —
> states whose annual total jumped by an order of magnitude. That's on screen
> too. I'd rather show you where it fails.

---

## 4:00 – 4:30 · Escalation

*(Escalation tab. Gadchiroli, STEMI.)*

> Last question — the one a drug can't answer. This patient needs more than I
> have.
>
> "Nearest hospital" is the wrong question. A heart attack needs a
> catheterisation lab, not a signboard. From this sub-centre in Gadchiroli,
> the nearest facility that can actually open the artery is **over ten hours
> away**, against a two-hour window. From an equivalent facility in Kerala, it's
> twenty-one minutes.
>
> Real coordinates, live from OpenStreetMap. Capability comes from the
> facility's tier under Indian Public Health Standards — and only for public
> facilities, because open data genuinely can't tell you what a private nursing
> home can do, and I'd rather say that than make it up.

---

## 4:30 – 4:40 · Close

*(Click the **Ink theme** button — one beat, then carry on talking.)*

> Every figure here is indicative, compiled from published ICMR, WHO GLASS,
> CDSCO and NPPA patterns. That's stated on every screen, and you can upload a
> hospital's own antibiogram and the whole thing re-bases on it.
>
> Eight engines, seven screens, fifty-three tests. One idea: the data to make
> these decisions well already exists in India. It just never reaches the room
> where the decision gets made.
>
> That's Parchi.

---

## Recording notes

- **Don't narrate code.** Presentation is scored on the demo; the repo is
  linked for the technical read.
- Four strongest beats, in order: the nitrofurantoin renal block (~1:40), the
  banned FDC firing live (~2:10), five-and-a-half days of income (~2:35), and
  ten hours to a cath lab (~4:10). Slow down at each.
- The theme switch at the end is a one-second flourish. Don't dwell on it and
  don't explain it — let it land and keep talking.
- If a chart takes a beat to draw, keep talking. Never wait in silence.
- End on "That's Parchi" and stop. No trailing thanks.

## Recording setup (macOS)

QuickTime → File → New Screen Recording, or `Cmd+Shift+5`. Record the browser
window only, not the full desktop. Check the mic level on a ten-second test
before committing to a full take — bad audio sinks a good demo faster than a
bad UI does.
