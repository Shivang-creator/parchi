"""The pharmacy counter — where a prescription becomes a bill.

This is the last place anything can be changed, and the only place anyone
finds out what the slip actually costs. Medicines are the largest single
component of Indian out-of-pocket health spending, and out-of-pocket spending
is the mechanism by which illness becomes poverty.

Four things happen here that nowhere else in the building can do:

    substitute   the identical molecule at a fraction of the price
    price        the whole slip against what this household actually earns
    stock        say plainly when the narrow drug is not on the shelf
    counsel      the free, evidence-based part of dispensing that is skipped

The affordability model matters most. A course that costs four days of income
does not get half-taken — it gets abandoned, and a partial antibiotic course is
worse than none, because it selects for resistance without curing anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import data


# --------------------------------------------------------------------------
# Substitution
# --------------------------------------------------------------------------
@dataclass
class Substitution:
    antibiotic: str
    days: int
    units: float
    brand_total: float
    generic_total: float
    janaushadhi_total: float
    janaushadhi_available: bool
    in_stock: bool
    stock_units: int
    months_of_cover: float

    @property
    def cheapest_total(self) -> float:
        return (self.janaushadhi_total if self.janaushadhi_available
                else self.generic_total)

    @property
    def cheapest_tier(self) -> str:
        return "Jan Aushadhi" if self.janaushadhi_available else "generic"

    @property
    def saving(self) -> float:
        return round(self.brand_total - self.cheapest_total, 2)

    @property
    def multiple(self) -> float:
        if self.cheapest_total <= 0:
            return 0.0
        return round(self.brand_total / self.cheapest_total, 1)


def substitute(antibiotic: str, days: int, dose_fraction: float = 1.0) -> Substitution:
    meta = data.drug_row(antibiotic)
    doses = int(meta["doses_per_day"])
    units = doses * days * max(dose_fraction, 0.0)
    ja_price = float(meta["price_janaushadhi"])

    stock_table = data.stock()
    stock_row = stock_table[stock_table["antibiotic"] == antibiotic]
    on_hand = int(stock_row.iloc[0]["units_in_stock"]) if not stock_row.empty else 0
    monthly = float(stock_row.iloc[0]["monthly_consumption"]) if not stock_row.empty else 0.0

    return Substitution(
        antibiotic=antibiotic,
        days=days,
        units=units,
        brand_total=round(float(meta["price_brand"]) * units, 2),
        generic_total=round(float(meta["price_generic"]) * units, 2),
        janaushadhi_total=round(ja_price * units, 2),
        janaushadhi_available=ja_price > 0,
        in_stock=on_hand >= units,
        stock_units=on_hand,
        months_of_cover=round(on_hand / monthly, 1) if monthly else float("inf"),
    )


# --------------------------------------------------------------------------
# Affordability
# --------------------------------------------------------------------------
@dataclass
class Affordability:
    total_inr: float
    daily_income: float
    days_of_income: float
    risk: str
    guidance: str
    reference: str

    @property
    def is_catastrophic(self) -> bool:
        return self.risk == "Catastrophic"


def affordability(total_inr: float, reference: str) -> Affordability:
    """Price the slip in days of this household's income, not in rupees.

    A rupee figure is meaningless on its own. The same ₹1,400 course is a
    routine expense for a salaried household and five days of earnings for a
    family on the rural employment guarantee wage — and the second one does not
    get completed.
    """
    table = data.affordability()
    row = table[table["reference"] == reference]
    daily = float(row.iloc[0]["daily_income_inr"]) if not row.empty else 350.0
    days = total_inr / daily if daily else 0.0

    bands = data.abandonment_risk()
    hit = bands[(bands["days_of_income_min"] <= days)
                & (days < bands["days_of_income_max"])]
    hit = hit.iloc[0] if not hit.empty else bands.iloc[-1]

    return Affordability(
        total_inr=round(total_inr, 2),
        daily_income=daily,
        days_of_income=round(days, 2),
        risk=str(hit["risk"]),
        guidance=str(hit["guidance"]),
        reference=reference,
    )


# --------------------------------------------------------------------------
# Dispensing checks
# --------------------------------------------------------------------------
@dataclass
class DispensingReview:
    lines: list[Substitution] = field(default_factory=list)
    brand_total: float = 0.0
    cheapest_total: float = 0.0
    out_of_stock: list[str] = field(default_factory=list)
    pregnancy_flags: list[tuple[str, str, str]] = field(default_factory=list)
    counselling: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def saving(self) -> float:
        return round(self.brand_total - self.cheapest_total, 2)

    @property
    def saving_pct(self) -> float:
        if self.brand_total <= 0:
            return 0.0
        return round(self.saving / self.brand_total * 100, 1)


def review(
    items: list[tuple[str, int, float]],
    pregnant: bool = False,
) -> DispensingReview:
    """Everything the counter should check before money changes hands.

    `items` is (antibiotic, days, dose_fraction) — the whole slip, not one line,
    because the patient pays for all of it at once and abandons all of it at
    once too.
    """
    result = DispensingReview()
    preg_table = data.pregnancy().set_index("antibiotic")
    counsel_table = data.counselling().set_index("antibiotic")

    for name, days, fraction in items:
        try:
            line = substitute(name, days, fraction)
        except KeyError:
            continue
        result.lines.append(line)
        result.brand_total += line.brand_total
        result.cheapest_total += line.cheapest_total
        if not line.in_stock:
            result.out_of_stock.append(name)

        if pregnant and name in preg_table.index:
            row = preg_table.loc[name]
            if str(row["category"]) in ("Avoid", "Caution"):
                result.pregnancy_flags.append(
                    (name, str(row["category"]), str(row["note"]))
                )

        if name in counsel_table.index:
            row = counsel_table.loc[name]
            result.counselling.append((name, str(row["timing"]), str(row["advice"])))

    result.brand_total = round(result.brand_total, 2)
    result.cheapest_total = round(result.cheapest_total, 2)
    return result


def stock_pressure() -> "list[dict]":
    """Which shelves are about to empty, worst first.

    Stock-outs of the cheap narrow agents are the quiet reason broad-spectrum
    drugs get used: a prescriber who cannot get nitrofurantoin writes a
    fluoroquinolone, and the stewardship advice upstream becomes theoretical.
    """
    table = data.stock().merge(data.drugs(), on="antibiotic", how="left")
    rows = []
    for _, row in table.iterrows():
        monthly = float(row["monthly_consumption"])
        on_hand = int(row["units_in_stock"])
        cover = on_hand / monthly if monthly else float("inf")
        rows.append({
            "antibiotic": str(row["antibiotic"]),
            "spectrum": int(row["spectrum"]),
            "aware": str(row["who_aware"]),
            "units_in_stock": on_hand,
            "monthly_consumption": monthly,
            "months_of_cover": round(cover, 2),
            "status": ("stock-out risk" if cover < 1.0
                       else "low" if cover < 1.5 else "adequate"),
        })
    rows.sort(key=lambda r: r["months_of_cover"])
    return rows
