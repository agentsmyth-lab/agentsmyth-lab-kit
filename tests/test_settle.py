"""Settlement rules from section 2 of the rubric, one control per rule."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from labkit.records import Event, Forecast, Outcome
from labkit.settle import classify, settle

ET = timezone(timedelta(hours=-4))
REFERENCE = datetime(2026, 10, 20, 16, 0, tzinfo=ET)


def event(return_pct: float | None = 2.0, status: str = "settled") -> Event:
    return Event(
        event_id="T-1",
        company="Test Co",
        ticker="SYN-T",
        release_date="2026-10-20",
        release_phase="after_close",
        reference_time=REFERENCE,
        outcome=Outcome(status, return_pct, None, None, None, None, "test", ""),  # type: ignore[arg-type]
        synthetic=True,
    )


def forecast(score: int | None = 60, *, minutes_before: int = 60, status: str = "scored") -> Forecast:
    saved = REFERENCE - timedelta(minutes=minutes_before) if status == "scored" else None
    return Forecast("T-1", status, score if status == "scored" else None, saved, "")  # type: ignore[arg-type]


class ClassifyTest(unittest.TestCase):
    def test_boundaries_follow_the_season_rule(self) -> None:
        self.assertEqual(classify(55), "bullish")
        self.assertEqual(classify(54), "neutral")
        self.assertEqual(classify(50), "neutral")
        self.assertEqual(classify(46), "neutral")
        self.assertEqual(classify(45), "bearish")
        self.assertEqual(classify(0), "bearish")
        self.assertEqual(classify(100), "bullish")


class SettleTest(unittest.TestCase):
    def test_direction_matches_return(self) -> None:
        self.assertEqual(settle(event(2.0), forecast(60), "A").verdict, "correct")
        self.assertEqual(settle(event(-2.0), forecast(40), "A").verdict, "correct")
        self.assertEqual(settle(event(-2.0), forecast(60), "A").verdict, "wrong")
        self.assertEqual(settle(event(2.0), forecast(40), "A").verdict, "wrong")

    def test_exact_zero_is_a_tie_not_a_hit_or_miss(self) -> None:
        self.assertEqual(settle(event(0.0), forecast(60), "A").verdict, "tie")
        self.assertEqual(settle(event(0.0), forecast(40), "A").verdict, "tie")

    def test_neutral_abstains_even_on_a_small_move(self) -> None:
        self.assertEqual(settle(event(0.1), forecast(50), "A").verdict, "neutral")
        self.assertEqual(settle(event(0.0), forecast(50), "A").verdict, "neutral")

    def test_missing_forecast_is_not_neutral(self) -> None:
        result = settle(event(2.0), forecast(status="missing"), "A")
        self.assertEqual(result.verdict, "missing")
        self.assertIsNone(result.call)

    def test_forecast_at_or_after_the_reference_time_is_late(self) -> None:
        self.assertEqual(settle(event(2.0), forecast(60, minutes_before=0), "A").verdict, "late")
        self.assertEqual(settle(event(2.0), forecast(60, minutes_before=-30), "A").verdict, "late")
        self.assertEqual(settle(event(2.0), forecast(60, minutes_before=1), "A").verdict, "correct")

    def test_unsettled_outcomes_are_never_graded(self) -> None:
        self.assertEqual(settle(event(None, "pending"), forecast(60), "A").verdict, "pending")
        self.assertEqual(settle(event(None, "unresolved"), forecast(60), "A").verdict, "unresolved")


if __name__ == "__main__":
    unittest.main()
