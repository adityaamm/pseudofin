"""The workflow's assertions and the corpus cannot drift apart — D108.

WHY THIS EXISTS

The CI workflow asserts properties of the generated corpus by reading fields from it
directly. D104 renamed one of those fields in the generator and in this suite, and
**left the workflow reading the old name** — so the push failed on a step that had
nothing to do with the change, with a KeyError three files from the edit.

That is the same defect D104 itself fixed: a name changed in one place and not another,
with nothing comparing the two. Introduced, in the same commit, by the person writing
about it.

WHY THE WORKFLOW READS THE CORPUS AT ALL

It could call this suite and stop there, and then it would prove less. These tests run
against `src/`; the workflow runs against the INSTALLED package from outside the
checkout, which is what catches a packaging fault. The duplication is deliberate and
the drift is what needed handling.

WHAT IS AND IS NOT CHECKED

Every quoted key the workflow reads from a corpus row must exist on a row of that kind.
Keys belonging to scenario results and other dictionaries are listed in
`NOT_CORPUS_FIELDS` rather than guessed at — a list of reasons somebody has to add to
deliberately, which is the same shape Gate 13's declarations take.
"""
from __future__ import annotations

import re
from pathlib import Path

import pseudofin.generator as generator
from pseudofin.emit import ENTITY_FILES

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

# Keys the workflow reads from something that is NOT a corpus row — scenario summaries,
# and anything else with its own shape. Named individually so that "not a corpus field"
# cannot quietly mean "nobody checked".
NOT_CORPUS_FIELDS: dict[str, str] = {
    "metrics_adjusted": "returned by a scenario injector, not carried on a row",
    "units_affected": "scenario summary",
    "worst_shortfall": "scenario summary",
    "best_shortfall": "scenario summary",
    "rows_added": "scenario summary",
    "offerings_retired": "scenario summary",
    "identifiers": "scenario summary",
    "people_exited": "scenario summary",
    "positions_removed": "scenario summary",
    "people_displaced": "scenario summary",
    "joiners_removed": "scenario summary",
}


def corpus_fields() -> set[str]:
    """Every field name appearing on any row of any entity this harness emits."""
    corpus = generator.generate(generator.Parameters(units=4))
    found: set[str] = set()
    for attribute in ENTITY_FILES.values():
        for row in getattr(corpus, attribute):
            found |= set(row)
    return found


def workflow_keys() -> set[str]:
    """Quoted subscripts in the workflow — `o['owning_source_unit_id']` and friends."""
    text = WORKFLOW.read_text(encoding="utf-8")
    return set(re.findall(r"\[\s*'([a-z][a-z0-9_]*)'\s*\]", text))


def test_the_workflow_reads_no_field_the_corpus_does_not_have():
    """**The check that would have saved a failed push.**

    A renamed field leaves the workflow asserting on a key that no longer exists, and
    the failure surfaces in CI as a KeyError in a step unrelated to the change.
    """
    unknown = sorted(workflow_keys() - corpus_fields() - set(NOT_CORPUS_FIELDS))
    assert not unknown, (
        f"the CI workflow reads {unknown} and no emitted row carries those fields. "
        "Either the generator renamed something and the workflow was left behind, or "
        "the key belongs to a scenario result and should be listed in "
        "NOT_CORPUS_FIELDS with a reason."
    )


def test_the_exclusion_list_does_not_outlive_its_reason():
    """A stale exclusion is how the first check quietly stops covering a field.

    Same argument as Gate 13's stale-declaration rule: an entry declared as an
    exception that is now an ordinary corpus field should fail rather than sit there
    reading as policy.
    """
    stale = sorted(set(NOT_CORPUS_FIELDS) & corpus_fields())
    assert not stale, (
        f"{stale} are listed as not corpus fields and now appear on a row. Remove the "
        "exclusion — it currently hides them from the check above."
    )


def test_the_scan_finds_something():
    """Vacuity guard. A regex that matched nothing would pass forever, and this file
    would be a comment about a check rather than a check."""
    assert WORKFLOW.exists(), "the workflow moved; this guard is reading nothing"
    assert workflow_keys(), "no quoted subscripts found in the workflow at all"
    assert corpus_fields(), "the generator produced no fields to compare against"
