"""The scaffold holds — pseudofin.

A repository with no tests has a green CI that proves nothing. That is the shape this
project has met five times, so the first test exists before the first generator.
"""
from __future__ import annotations

import pseudofin
from pseudofin.marking import SHARED_MACHINERY_VERSION, mark


def test_the_package_imports():
    assert pseudofin.__doc__


def test_the_marker_is_applied():
    """Gate 7's half of the poison pill. If this fails the harness can load into a
    customer database and the product's own tests would still pass, because they test
    the refusal rather than the stamping."""
    from contract.markers import SYNTHETIC_MARKER_FIELD, SYNTHETIC_MARKER_VALUE

    marked = mark({"thing_id": "x-1", "label": "a"})
    assert marked[SYNTHETIC_MARKER_FIELD] == SYNTHETIC_MARKER_VALUE


def test_identifiers_are_moved_into_the_reserved_namespace():
    assert mark({"thing_id": "x-1"})["thing_id"].startswith("PSEUDO::")


def test_an_already_marked_identifier_is_not_double_prefixed():
    once = mark({"thing_id": "x-1"})
    assert mark(once)["thing_id"] == once["thing_id"]


def test_the_original_record_is_not_mutated():
    """`mark` copies. A generator that saw its own input change would produce a corpus
    that differs from the one it described."""
    original = {"thing_id": "x-1"}
    mark(original)
    assert original == {"thing_id": "x-1"}


def test_the_shared_machinery_declares_its_version():
    """Read by the cross-repo drift check. Four copies of this file exist by decision
    (D91), and a check rather than coupling is what keeps them honest."""
    assert SHARED_MACHINERY_VERSION == "1"
