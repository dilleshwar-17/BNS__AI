"""Phase 7: graph section-reference extractor tests."""

from __future__ import annotations

from app.retrieval.graph_extractor import extract_section_references


def test_explicit_single() -> None:
    refs = extract_section_references("subject to the restrictions contained in section 37")
    assert refs["explicit"] == {37}
    assert refs["subsection"] == set()


def test_explicit_list() -> None:
    refs = extract_section_references("the exceptions in sections 25, 26 and 27 do not extend")
    assert refs["explicit"] == {25, 26, 27}


def test_explicit_mixed_list() -> None:
    refs = extract_section_references("sub-sections (2), (3), (4) and (5) of section 8, sections 9, 49, 50")
    assert refs["explicit"] == {8, 9, 49, 50}


def test_subsection_of_section() -> None:
    refs = extract_section_references("in sub-section (1) of section 189 the word offence means")
    assert 189 in refs["explicit"] or 189 in refs["subsection"]


def test_excludes_out_of_range_external_act() -> None:
    refs = extract_section_references("in accordance with section 474 of the Bharatiya Nagarik Suraksha Sanhita")
    assert refs["explicit"] == set()


def test_no_references() -> None:
    refs = extract_section_references("The right of private defence of the body extends")
    assert refs["explicit"] == set()
    assert refs["subsection"] == set()


def test_self_reference_kept_in_explicit() -> None:
    refs = extract_section_references("as per section 12 of this Sanhita")
    assert 12 in refs["explicit"]
