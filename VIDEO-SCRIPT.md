# Demo video — 3:20

Short beats long. Judges watch dozens of these; a tight three minutes that
lands beats five minutes that wander. Max allowed is 5:00, so this leaves room
if you run slow.

**Record:** browser window only (not the desktop), 1560×1000 or larger, ~90%
zoom. `Cmd+Shift+5` on macOS. Do a ten-second mic test first — bad audio kills
a good demo faster than a bad UI does.

## Set up every screen before you hit record

| Stop | Set to |
|---|---|
| **Reception** | defaults are already the sick patient — RR 28, SpO₂ 89, BP 88, pulse 124, 39.2 °C, on oxygen, General Medicine |
| **Doctor** | 68 · Female · 52 kg · creatinine **1.9** · UTI · **OPD** · 5 days · risk factor "Indwelling urinary catheter" · **Also prescribing: leave empty** |
| **Pharmacy** | Levofloxacin + Linezolid · 7 days · household **MGNREGA rural daily wage** |
| **Hospital** | Dengue · Kerala · 12 months · 60 beds. Second tab: **Gadchiroli**, *Myocardial infarction (STEMI)* |

Start the recording on **Doctor**. Speak at a normal pace — the timings assume
about 150 words a minute.

---

## 0:00 – 0:18 · Hook

> *Parchi* is what every Indian patient calls the slip the doctor hands them.
>
> A government hospital doctor here sees up to two hundred patients a day.
> Two minutes each. And a culture test takes three days and comes out of the
> patient's own pocket — so it's usually never sent.
>
> Every antibiotic decision is a bet placed blind. This shows the odds.

---

## 0:18 – 0:50 · Reception

*(Click **Reception**.)*

> It starts before the doctor. An Indian OPD is a queue — people travel before
> dawn, arrive together, and get seen in the order they reached the window. So
> the man having a heart attack waits behind the child with a rash.
>
> Six measurements fix that. This is NEWS2, a real validated early warning
> score. This patient scores 15 — priority one, seen immediately. And you can
> see exactly why: three parameters are deranged enough to score three on their
> own.

*(Point at the two meters.)*

> By arrival order, they wait. By acuity, they're next.

---

## 0:50 – 1:40 · Doctor

*(Click **Doctor**.)*

> Now the prescription. Sixty-eight-year-old woman, urinary infection.
>
> Parchi has *drafted* — it never prescribes. It drafts, shows its working,
> and waits.

*(Slow down. This is the best moment in the video.)*

> Her creatinine is 1.9. Parchi worked out her kidney clearance: 23. She's in
> severe renal failure — and nobody typed that in. It came from her age,
> weight, sex, and one lab value.
>
> Which matters, because the standard drug for her infection is nitrofurantoin,
> and below a clearance of 30 it doesn't even reach the bladder. So it was
> removed *before* ranking. Not flagged afterwards. Removed.

*(Open **The whole panel**.)*

> And this is the problem underneath. Every organism, every drug. Read it by
> rows — *Acinetobacter*, *Klebsiella*, dark nearly all the way across. That's
> what a resistance crisis looks like from above.

*(Add **Cefixime** and **Azithromycin** in the sidebar.)*

> Real slips have several drugs. Watch — cefixime plus azithromycin is a
> *banned* combination in India. Still prescribed daily.

---

## 1:40 – 2:15 · Pharmacy

*(Click **Pharmacy**.)*

> Then the counter — the last place anything can change, and the first place
> anyone finds out what it costs.
>
> As written: fourteen hundred rupees. Same molecules at Jan Aushadhi prices:
> two hundred and eighty-seven.

*(Point at the days-of-income card.)*

> But rupees mean nothing alone. Against what this household actually earns,
> the branded slip is **five and a half days of income**.
>
> That's the number that matters. A course costing five days of earnings
> doesn't get half-taken — it gets abandoned. And a half-taken antibiotic
> course is worse than none. It breeds resistance without curing anything.

---

## 2:15 – 2:50 · Hospital, and the honest part

*(Click **Hospital**.)*

> A dengue season isn't a surprise. It peaks in the same months every year.
> This turns that curve into what an administrator can actually act on —
> bed-days, staffing, platelet units.
>
> This is real data. State-wise dengue counts published by India's health
> ministry.

*(Scroll to the backtest.)*

> And here's the part I want to show you.
>
> I held out twelve months, refit the model, and predicted months it had never
> seen. On my earlier reconstructed data it beat the baseline on fifteen of
> eighteen series.
>
> On the **real** government data, it wins about a third.
>
> The old number was measuring my own data generator, not the world. So I
> replaced the number, not the data — and wrote a test that fails the build if
> anyone tunes it to look better.

---

## 2:50 – 3:10 · Escalation

*(Escalation tab. Gadchiroli, STEMI.)*

> Last question — the one a drug can't answer. This patient needs more than I
> have.
>
> "Nearest hospital" is the wrong question. A heart attack needs a cath lab,
> not a signboard. From this sub-centre in Gadchiroli, the nearest facility
> that can actually open the artery is **over ten hours away**. The window is
> two.
>
> From an equivalent clinic in Kerala, it's twenty-one minutes. Real
> coordinates, live from OpenStreetMap.

---

## 3:10 – 3:20 · Close

*(Click **Ink theme** — one beat, don't explain it.)*

> Eight engines, seven screens, fifty-five tests.
>
> One idea: the data to make these decisions well already exists in India. It
> just never reaches the room where the decision gets made.
>
> That's Parchi.

---

## Delivery notes

- **Never narrate code.** The repo is linked; the video is for the demo.
- Four beats carry the whole video. Slow down at each and let them land:
  1. `1:05` the nitrofurantoin renal block
  2. `1:35` the banned combination firing live
  3. `2:00` five and a half days of income
  4. `3:00` ten hours to a cath lab
- The backtest admission at `2:40` is the one judges will remember. Say it
  plainly and without apology — it is a strength, not a confession.
- If a chart takes a beat to draw, keep talking. Never wait in silence.
- End on "That's Parchi" and stop recording. No sign-off, no thanks.
