"""The Financials emulator produces what Pillar E needs — D97.

The organising question: **could a build that got `direction` wrong pass these tests?**

It could not, and that is the point of the corpus containing a cost measure by default
rather than as an option. A revenue-only corpus would let a product assume
higher-is-better everywhere and stay green all the way to a customer's chart.
"""
from __future__ import annotations

import json
from datetime import date

from contract.markers import SYNTHETIC_MARKER_FIELD, SYNTHETIC_MARKER_VALUE

from pseudofin.emit import ENTITY_FILES, emit
from pseudofin.generator import MEASURES, Corpus, Parameters, generate, periods
from pseudofin.scenarios import inject_bad_year, inject_sole_metric


def small() -> Parameters:
    return Parameters(units=4, history_end=date(2025, 12, 31))


class TestReproducibility:
    def test_the_same_seed_produces_byte_identical_output(self):
        """Document 10 §3 — the harness's central claim. Everything downstream that
        pins a count depends on it."""
        first = json.dumps(generate(small()).business_unit_metrics, sort_keys=True)
        second = json.dumps(generate(small()).business_unit_metrics, sort_keys=True)
        assert first == second

    def test_a_different_seed_produces_different_output(self):
        """The guard against the guard: if the seed did nothing, the test above would
        pass against a generator that returned a constant."""
        a = json.dumps(generate(Parameters(units=4, seed=1)).business_unit_metrics,
                       sort_keys=True)
        b = json.dumps(generate(Parameters(units=4, seed=2)).business_unit_metrics,
                       sort_keys=True)
        assert a != b

    def test_it_does_not_touch_the_global_random_generator(self):
        """A corpus built after any other code touched the shared RNG would not
        reproduce, and the failure would look like flakiness rather than a defect."""
        import random

        random.seed(1)
        before = random.random()
        random.seed(1)
        generate(small())
        assert random.random() == before


class TestDirectionIsPartOfTheDefinition:
    def test_a_cost_measure_is_present_by_default(self):
        """**Not optional, and this is the test that says why.**

        A corpus of revenue-like measures only would let a product assume
        higher-is-better everywhere and stay green — right up to the customer's chart,
        where every well-run cost centre sits in the underperforming quadrant.
        """
        directions = {d for _, _, d, _ in MEASURES}
        assert directions == {"HIGHER_IS_BETTER", "LOWER_IS_BETTER"}
        corpus = generate(small())
        assert any(m["direction"] == "LOWER_IS_BETTER"
                   for m in corpus.business_unit_metrics)

    def test_every_metric_states_a_direction(self):
        for metric in generate(small()).business_unit_metrics:
            assert metric["direction"] in ("HIGHER_IS_BETTER", "LOWER_IS_BETTER")

    def test_no_plan_is_zero(self):
        """The ratio half of D92 divides by it. The schema refuses zero, so a harness
        emitting one would fail at ingestion for a reason nobody could see from here."""
        assert all(m["plan"] != 0 for m in generate(small()).business_unit_metrics)


class TestThePeriodConvention:
    def test_periods_do_not_overlap_and_leave_no_gap(self):
        found = periods(small())
        assert found
        for earlier, later in zip(found, found[1:]):
            assert later[0].toordinal() == earlier[1].toordinal() + 1, (
                "periods must abut exactly — a gap loses a quarter and an overlap "
                "counts one twice"
            )

    def test_period_end_is_inclusive(self):
        """The last day the period covers, like `exit_date` and unlike `valid_to`.
        D67 was caused by conflating those two kinds of date in the other direction."""
        first = periods(small())[0]
        assert first == (date(2024, 1, 1), date(2024, 3, 31))


class TestTheBadYear:
    def test_every_unit_misses_plan_and_the_range_is_as_stated(self):
        """**The D92 scenario.** Standardised, this looks like an ordinary year."""
        corpus = generate(small())
        result = inject_bad_year(corpus, year=2025)
        assert result["units_affected"] == 4
        assert result["worst_shortfall"] == 0.42
        assert result["best_shortfall"] == 0.18

        for metric in corpus.business_unit_metrics:
            if date.fromisoformat(metric["period_start"]).year != 2025:
                continue
            if metric["direction"] == "HIGHER_IS_BETTER":
                assert metric["actual"] < metric["plan"]
            else:
                assert metric["actual"] > metric["plan"], (
                    "a cost above plan IS a miss — pushing every actual the same way "
                    "would hand the cost centres a triumphant year mid-disaster"
                )

    def test_the_standardised_picture_flattens_and_that_is_the_finding(self):
        """The claim D92 rests on, checked rather than asserted.

        After a bad year every unit is far below plan, yet the SPREAD of shortfalls is
        ordinary — so a z-score across them places units in unremarkable positions. The
        plain percentage is the only thing that still says everyone missed.
        """
        corpus = generate(small())
        inject_bad_year(corpus, year=2025)
        revenue = [m for m in corpus.business_unit_metrics
                   if m["metric_key"] == "net_revenue"
                   and date.fromisoformat(m["period_start"]).year == 2025]
        deviations = [(m["actual"] - m["plan"]) / abs(m["plan"]) for m in revenue]
        assert max(deviations) < -0.17, "every unit is well below plan"
        mean = sum(deviations) / len(deviations)
        centred = [d - mean for d in deviations]
        assert min(centred) < 0 < max(centred), (
            "centred on their own mean the units sit either side of zero — which is "
            "exactly the healthy-looking scatter D92 warns about"
        )

    def test_a_year_with_no_data_reports_zero_rather_than_pretending(self):
        result = inject_bad_year(generate(small()), year=1999)
        assert result["metrics_adjusted"] == 0

    def test_the_base_corpus_does_not_already_contain_a_bad_year(self):
        """Injected, never generated. If the base corpus already had it, every fixture
        would change shape and no test could say the behaviour depends on it."""
        corpus = generate(small())
        revenue = [m for m in corpus.business_unit_metrics
                   if m["metric_key"] == "net_revenue"]
        assert any(m["actual"] >= m["plan"] for m in revenue)


class TestTheSoleMetric:
    def test_a_measure_only_one_unit_carries_cannot_be_standardised(self):
        corpus = generate(small())
        result = inject_sole_metric(corpus, unit_code="CC-001")
        assert result["rows_added"] > 0
        holders = {m["source_unit_id"] for m in corpus.business_unit_metrics
                   if m["metric_key"] == "regulatory_levy"}
        assert holders == {"PSEUDO::CC-001"}, (
            "exactly one unit carries it, which is what makes the group unstandardisable"
        )


class TestIdentifiersAreThisSystemsOwn:
    def test_cost_centre_codes_are_invented_unless_supplied(self):
        """A finance system's cost centre and an HCM's org unit are not automatically
        the same thing. D56 put that inference out of scope, so the default must not
        quietly agree with the HCM."""
        corpus = generate(small())
        codes = {m["source_unit_id"] for m in corpus.business_unit_metrics}
        assert all(c.endswith(("001", "002", "003", "004")) for c in codes)
        assert all("CC-" in c for c in codes)

    def test_supplied_codes_are_used_verbatim(self):
        corpus = generate(Parameters(units=2, org_unit_codes=("OU-7", "OU-9"),
                                     history_end=date(2024, 6, 30)))
        codes = {m["source_unit_id"] for m in corpus.business_unit_metrics}
        assert codes == {"PSEUDO::OU-7", "PSEUDO::OU-9"}


class TestStrategicPriorities:
    def test_at_least_one_priority_has_no_statement(self):
        """A priority recorded only as a label supports the weakest linkage confidence,
        and D24 then suppresses rather than scores low. A corpus where every priority
        is richly written never exercises that path."""
        priorities = generate(small()).strategic_priorities
        assert any(p["statement"] is None for p in priorities)

    def test_a_missing_statement_is_null_and_never_an_empty_string(self):
        """An empty string satisfies a NOT NULL check while carrying nothing, which is
        how emptiness comes to be scored as content. The schema refuses it."""
        for priority in generate(small()).strategic_priorities:
            assert priority["statement"] != ""

    def test_one_priority_is_unranked(self):
        """Unranked is a real state and must not sort to last: an organisation that
        declines to rank its priorities is making a statement."""
        priorities = generate(small()).strategic_priorities
        assert any(p["stated_rank"] is None for p in priorities)


class TestUnstatedComparabilityExists:
    def test_some_rows_leave_comparability_unstated(self):
        """Null must never read as true. Pillar E's third hypothesis is that the metric
        is the wrong measure for a unit, and only the customer can settle it."""
        corpus = generate(Parameters(units=8, history_end=date(2026, 12, 31)))
        values = {m["comparable_across_units"] for m in corpus.business_unit_metrics}
        assert None in values and True in values


class TestTheMarker:
    def test_every_emitted_record_carries_it(self):
        """Gate 7's half of the poison pill. The product's own tests prove the refusal
        works, never that the stamp was applied."""
        corpus = generate(small())
        inject_bad_year(corpus, year=2025)
        inject_sole_metric(corpus, unit_code="CC-002")
        for attribute in ENTITY_FILES.values():
            rows = getattr(corpus, attribute)
            assert rows, f"{attribute} is empty — this check would pass by vacancy"
            for row in rows:
                assert row[SYNTHETIC_MARKER_FIELD] == SYNTHETIC_MARKER_VALUE

    def test_identifiers_are_moved_into_the_reserved_namespace(self):
        for metric in generate(small()).business_unit_metrics:
            assert metric["metric_id"].startswith("PSEUDO::")


class TestEmission:
    def test_every_entity_gets_a_file_even_when_empty(self, tmp_path):
        written = emit(Corpus(), tmp_path)
        assert set(written) == set(ENTITY_FILES)
        for entity in ENTITY_FILES:
            assert (tmp_path / f"{entity}.jsonl").exists(), (
                "absent and empty say different things to whoever is loading them")

    def test_the_files_round_trip(self, tmp_path):
        corpus = generate(small())
        written = emit(corpus, tmp_path)
        lines = (tmp_path / "BusinessUnitMetric.jsonl").read_text(
            encoding="utf-8").splitlines()
        assert len(lines) == written["BusinessUnitMetric"]
        assert json.loads(lines[0])["direction"] in ("HIGHER_IS_BETTER",
                                                     "LOWER_IS_BETTER")
