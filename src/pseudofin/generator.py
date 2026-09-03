"""Deterministic generation — pseudofin, the Financials emulator.

Same rule as `pseudohcm`: the output is not a claim about the world. It is the
reproducible result of a published rule set with stated parameters. Same seed, same
parameters, byte-identical output.

**THE DOMAIN, NEVER A VENDOR'S SCHEMA — D91.**

Nothing here is modelled on any particular financial system's tables, field names or
documentation. What is modelled is what every financial system holds in some form: a
unit, a measure, a period, a planned number and an actual one. Field mappings for a
real product are authored from that product's own published documentation, under that
product's terms, at the point an engagement requires them.

WHAT THIS EMULATOR EXISTS TO EXERCISE

Pillar E's attainment axis, and the three ways it can go wrong:

  DIRECTION      `operating_cost` is LOWER_IS_BETTER. A build that assumed otherwise
                 would place every well-run cost centre in the underperforming
                 quadrant, and a corpus containing only revenue metrics would never
                 catch it. So a cost metric is emitted by default, not as an option.

  A BAD YEAR     `inject_bad_year` makes every unit miss plan by 18 to 42 per cent.
                 Standardised, that produces a scatter identical to a good year —
                 which is the entire reason D92 requires the ratio reported alongside.
                 The scenario exists so that claim can be tested rather than asserted.

  THIN GROUPS    `inject_sole_metric` gives one unit a measure no other unit carries,
                 so it cannot be standardised against anything. The product must
                 exclude and count it, not plot it at zero.

IDENTIFIERS ARE THIS SYSTEM'S OWN, AND THAT IS THE POINT

A financial system's cost centre and an HCM's org unit are **not automatically the same
thing**, and deciding that they are is cross-system identity resolution, which D56 put
out of scope for inference. So by default this emulator invents its own cost centre
codes and says so in `source_unit_id`.

`Parameters.org_unit_codes` lets a test line them up deliberately. Passing them is an
act of configuration, exactly as the adapter profile is in a real deployment — it is
never assumed, because a harness that silently agreed with the HCM would hide the one
integration question that matters most here.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date

from pseudofin.calendar import periods as calendar_periods
from pseudofin.marking import mark

HISTORY_START = date(2024, 1, 1)
HISTORY_END = date(2026, 12, 31)


# The measures, and which way is good. THE DIRECTION IS PART OF THE DEFINITION —
# `actual / plan` means nothing without it, and the schema refuses a metric that does
# not state one.
MEASURES: tuple[tuple[str, str, str, str], ...] = (
    ("net_revenue", "Net revenue", "HIGHER_IS_BETTER", "GBP"),
    ("gross_margin_pct", "Gross margin", "HIGHER_IS_BETTER", "percent"),
    # The one that matters. Under plan is GOOD here and bad in the two above.
    ("operating_cost", "Operating cost", "LOWER_IS_BETTER", "GBP"),
)

PRIORITIES: tuple[tuple[str, str], ...] = (
    ("GROWTH", "Grow revenue in existing markets without adding headcount at the same "
               "rate"),
    ("MARGIN", "Improve gross margin through automation of manual fulfilment steps"),
    ("RESILIENCE", "Reduce single-supplier dependency across the critical component "
                   "set"),
    # Deliberately statement-free — see `Parameters.priorities_without_statement`.
    ("CULTURE", ""),
)


@dataclass
class Parameters:
    """Every parameter documented and adjustable. Nothing hidden."""

    seed: int = 20260902
    units: int = 12
    history_start: date = HISTORY_START
    history_end: date = HISTORY_END

    # Quarterly by default. Financial periods and HR review cycles are set
    # independently, and the product must cope with a measurement period that overlaps
    # no review cycle at all — so the two clocks are deliberately not aligned here.
    months_per_period: int = 3

    # Where the customer's HCM unit codes are known, pass them. Empty means this
    # system's own cost centre codes, which is the honest default. See the module
    # docstring.
    org_unit_codes: tuple[str, ...] = ()

    # How far a unit's actual typically lands from its plan, as a share.
    performance_spread: float = 0.12

    # Share of metric rows whose `comparable_across_units` is left UNSTATED. Null must
    # never read as true — Pillar E's third hypothesis is that the metric is the wrong
    # measure for a unit, and only the customer can settle it. A corpus where every
    # row states a value never exercises the unstated path.
    unstated_comparability: float = 0.15

    # Share of periods where the plan was set AFTER the period began. The plan-setting
    # confound is stated on every Pillar E reading; this is what makes it checkable
    # rather than merely warned about.
    late_plans: float = 0.10

    # A priority with no statement supports only the weakest linkage confidence, and
    # D24 then suppresses rather than scores. Real strategy decks contain at least one
    # of these.
    priorities_without_statement: int = 1


@dataclass
class Corpus:
    business_unit_metrics: list[dict] = field(default_factory=list)
    strategic_priorities: list[dict] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "BusinessUnitMetric": len(self.business_unit_metrics),
            "StrategicPriority": len(self.strategic_priorities),
        }


def periods(params: Parameters) -> list[tuple[date, date]]:
    """Measurement periods for these parameters. D98.

    The arithmetic lives in `calendar.py`, which is shared by copy across the three ERP
    emulators and compared by Gate 12 — the same arrangement `mark()` is under, for the
    same reason.
    """
    return calendar_periods(params.history_start, params.history_end,
                            params.months_per_period)


def unit_codes(params: Parameters) -> list[str]:
    if params.org_unit_codes:
        return list(params.org_unit_codes)
    # This system's own identifiers, and named so nobody mistakes them for the HCM's.
    return [f"CC-{n:03d}" for n in range(1, params.units + 1)]


def generate(params: Parameters | None = None) -> Corpus:
    """The full corpus. Seeded locally — never the module-level RNG.

    `random.Random(seed)` rather than `random.seed(seed)`: the global generator is
    shared with everything else in the process, so a corpus built after any other code
    touched it would not reproduce. Byte-identical output is the harness's central
    claim and a shared RNG quietly voids it.
    """
    params = params or Parameters()
    rng = random.Random(params.seed)
    corpus = Corpus()
    codes = unit_codes(params)

    for start, end in periods(params):
        for code in codes:
            for key, label, direction, measure in MEASURES:
                plan = float(rng.randrange(500, 5_000))
                actual = round(plan * (1 + rng.uniform(-params.performance_spread,
                                                       params.performance_spread)), 2)
                late = rng.random() < params.late_plans
                comparable: bool | None = (
                    None if rng.random() < params.unstated_comparability else True)
                corpus.business_unit_metrics.append(mark({
                    "metric_id": f"BUM-{code}-{start.isoformat()}-{key}",
                    "source_unit_id": code,
                    "metric_key": key,
                    "label": label,
                    "unit_of_measure": measure,
                    "direction": direction,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "actual": actual,
                    "plan": plan,
                    # A late plan is set inside the period it measures.
                    "plan_set_on": (date.fromordinal(start.toordinal() + 20).isoformat()
                                    if late
                                    else date.fromordinal(start.toordinal() - 30)
                                    .isoformat()),
                    "comparable_across_units": comparable,
                    "valid_from": start.isoformat(),
                    "valid_to": None,
                }))

    for index, (code, statement) in enumerate(PRIORITIES):
        blank = index >= len(PRIORITIES) - params.priorities_without_statement
        corpus.strategic_priorities.append(mark({
            "priority_id": f"SP-{code}",
            "priority_code": code,
            "label": code.title(),
            # None, not "". The schema refuses a blank statement precisely because an
            # empty string satisfies a NOT NULL check while carrying nothing, which is
            # how emptiness comes to be scored as content.
            "statement": None if (blank or not statement) else statement,
            "horizon_start": params.history_start.isoformat(),
            "horizon_end": None,
            # Unranked is a real state and must not sort to last. One priority is left
            # unranked so the path exists in every corpus.
            "stated_rank": None if index == 0 else index,
            # D104. Same defect as pseudocrm's offering owner, in the priority set:
            # the profile maps `owning_source_unit_code` from `owning_source_unit_id`,
            # and this emitted `source_unit_id`. A priority owned by a unit would have
            # arrived owned by none.
            "owning_source_unit_id": None,
            "valid_from": params.history_start.isoformat(),
            "valid_to": None,
        }))
    return corpus
