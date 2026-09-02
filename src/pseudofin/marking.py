"""Marking every emitted record. Gate 7 — the poison pill.

Gates 1 to 6 prevent this harness reaching production. This assumes they all failed,
and ensures the product refuses the data anyway.

SHARED BY COPY, NOT BY IMPORT — D91
-----------------------------------
This file is near-identical in all four harnesses, and that is a decision rather than
an oversight. Each emulator stays independently deliverable: a customer running one ERP
and a different HCM should be able to take only the one they need, without a shared
library dragging the other three along.

The duplication risk is real — four copies of a cleanup list drifted apart in D82 — and
it is handled by a check rather than by coupling. `ops/gates/gate12_harness_drift.py`
in `aiecona-hr` fails if these copies stop behaving identically.

**The safety-critical part was never duplicated.** The marker values live once, in
`aiecona-adapter-contract`, and both sides read them from there: this stamps them, the
product's ingestion validation refuses them. One definition, two consumers, opposite
intentions.
"""
from contract.markers import (
    RESERVED_ID_NAMESPACE,
    SYNTHETIC_MARKER_FIELD,
    SYNTHETIC_MARKER_VALUE,
)

# Read by the drift check. Do not edit without editing every copy.
SHARED_MACHINERY_VERSION = "1"


def mark(record: dict) -> dict:
    """Stamp a record so production ingestion will reject it."""
    marked = dict(record)
    marked[SYNTHETIC_MARKER_FIELD] = SYNTHETIC_MARKER_VALUE
    for key, value in list(marked.items()):
        if (key.endswith("_id") or key == "id") and isinstance(value, str):
            if not value.startswith(RESERVED_ID_NAMESPACE):
                marked[key] = RESERVED_ID_NAMESPACE + value
    return marked
