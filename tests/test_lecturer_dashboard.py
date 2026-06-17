"""Tests for lecturer dashboard services."""

from __future__ import annotations

import pytest

from fastapi_app.services.grade_service import compute_grade


@pytest.mark.parametrize(
    "score,letter,point,remark",
    [
        (75, "A", 5.0, "Distinction"),
        (65, "B", 4.0, "Credit"),
        (55, "C", 3.0, "Merit"),
        (47, "D", 2.0, "Pass"),
        (42, "E", 1.0, "Pass"),
        (30, "F", 0.0, "Fail"),
    ],
)
def test_compute_grade_mapping(score, letter, point, remark):
    got_letter, got_point, got_remark = compute_grade(score)
    assert got_letter == letter
    assert got_point == point
    assert got_remark == remark


def test_compute_grade_clamps():
    letter, point, _ = compute_grade(150)
    assert letter == "A"
    assert point == 5.0
    letter, point, _ = compute_grade(-5)
    assert letter == "F"
    assert point == 0.0
