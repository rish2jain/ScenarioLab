"""Tests for shared simulation input bound validation."""

import pytest

from app.simulation.validation import validate_int_bounds


def test_validate_int_bounds_accepts_inclusive_range():
    assert validate_int_bounds(1, minimum=1, maximum=10, field_name="x") == 1
    assert validate_int_bounds(10, minimum=1, maximum=10, field_name="x") == 10


def test_validate_int_bounds_rejects_below_minimum():
    with pytest.raises(ValueError, match="total_rounds must be >= 1"):
        validate_int_bounds(0, minimum=1, maximum=20, field_name="total_rounds")


def test_validate_int_bounds_rejects_above_maximum():
    with pytest.raises(ValueError, match="iterations must be <= 10"):
        validate_int_bounds(11, minimum=1, maximum=10, field_name="iterations")
