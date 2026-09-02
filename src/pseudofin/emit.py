"""File emission — pseudofin.

Contract-shaped JSONL, one file per canonical entity, the same shape `pseudohcm` emits.

**Written even when empty**, deliberately: an absent file and an empty one say
different things to whoever is loading them. Absent reads as *this harness does not
know about strategic priorities*; empty reads as *it does, and this run produced none*.
Only the second is ever true here.
"""
from __future__ import annotations

import json
from pathlib import Path

from pseudofin.generator import Corpus

ENTITY_FILES = {
    "BusinessUnitMetric": "business_unit_metrics",
    "StrategicPriority": "strategic_priorities",
}


def emit(corpus: Corpus, out: Path) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}
    for entity, attribute in ENTITY_FILES.items():
        records = getattr(corpus, attribute)
        (out / f"{entity}.jsonl").write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )
        written[entity] = len(records)
    return written
