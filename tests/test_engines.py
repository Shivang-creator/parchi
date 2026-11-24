"""Engine tests.

These are the invariants that matter clinically — the ones where a silent
regression would produce a confident wrong answer rather than a crash. Several
of them exist because the bug they describe actually happened during the build:
the stewardship picker recommending colistin for outpatient cystitis, the
malaria forecast collapsing to zeros, the banned-FDC checker never firing.

    python -m pytest tests -q
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from engine import coverage, data, dosing, forecast, geo, pharmacy, safety, triage


# ==========================================================================
# Data layer
# ==========================================================================
def test_every_table_loads_and_is_non_empty():
    for loader in (
        data.priors, data.drugs, data.susceptibility, data.durations,
        data.risk_factors, data.fdc_flags, data.interactions, data.renal_rules,
        data.burden, data.disease_load, data.news2_bands, data.news2_response,
        data.departments, data.opd_arrivals, data.counselling, data.pregnancy,
        data.stock, data.affordability, data.abandonment_risk,
    ):
        assert not loader().empty, loader.__name__


def test_organism_priors_sum_to_one_per_site_and_setting():
    frame = data.priors()
    totals = frame.groupby(["site", "setting"])["prior"].sum()
    assert np.allclose(totals.to_numpy(), 1.0, atol=1e-3), totals[
        ~np.isclose(totals, 1.0, atol=1e-3)
    ]


def test_susceptibility_is_a_percentage():
    values = data.susceptibility()["percent_susceptible"]
    assert values.between(0, 100).all()


def test_ventilator_pneumonia_has_no_outpatient_form():
    """A nonsense query should be impossible to ask, not answered confidently."""
    assert data.settings_for("Pneumonia — hospital / ventilator") == ["Ward", "ICU"]
    assert "OPD" in data.settings_for("Urinary tract infection")


def test_every_renal_rule_and_stock_row_names_a_real_drug():
    formulary = set(data.antibiotic_names())
    assert set(data.renal_rules()["antibiotic"]) <= formulary
    assert set(data.stock()["antibiotic"]) <= formulary
    assert set(data.counselling()["antibiotic"]) <= formulary


# ==========================================================================
# Coverage
# ==========================================================================
def test_coverage_is_a_probability_everywhere():
    for site in data.infection_sites():
        for setting in data.settings_for(site):
            for result in coverage.rank_antibiotics(site, setting):
                assert 0.0 <= result.coverage <= 1.0, (site, setting, result.antibiotic)


def test_vectorised_ranking_matches_the_scalar_path():
    """The matrix product must be arithmetic-identical to the per-organism loop."""
    factors = ["Diabetes mellitus", "Central venous line"]
    for site in data.infection_sites():
        for setting in data.settings_for(site):
            fast = {r.antibiotic: r.coverage
                    for r in coverage.rank_antibiotics(site, setting, factors)}
            for drug in list(fast)[:6]:
                slow = coverage.score_antibiotic(drug, site, setting, factors).coverage
                assert fast[drug] == pytest.approx(slow, abs=1e-12)


def test_resistance_rises_from_outpatient_to_icu():
    """Same bug, same drug, sicker setting — coverage must not improve."""
    for site in ("Urinary tract infection", "Bloodstream infection / sepsis"):
        opd = coverage.score_antibiotic("Meropenem", site, "OPD").coverage
        ward = coverage.score_antibiotic("Meropenem", site, "Ward").coverage
        icu = coverage.score_antibiotic("Meropenem", site, "ICU").coverage
        assert opd >= ward >= icu


def test_risk_factors_never_increase_coverage():
    plain = coverage.score_antibiotic("Ceftriaxone", "Intra-abdominal", "Ward").coverage
    risky = coverage.score_antibiotic(
        "Ceftriaxone", "Intra-abdominal", "Ward",
        ["Antibiotics in the last 90 days", "Known prior MDR isolate"],
    ).coverage
    assert risky <= plain


def test_risk_multiplier_has_diminishing_returns():
    """Six overlapping risk factors must not multiply to an absurdity."""
    factors = list(data.risk_factors()["factor"])
    many = coverage.risk_multiplier(factors, "OPD")
    naive = float(np.prod(data.risk_factors()["susceptibility_multiplier"]))
    assert many > naive
    assert 0.2 < many < 1.0


def test_stewardship_never_recommends_colistin_for_outpatient_cystitis():
    """The bug this whole function exists to prevent.

    Ranking by coverage alone put a nephrotoxic, IV-only, last-line polymyxin
    at the top of an outpatient urinary infection. That is precisely how
    last-line agents get burned through.
    """
    # Deliberately WITHOUT the oral-only filter. Filtering to PO would remove
    # colistin on route alone and the test would pass for the wrong reason —
    # which is exactly what it did until a mutation check caught it.
    ranked = coverage.rank_antibiotics("Urinary tract infection", "OPD")
    assert any(r.antibiotic == "Colistin" for r in ranked), "colistin must be a candidate"
    assert max(ranked, key=lambda r: r.coverage).who_aware == "Reserve", (
        "a Reserve agent should top the raw coverage ranking — that is the trap"
    )

    recommendation = coverage.stewardship_choice(ranked, "OPD")
    assert recommendation is not None
    assert recommendation.choice.antibiotic != "Colistin"
    assert recommendation.choice.who_aware != "Reserve"

    # And the same must hold for every site and setting: a Reserve agent is
    # never first-line while any non-Reserve option exists.
    for site in data.infection_sites():
        for setting in data.settings_for(site):
            candidates = coverage.rank_antibiotics(site, setting)
            if all(r.who_aware == "Reserve" for r in candidates):
                continue
            pick = coverage.stewardship_choice(candidates, setting)
            assert pick.choice.who_aware != "Reserve", (site, setting)


def test_stewardship_prefers_narrow_over_strong():
    for site in data.infection_sites():
        for setting in data.settings_for(site):
            ranked = coverage.rank_antibiotics(site, setting)
            rec = coverage.stewardship_choice(ranked, setting)
            strongest = max(ranked, key=lambda r: r.coverage)
            if rec.choice.antibiotic != strongest.antibiotic:
                # Whenever it declines the strongest agent it must be choosing
                # something genuinely narrower, not merely something different.
                assert rec.choice.spectrum <= strongest.spectrum, (site, setting)


def test_combination_beats_or_equals_its_own_members():
    site, setting = "Bloodstream infection / sepsis", "ICU"
    pair = coverage.score_combination(["Meropenem", "Colistin"], site, setting)
    for single in ("Meropenem", "Colistin"):
        assert pair.coverage >= coverage.score_antibiotic(single, site, setting).coverage


def test_two_carbapenems_add_less_than_a_polymyxin():
    """The reason combinations are scored organism-wise, not independently.

    Under 1 - prod(1 - p) a second carbapenem would look valuable. It is not:
    both fail on the same carbapenemase.
    """
    site, setting = "Bloodstream infection / sepsis", "ICU"
    duplicate = coverage.score_combination(
        ["Meropenem", "Imipenem-Cilastatin"], site, setting).coverage
    complementary = coverage.score_combination(
        ["Meropenem", "Colistin"], site, setting).coverage
    assert complementary > duplicate


def test_intrinsic_resistance_is_scored_as_zero_cover():
    """Absent pairs are the model working, not missing data."""
    lookup = coverage._matrix("ICU", data.LATEST_YEAR)
    organism_index, columns, matrix = lookup
    impossible = [
        ("Escherichia coli", "Vancomycin"),      # glycopeptide vs gram-negative
        ("Staphylococcus aureus", "Colistin"),   # polymyxin vs gram-positive
        ("Enterococcus spp", "Ceftriaxone"),     # intrinsic cephalosporin resistance
        ("Proteus mirabilis", "Nitrofurantoin"),  # intrinsic
        ("Pseudomonas aeruginosa", "Ertapenem"),  # no useful activity
        ("Atypical pathogens", "Amoxicillin"),   # no cell wall to attack
    ]
    for organism, drug in impossible:
        assert matrix[organism_index[organism], columns.index(drug)] == 0.0, (
            f"{drug} should have no activity against {organism}"
        )


def test_deescalation_refuses_to_narrow_without_a_lab_report():
    """Narrowing on population statistics alone is a guess, not a recommendation."""
    blind = coverage.deescalate("Acinetobacter baumannii", "Meropenem", "ICU")
    assert not blind.lab_confirmed
    confirmed = coverage.deescalate(
        "Escherichia coli", "Meropenem", "ICU",
        lab_susceptible_to=["Nitrofurantoin", "Amikacin"],
    )
    assert confirmed.lab_confirmed
    assert confirmed.recommended in ("Nitrofurantoin", "Amikacin")
    assert confirmed.spectrum_saved > 0


def test_active_agents_excludes_the_inactive():
    agents = coverage.active_agents("Bacteroides fragilis", "Ward")
    assert "Metronidazole" in agents
    assert "Amikacin" not in agents      # aminoglycosides are inactive on anaerobes


def test_expiry_reports_a_past_crossing_as_past():
    trend = coverage.coverage_trend("Ciprofloxacin", "Urinary tract infection", "OPD")
    _, expiry = coverage.project_expiry(trend, threshold=50.0)
    assert expiry is not None and expiry <= data.LATEST_YEAR


# ==========================================================================
# Dosing
# ==========================================================================
def test_cockcroft_gault_matches_a_worked_example():
    patient = dosing.Patient(age=68, sex="Female", weight_kg=52,
                             serum_creatinine=1.9)
    expected = ((140 - 68) * 52 * 0.85) / (72 * 1.9)
    assert dosing.cockcroft_gault(patient) == pytest.approx(round(expected, 1))


def test_female_clearance_is_the_documented_fraction_of_male():
    kw = dict(age=50, weight_kg=70, serum_creatinine=1.0)
    male = dosing.cockcroft_gault(dosing.Patient(sex="Male", **kw))
    female = dosing.cockcroft_gault(dosing.Patient(sex="Female", **kw))
    assert female == pytest.approx(male * 0.85, abs=0.15)


def test_nitrofurantoin_is_contraindicated_below_the_published_threshold():
    poor = dosing.Patient(age=80, sex="Female", weight_kg=45, serum_creatinine=2.6)
    assert dosing.cockcroft_gault(poor) < 30
    assert dosing.dose_for("Nitrofurantoin", poor).blocked

    good = dosing.Patient(age=30, sex="Male", weight_kg=70, serum_creatinine=0.9)
    assert dosing.cockcroft_gault(good) > 30
    assert not dosing.dose_for("Nitrofurantoin", good).blocked


def test_dose_fraction_never_exceeds_normal_and_is_monotone_in_clearance():
    for drug in data.antibiotic_names():
        previous = 0.0
        for creatinine in (6.0, 3.0, 1.6, 0.9):        # improving renal function
            patient = dosing.Patient(age=60, sex="Male", weight_kg=70,
                                     serum_creatinine=creatinine)
            fraction = dosing.dose_for(drug, patient).dose_fraction
            assert 0.0 <= fraction <= 1.0
            assert fraction >= previous - 1e-9, drug
            previous = fraction


def test_every_drug_doses_for_extreme_patients():
    extremes = [
        dosing.Patient(age=0, sex="Female", weight_kg=2.5, serum_creatinine=0.2),
        dosing.Patient(age=110, sex="Male", weight_kg=200, serum_creatinine=15.0),
    ]
    for patient in extremes:
        for drug in data.antibiotic_names():
            result = dosing.dose_for(drug, patient)
            assert result.crcl >= 0
            assert dosing.course_cost(drug, 7, result.dose_fraction).best_total >= 0


def test_paediatric_dosing_is_weight_based():
    small = dosing.Patient(age=4, sex="Male", weight_kg=15, serum_creatinine=0.4)
    assert dosing.dose_for("Amoxicillin", small).is_paediatric
    assert "mg/kg" in dosing.dose_for("Amoxicillin", small).dose_text


def test_duration_advice_flags_the_classic_overlong_course():
    advice = dosing.duration_advice("Pneumonia — community acquired", 10)
    assert advice.verdict == "TOO LONG"
    assert advice.excess_days == 10 - advice.typical
    assert dosing.duration_advice("Bloodstream infection / sepsis", 7).verdict == "APPROPRIATE"


# ==========================================================================
# Safety
# ==========================================================================
def test_banned_fdc_fires_across_a_multi_drug_slip():
    """It could never fire while the UI passed a single drug."""
    alerts = safety.check_combinations(["Cefixime", "Azithromycin"])
    assert any(a.severity == "BANNED" for a in alerts)
    assert not safety.check_combinations(["Cefixime"])


def test_interaction_matches_a_molecule_against_a_class():
    """A chart says "sertraline"; the table says "SSRI"."""
    alerts = safety.check_interactions(["Linezolid"], ["Tab Sertraline 50 mg"])
    assert any("SSRI" in a.title for a in alerts)


def test_moderate_interactions_are_suppressed_by_default():
    quiet = safety.check_interactions(["Cotrimoxazole"], ["Tab Ramipril 5 mg"])
    loud = safety.check_interactions(["Cotrimoxazole"], ["Tab Ramipril 5 mg"],
                                     include_moderate=True)
    assert len(quiet) < len(loud)


def test_a_clean_prescription_produces_no_alerts():
    assert safety.run_all(["Nitrofurantoin"], ["Tab Metformin 500 mg"]) == []


# ==========================================================================
# Triage
# ==========================================================================
def test_news2_scores_a_well_patient_at_zero():
    assert triage.score(16, 98, 120, 70, 36.8).score == 0


def test_news2_escalates_on_any_single_parameter_scoring_three():
    """The rule most implementations get wrong."""
    result = triage.score(18, 97, 118, 88, 36.6, "Responds to voice")
    assert result.score == 3
    assert result.band == "Medium"          # not "Low", despite the low total
    assert result.red_flags


def test_news2_monotonic_in_derangement():
    mild = triage.score(20, 95, 112, 95, 37.9).score
    severe = triage.score(30, 88, 85, 135, 39.5).score
    assert severe > mild


def test_triage_priority_orders_correctly():
    sick = triage.score(30, 86, 82, 132, 39.6, "Confusion (new)", on_oxygen=True)
    well = triage.score(16, 99, 122, 72, 36.7)
    assert sick.priority < well.priority        # 1 is seen first


def test_news2_reading_between_two_bands_is_not_scored_as_extreme():
    """Regression: a finer-than-chart reading fell in the gap between two
    published bands (20 < 20.5 < 21) and was scored 3, the out-of-range value."""
    well = triage.score(20.4, 96.4, 119.5, 90.4, 38.04)
    assert well.score == 0 and not well.red_flags, [
        (o.parameter, o.points) for o in well.observations
    ]
    assert triage.score(16, 98, 120, 80, 36.05).score <= 1
    # Genuinely out-of-range values still score the maximum.
    assert triage.score(4, 98, 120, 80, 37.0).red_flags
    assert triage.score(16, 98, 120, 80, 34.96).red_flags


def test_simulated_waiting_room_is_mostly_well():
    """16% of the simulated room is drawn sick; the band gaps used to push
    more than half of it to Medium or High."""
    queue = triage.synthetic_queue(200)
    urgent = queue["band"].isin(["Medium", "High"]).mean()
    assert urgent < 0.35, urgent


def test_queue_sorts_by_acuity_not_arrival():
    queue = triage.synthetic_queue(80)
    ordered = queue.sort_values(["priority", "arrived"])
    assert ordered["priority"].is_monotonic_increasing
    # Somebody must actually overtake, or the sort is doing nothing.
    assert (ordered["arrived"].to_numpy() != np.arange(len(ordered))).any()


def test_more_doctors_never_lengthen_the_queue():
    previous = math.inf
    for doctors in range(1, 8):
        wait = triage.expected_wait_minutes("General Medicine", 60, doctors)
        assert wait <= previous
        previous = wait


def test_staffing_recommendation_actually_meets_the_target():
    needed = triage.staffing_to_clear(900, "General Medicine", 60)
    projection = triage.day_projection(900, "General Medicine")
    assert needed >= 1
    # The rostered establishment is not enough, which is the finding.
    assert projection["wait_minutes"].max() > 60


# ==========================================================================
# Pharmacy
# ==========================================================================
def test_substitution_never_costs_more_than_the_brand():
    for drug in data.antibiotic_names():
        line = pharmacy.substitute(drug, 7)
        assert line.cheapest_total <= line.brand_total
        assert line.saving >= 0


def test_affordability_is_relative_to_income_not_absolute():
    """The same bill is routine for one household and catastrophic for another."""
    poor = pharmacy.affordability(1400, "MGNREGA rural daily wage")
    rich = pharmacy.affordability(1400, "Salaried urban (median)")
    assert poor.days_of_income > rich.days_of_income
    assert poor.risk == "Catastrophic"
    assert rich.risk in ("Low", "Moderate")


def test_pregnancy_flags_the_contraindicated_agents():
    review = pharmacy.review([("Doxycycline", 7, 1.0), ("Amoxicillin", 7, 1.0)],
                             pregnant=True)
    flagged = {name: category for name, category, _ in review.pregnancy_flags}
    assert flagged.get("Doxycycline") == "Avoid"
    assert "Amoxicillin" not in flagged          # safe, must not cry wolf


def test_pregnancy_checks_are_off_when_not_pregnant():
    review = pharmacy.review([("Doxycycline", 7, 1.0)], pregnant=False)
    assert review.pregnancy_flags == []


def test_stock_pressure_is_sorted_worst_first():
    rows = pharmacy.stock_pressure()
    covers = [r["months_of_cover"] for r in rows]
    assert covers == sorted(covers)


# ==========================================================================
# Forecast
# ==========================================================================
def test_no_series_collapses_to_zero():
    """A linear fit on declining malaria used to extrapolate below zero."""
    for disease in data.diseases():
        for state in data.states(disease):
            frame = forecast.forecast_months(state, disease, 24)
            assert frame["cases"].max() > 0, (disease, state)
            assert (frame["cases"] >= 0).all()


def test_seasonal_index_is_a_distribution():
    for disease in data.diseases():
        for state in data.states(disease)[:4]:
            index = forecast.seasonal_index(state, disease)
            assert len(index) == 12
            assert index.sum() == pytest.approx(1.0)


def test_dengue_peaks_post_monsoon():
    """Sanity check on the applied profile, not evidence about the model."""
    index = forecast.seasonal_index("Kerala", "Dengue")
    assert int(index.idxmax()) in (9, 10, 11)


def test_uncertainty_band_contains_the_point_estimate():
    frame = forecast.forecast_months("Kerala", "Dengue", 12)
    assert (frame["lower"] <= frame["cases"]).all()
    assert (frame["cases"] <= frame["upper"]).all()


def test_backtest_runs_and_reports_honestly_on_real_data():
    """The model does NOT beat the naive baseline on most real series.

    On the reconstructed data this project shipped with earlier it won 15 of
    18. Swapping in the real NCVBDC national series, it wins about a third —
    because real dengue is a boom-bust series (a 2023 national peak, then a
    48% fall by 2025) that a damped trend cannot anticipate, and because
    'same month last year' is a genuinely strong baseline for a seasonal
    disease.

    This test asserts the honest range rather than a flattering one, so that
    tuning the model to look good in the demo breaks the build.
    """
    wins = total = 0
    for disease in data.diseases():
        for state in data.states(disease):
            scored = forecast.backtest(state, disease)
            if not scored:
                continue
            total += 1
            assert scored["model_mape"] >= 0
            assert scored["naive_mape"] >= 0
            wins += bool(scored["beats_naive"])
    assert total > 30
    assert 0.2 < wins / total < 0.85, (
        f"beat the baseline on {wins}/{total} — outside the range this model "
        f"honestly achieves; check whether the metric has been gamed"
    )


def test_peak_month_accuracy_is_never_reported_as_validation():
    """Seasonality is applied, not observed, so recovering it proves nothing.

    Real data supplies annual totals; the build step distributes them by a
    fixed documented profile. Any 'we predict the peak month' claim would be
    a round trip. The key is named to make that impossible to quote by
    accident.
    """
    scored = forecast.backtest("Kerala", "Dengue")
    assert "peak_month_correct" not in scored
    assert "peak_month_correct_CIRCULAR" in scored


def test_dengue_burden_is_real_and_the_others_are_labelled():
    assert forecast.is_real("Dengue")
    assert forecast.source_of("Dengue") == "NCVBDC"
    for disease in data.diseases():
        if disease != "Dengue":
            assert not forecast.is_real(disease)


def test_disease_load_differs_by_disease():
    """Malaria fills beds; dengue also eats platelets."""
    dengue = forecast.SurgeAssumptions.for_disease("Dengue")
    malaria = forecast.SurgeAssumptions.for_disease("Malaria")
    assert dengue.platelet_transfusion_rate > malaria.platelet_transfusion_rate


# ==========================================================================
# Geo
# ==========================================================================
def test_haversine_against_a_known_distance():
    """Delhi to Mumbai is about 1,150 km."""
    km = geo.haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1100 < km < 1200


def test_nearest_facility_is_never_the_origin_itself():
    frame = geo.facilities()
    if frame.empty:
        pytest.skip("no facility extract present")
    for row in frame.head(40).itertuples():
        result = geo.assess(float(row.latitude), float(row.longitude),
                            "Severe trauma", exclude_name=row.name)
        assert result.minutes_to_any > 0


def test_capability_is_only_inferred_for_public_tiers():
    frame = geo.facilities()
    if frame.empty:
        pytest.skip("no facility extract present")
    private = frame[frame["tier"] == "Private Clinic / Nursing home"]
    assert (private["capabilities"].fillna("") == "").all()


def test_reachability_respects_the_clock():
    frame = geo.facilities()
    if frame.empty:
        pytest.skip("no facility extract present")
    row = frame.iloc[0]
    for emergency, spec in geo.EMERGENCIES.items():
        result = geo.assess(float(row.latitude), float(row.longitude), emergency)
        if result.nearest_capable is not None:
            assert result.reachable == (result.minutes_to_capable <= spec["window_min"])


def test_contraindicated_paediatric_dose_is_a_refusal_not_zero_milligrams():
    child = dosing.Patient(age=8, sex="Male", weight_kg=25, serum_creatinine=3.0)
    result = dosing.dose_for("Nitrofurantoin", child)
    assert result.blocked
    assert result.dose_text == "Do not administer"


def test_agent_without_a_paediatric_dose_never_prints_zero_milligrams():
    child = dosing.Patient(age=6, sex="Female", weight_kg=20, serum_creatinine=0.5)
    for name in data.antibiotic_names():
        if float(data.drug_row(name)["peds_mg_per_kg_per_day"]) > 0:
            continue
        text = dosing.dose_for(name, child).dose_text
        assert "0 mg" not in text, (name, text)
        assert "No paediatric dose" in text


def test_short_class_tokens_do_not_match_inside_other_drug_names():
    """'ace' is in paracetamol and 'arb' is in carbonate; neither is an ACE
    inhibitor or an ARB."""
    for meds in (["Tab Paracetamol 650 mg"], ["Tab Calcium carbonate 500 mg"]):
        titles = [a.title for a in safety.check_interactions(["Cotrimoxazole"], meds, True)]
        assert not any("ACE" in t for t in titles), (meds, titles)
    # The real pairing still fires, by class word and by molecule.
    for meds in (["ACE inhibitor"], ["Tab Ramipril 5 mg"], ["Tab Telmisartan 40"]):
        titles = [a.title for a in safety.check_interactions(["Cotrimoxazole"], meds, True)]
        assert any("ACE" in t for t in titles), (meds, titles)


# ==========================================================================
# Antibiogram override
# ==========================================================================
def test_uploading_an_antibiogram_rebases_every_engine():
    before = coverage.rank_antibiotics("Urinary tract infection", "OPD")[0].coverage
    frame = data.susceptibility().copy()
    frame["percent_susceptible"] = 5.0
    ok, _ = data.load_antibiogram(frame)
    assert ok
    try:
        after = coverage.rank_antibiotics("Urinary tract infection", "OPD")[0].coverage
        assert after < before, "derived caches were not invalidated"
    finally:
        data.clear_antibiogram()
    restored = coverage.rank_antibiotics("Urinary tract infection", "OPD")[0].coverage
    assert restored == pytest.approx(before)


def test_a_bad_upload_is_rejected_without_raising():
    import pandas as pd

    ok, message = data.load_antibiogram(pd.DataFrame({"nonsense": [1, 2]}))
    assert not ok and "Missing required column" in message
    assert not data.using_custom_antibiogram()


def test_one_sessions_antibiogram_is_invisible_to_every_other_session():
    """Regression: the override was a module global, so on the public server one
    visitor's upload replaced the resistance data for every other visitor.
    Each Streamlit session runs its script on its own thread."""
    import threading

    national = coverage.rank_antibiotics("Urinary tract infection", "OPD")[0].coverage
    seen: dict[str, object] = {}
    uploaded, checked = threading.Event(), threading.Event()

    def uploader():
        frame = data.susceptibility().copy()
        frame["percent_susceptible"] = 5.0
        assert data.load_antibiogram(frame)[0]
        seen["uploader"] = coverage.rank_antibiotics(
            "Urinary tract infection", "OPD")[0].coverage
        seen["handle"] = data.current_antibiogram()
        uploaded.set()
        checked.wait(5)

    def bystander():
        uploaded.wait(5)
        seen["bystander_custom"] = data.using_custom_antibiogram()
        seen["bystander"] = coverage.rank_antibiotics(
            "Urinary tract infection", "OPD")[0].coverage
        checked.set()

    threads = [threading.Thread(target=uploader), threading.Thread(target=bystander)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)

    assert seen["uploader"] < national
    assert seen["bystander_custom"] is False
    assert seen["bystander"] == pytest.approx(national)

    # The uploading session gets its table back on its next run, by handle.
    assert not data.using_custom_antibiogram()
    data.use_antibiogram(seen["handle"])
    try:
        assert coverage.rank_antibiotics(
            "Urinary tract infection", "OPD")[0].coverage == pytest.approx(seen["uploader"])
    finally:
        data.use_antibiogram(None)


def test_antibiogram_with_numeric_names_does_not_break_the_organism_picker():
    frame = data.susceptibility().head(50).copy()
    frame["organism"] = frame["organism"].astype(object)
    frame.loc[frame.index[0], "organism"] = 12345
    assert data.load_antibiogram(frame)[0]
    try:
        assert all(isinstance(name, str) for name in data.organisms())
    finally:
        data.clear_antibiogram()
