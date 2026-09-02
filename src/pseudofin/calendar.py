"""Measurement periods — the second piece of shared harness machinery. D98.

SHARED BY COPY, NOT BY IMPORT — the same decision as `marking.py` under D91, and the
same condition attached: a check notices when the copies diverge.

Three ERP emulators all divide a history into measurement periods, and the arithmetic
is mechanical, judgement-free and exactly the kind of thing that rots quietly. When it
was written once it lived inside `pseudofin.generator`; the moment the second emulator
needed it, it became duplicated code with nothing comparing the copies — which is
precisely the state D91 refused to leave `mark()` in.

So it sits here, in its own module, and `gate12_harness_drift.py` compares the copies
by behaviour. `pseudohcm` does not carry this file: its clock is review cycles rather
than financial periods, and giving it one for symmetry would be inventing a concept the
HCM domain does not have. The gate compares the harnesses that carry it and reports how
many did.

BOTH ENDPOINTS ARE INCLUSIVE.

`period_end` is the last day the period covers — the same convention the schema states
for this column, the same one `exit_date` follows, and the opposite of `valid_to`. D67
was caused by conflating those two kinds of date in the other direction, and the fix
was to say which kind each one is rather than to make them all one kind.
"""
from __future__ import annotations

from datetime import date

# Read by the cross-repo drift check. Do not edit without editing every copy.
SHARED_CALENDAR_VERSION = "1"


def periods(start: date, end: date, months: int = 3) -> list[tuple[date, date]]:
    """Consecutive periods of `months`, abutting exactly, none extending past `end`.

    A partial final period is DROPPED rather than truncated. A quarter measured over
    two months is not a smaller quarter — it is a different denominator — and a plan
    set for three months compared against two months of actuals reports a shortfall
    that did not happen.
    """
    if months < 1:
        raise ValueError("a measurement period must span at least one month")
    out: list[tuple[date, date]] = []
    year, month = start.year, start.month
    while True:
        period_start = date(year, month, 1)
        if period_start > end:
            break
        last = month + months - 1
        last_year = year + (last - 1) // 12
        last_month = (last - 1) % 12 + 1
        following = (date(last_year + 1, 1, 1) if last_month == 12
                     else date(last_year, last_month + 1, 1))
        period_end = date.fromordinal(following.toordinal() - 1)
        if period_end > end:
            break
        out.append((period_start, period_end))
        year, month = following.year, following.month
    return out
