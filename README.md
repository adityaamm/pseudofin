# pseudofin — Financials emulator

**A test harness. It never ships, and it is built so that it cannot.**

Attainment against plan, and the customer's own strategic priorities.
Unblocks Pillar E's performance landscape (D62) and D77's highest-weighted
role-relevance component.

## What this is, and what it is emphatically not

This emulator mimics **the shape of the Financials domain** — the entities, the
relationships, the way plan and actual behave over time, and the edge cases that make
an analytical layer either honest or quietly wrong.

**It does not mimic any vendor's schema, and it is not derived from one.** Field
mappings for a real product are authored from that vendor's own published API
documentation, under that vendor's terms, at the point a customer engagement requires
it. Nothing proprietary is embedded here.

That distinction is also what makes the emulator useful. A harness copying one vendor's
field names tests the adapter against one vendor. A harness capturing what the domain
*is* tests it against all of them.

## Gate 7 — the poison pill

Every record this harness emits carries a synthetic marker, and the product's ingestion
refuses anything carrying it. The marker is defined once, in
`aiecona-adapter-contract`, and read from there by both sides: this harness stamps it,
the product rejects it.

**That is the half of the control living in this repository.** If the stamping ever
stopped, this harness would become capable of loading into a customer database — and
the product's own tests would still pass, because they test the refusal rather than
the stamping.

## Determinism

Same seed, same parameters, byte-identical output. Not "here is data" but "here is a
documented process with stated parameters that produces data" — the output is not a
claim about the world.

Nothing here reads the wall clock. `pseudohcm` learned that the hard way: its
provenance timestamp came from `datetime.now()` for months, making its own documented
determinism claim false, and the test that should have caught it compared two fields
rather than whole records (D80).

## Canonical targets

Writes only to the `enterprise_context` partition:

- `BusinessUnitMetric`
- `StrategicPriority`

## Shared machinery, deliberately copied

`marking.py` and `emit.py` are near-identical across the four harnesses. That
duplication is a decision (D91), not an oversight: each emulator stays independently
deliverable, since a customer running one ERP and a different HCM should take only what
they need.

The drift risk that duplication creates is handled by a check rather than by coupling —
the same move as the single-temporal-gateway gate. The safety-critical part, the marker
itself, was never duplicated.

## Status

**Scaffold.** The generator is not yet written. This repository exists so the shape,
the guard rails and the CI are in place before any data is produced.
