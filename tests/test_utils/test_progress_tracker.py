"""Regressions for ProgressTracker (previously untested).

Increment mode used to stop one step short of 100 %: with three steps the
percentage was 33 → 66 → 66 → 66 forever.
"""
import pytest

from docutranslate.progress import NullProgressTracker, ProgressTracker


def test_increment_mode_reaches_100_percent():
    tracker = ProgressTracker().set_steps(["parse", "translate", "export"])

    percentages = []
    for _ in range(3):
        tracker.update(message="step")
        percentages.append(tracker.percent)

    assert percentages == [33, 66, 100]


def test_increment_mode_beyond_step_count_stays_at_100():
    tracker = ProgressTracker().set_steps(["a", "b"])

    for _ in range(5):
        tracker.update()

    assert tracker.percent == 100


def test_explicit_step_and_weighted_steps():
    tracker = ProgressTracker().set_steps(["a", "b", "c"])
    assert tracker.update(step=2).percent == 100

    weighted = ProgressTracker().set_steps([
        {"name": "parse", "weight": 3},
        {"name": "translate", "weight": 1},
    ])
    assert weighted.update(step=1).percent == 100


def test_explicit_percent_is_clamped_and_callback_runs():
    seen = []
    tracker = ProgressTracker(callback=lambda percent, message: seen.append((percent, message)))

    tracker.update(percent=250, message="over")
    tracker.update(percent=-10, message="under")

    assert tracker.percent == 0
    assert seen == [(100, "over"), (0, "under")]


def test_status_and_reset():
    tracker = ProgressTracker().set_steps(["a", "b"])
    tracker.update(percent=50, message="half")

    status = tracker.get_status()
    assert status["percent"] == 50
    assert status["total_steps"] == 2
    assert status["message"] == "half"

    tracker.reset()
    assert tracker.percent == 0
    assert tracker.current_step == 0


def test_null_tracker_is_a_noop():
    tracker = NullProgressTracker()
    tracker.set_steps(["a"])
    tracker.update(percent=90, message="ignored")
    assert tracker.percent == 0
