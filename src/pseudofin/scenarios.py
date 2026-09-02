"""Scenario injectors — pseudofin.

Injected, never generated. Same rule as `pseudohcm`'s de-growth: a base corpus that
already contained the scenario would change the shape of every fixture written against
it, and a test could no longer say *this behaviour appears when the scenario is applied
and not otherwise*.

Each injector returns a summary the caller can assert on. A scenario that reported
nothing would be indistinguishable from one that did nothing.
"""
from __future__ import annotations

from datetime import date

from contract.markers import RESERVED_ID_NAMESPACE

from pseudofin.generator import Corpus
from pseudofin.marking import mark


def _namespaced(code: str) -> str:
    """A caller names a unit by its plain code; the corpus holds the stamped one.

    `source_unit_id` ends in `_id`, so the shared marking machinery moves it into the
    reserved namespace along with every other identifier — which is right, and is why
    the field is named `_id` rather than `_code`. A cost centre code identifies a unit
    whatever it is called, and a field escaping the namespace because of its NAME would
    be a hole in the poison pill that nothing in either repository would notice.

    The cost lands here: an injector taking `unit_code="CC-001"` has to normalise, and
    doing it in one function means no caller has to know the convention.
    """
    return code if code.startswith(RESERVED_ID_NAMESPACE) else (
        RESERVED_ID_NAMESPACE + code)


def inject_bad_year(corpus: Corpus, *, year: int,
                    worst: float = 0.42, best: float = 0.18) -> dict:
    """Every unit misses plan, by between `best` and `worst` — **the D92 scenario.**

    THIS IS THE CASE THE PRODUCT MUST NOT GET WRONG.

    Standardise these figures and the scatter is indistinguishable from a year of
    +12%, +3%, -3%, -12%: the spread is similar, the centre is wherever the mean is,
    and every unit sits in an ordinary-looking position. **Every unit missed plan, one
    of them by 42 per cent, and the chart reads healthy.**

    That is why D92 requires the quadrant to use the standardised value and the label
    to state the plain percentage. The discrepancy between the two is itself the
    finding — everyone missed, nobody is unusual — and neither number alone can say it.

    Applied deterministically rather than randomly: the shortfall is spread evenly
    across the units in the order they appear, so the same corpus produces the same bad
    year every run and a test can assert an exact figure.

    HIGHER_IS_BETTER measures are pushed DOWN and LOWER_IS_BETTER measures are pushed
    UP, because both mean *missed the plan*. An injector that moved every actual in one
    direction would have handed the cost centres a triumphant year in the middle of a
    disaster, which is the same confusion the `direction` column exists to prevent.
    """
    affected = [m for m in corpus.business_unit_metrics
                if _year_of(m["period_start"]) == year]
    if not affected:
        return {"metrics_adjusted": 0, "units_affected": 0, "year": year}

    units = sorted({m["source_unit_id"] for m in affected})
    # Evenly spaced between best and worst, so the set is reproducible and spans the
    # stated range with both endpoints present.
    span = (worst - best) / (len(units) - 1) if len(units) > 1 else 0.0
    shortfall = {code: best + span * index for index, code in enumerate(units)}

    for metric in affected:
        miss = shortfall[metric["source_unit_id"]]
        plan = metric["plan"]
        if metric["direction"] == "LOWER_IS_BETTER":
            metric["actual"] = round(plan * (1 + miss), 2)
        else:
            metric["actual"] = round(plan * (1 - miss), 2)
    return {
        "metrics_adjusted": len(affected),
        "units_affected": len(units),
        "year": year,
        "worst_shortfall": max(shortfall.values()),
        "best_shortfall": min(shortfall.values()),
    }


def inject_sole_metric(corpus: Corpus, *, unit_code: str,
                       metric_key: str = "regulatory_levy") -> dict:
    """One unit carries a measure no other unit carries.

    It cannot be standardised against anything — there is no group to compare it with —
    so the product must exclude it and say so. A z-score computed over a group of one
    is not a smaller finding, it is an invented one, and the failure mode if the
    exclusion goes unreported is a unit that quietly stops appearing on the chart.
    """
    stamped = _namespaced(unit_code)
    periods_held = sorted({(m["period_start"], m["period_end"])
                           for m in corpus.business_unit_metrics
                           if m["source_unit_id"] == stamped})
    if not periods_held:
        return {"rows_added": 0, "unit_code": unit_code}

    added = 0
    for start, end in periods_held:
        corpus.business_unit_metrics.append(mark({
            # The BARE code in the identifier. `mark` stamps the whole thing once;
            # building it from the already-stamped value would produce
            # `PSEUDO::BUM-PSEUDO::CC-001-...`, which no lookup resolves.
            "metric_id": f"BUM-{unit_code}-{start}-{metric_key}",
            "source_unit_id": stamped,
            "metric_key": metric_key,
            "label": "Regulatory levy",
            "unit_of_measure": "GBP",
            "direction": "LOWER_IS_BETTER",
            "period_start": start,
            "period_end": end,
            "actual": 120.0,
            "plan": 100.0,
            "plan_set_on": start,
            "comparable_across_units": False,
            "valid_from": start,
            "valid_to": None,
        }))
        added += 1
    return {"rows_added": added, "unit_code": unit_code, "metric_key": metric_key}


def _year_of(iso: str) -> int:
    return date.fromisoformat(iso).year
