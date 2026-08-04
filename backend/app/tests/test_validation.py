"""Phase 8: grounding validator tests."""

from __future__ import annotations

import pytest
from app.core.exceptions import GroundingValidationFailedError
from app.validation.grounding import GroundingValidator, assert_grounded


def test_valid_citations_pass() -> None:
    res = GroundingValidator().validate(
        "Under section 112 the punishment is rigorous imprisonment.",
        [112, 44, 37],
    )
    assert res.grounded is True
    assert res.stray == []


def test_stray_citation_detected() -> None:
    res = GroundingValidator().validate(
        "Under section 999 the punishment is life.",
        [112],
    )
    assert res.grounded is False
    assert res.stray == [999]


def test_mixed_valid_and_stray() -> None:
    res = GroundingValidator().validate(
        "See sections 112 and 303 for context.",
        [112],
    )
    assert res.grounded is False
    assert res.stray == [303]


def test_assert_grounded_passes() -> None:
    res = assert_grounded("Section 44 governs private defence.", [44])
    assert res.grounded is True


def test_assert_grounded_raises() -> None:
    with pytest.raises(GroundingValidationFailedError):
        assert_grounded("Section 44 governs private defence.", [112])


def test_empty_answer_is_grounded() -> None:
    res = GroundingValidator().validate("", [1, 2])
    assert res.grounded is True


def test_handles_non_section_text() -> None:
    res = GroundingValidator().validate("The punishment is five years.", [5])
    assert res.grounded is True
