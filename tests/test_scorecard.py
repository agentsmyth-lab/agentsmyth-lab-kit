"""The comparison: completeness, denominators, the curve, and the saved example output."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from labkit.__main__ import main
from labkit.records import RecordError, load_events, load_forecasts
from labkit.scorecard import build_scorecard

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "earnings"


def run_cli(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class CompletenessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.events = load_events(EXAMPLE / "events.json")
        self.candidate = load_forecasts(EXAMPLE / "forecasts" / "candidate.json")
        self.baseline = load_forecasts(EXAMPLE / "forecasts" / "baseline.json")

    def test_complete_record_is_graded(self) -> None:
        card = build_scorecard(self.events, self.candidate, self.baseline)
        self.assertTrue(card.complete)
        self.assertEqual(card.exit_code, 0)
        self.assertEqual(len(card.systems), 2)

    def test_dropping_a_wrong_call_is_refused_not_rewarded(self) -> None:
        # Known positive: without the completeness check, deleting E-03 (a wrong call) would raise
        # the candidate's accuracy from 3 of 5 to 3 of 4. The comparison must refuse instead.
        full = build_scorecard(self.events, self.candidate, self.baseline)
        self.assertEqual((full.systems[0].counts["correct"], full.systems[0].directional), (3, 5))
        dropped = load_forecasts(EXAMPLE / "controls" / "candidate-dropped-case.json")
        card = build_scorecard(self.events, dropped, self.baseline)
        self.assertFalse(card.complete)
        self.assertEqual(card.exit_code, 1)
        self.assertEqual(card.systems, ())
        self.assertEqual(card.completeness[0].absent, ("E-03",))

    def test_dropped_case_cli_exits_nonzero_and_reports_no_accuracy(self) -> None:
        code, out, err = run_cli("run", str(EXAMPLE), "--candidate", str(EXAMPLE / "controls" / "candidate-dropped-case.json"))
        self.assertEqual(code, 1)
        self.assertIn("`E-03`", out)
        self.assertNotIn("Directional accuracy", out)
        self.assertIn("incomplete record", err)

    def test_malformed_input_exits_2_with_the_field_named(self) -> None:
        code, _, err = run_cli("run", str(EXAMPLE), "--baseline", str(EXAMPLE / "events.json"))
        self.assertEqual(code, 2)
        self.assertIn("'forecasts'", err)


class MeasurementTest(unittest.TestCase):
    def setUp(self) -> None:
        card = build_scorecard(
            load_events(EXAMPLE / "events.json"),
            load_forecasts(EXAMPLE / "forecasts" / "candidate.json"),
            load_forecasts(EXAMPLE / "forecasts" / "baseline.json"),
        )
        self.card = card

    def test_every_event_lands_in_exactly_one_verdict(self) -> None:
        for system in self.card.systems:
            self.assertEqual(sum(system.counts.values()), len(self.card.events))

    def test_curve_at_the_season_half_width_matches_the_season_rule(self) -> None:
        for system in self.card.systems:
            point = next(p for p in system.curve if p["half_width"] == 5)
            self.assertEqual(point["called"], system.directional)
            self.assertEqual(point["correct"], system.counts["correct"])
            self.assertEqual(point["ties"], system.counts["tie"])

    def test_paired_panel_counts_only_events_both_systems_can_be_graded_on(self) -> None:
        assert self.card.paired is not None
        self.assertEqual(self.card.paired.events, sum(r["events"] for r in self.card.paired.rows.values()))
        self.assertEqual(self.card.paired.events, 8)


class RecordValidationTest(unittest.TestCase):
    def write(self, payload: dict[str, object]) -> Path:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(payload, handle)
        handle.close()
        return Path(handle.name)

    def test_return_must_agree_with_prices(self) -> None:
        events = json.loads((EXAMPLE / "events.json").read_text())
        events["events"][0]["outcome"]["return_pct"] = 99.0
        with self.assertRaisesRegex(RecordError, "disagrees with the prices"):
            load_events(self.write(events))

    def test_timestamps_need_an_offset(self) -> None:
        events = json.loads((EXAMPLE / "events.json").read_text())
        events["events"][0]["reference_time"] = "2026-10-14T16:00:00"
        with self.assertRaisesRegex(RecordError, "no UTC offset"):
            load_events(self.write(events))

    def test_scores_are_integers_from_0_to_100(self) -> None:
        for bad in (101, -1, 55.5, "60", True):
            payload = {"system": "X", "forecasts": [{"event_id": "E-01", "status": "scored", "score": bad, "saved_at": "2026-10-14T10:00:00-04:00"}]}
            with self.assertRaises(RecordError):
                load_forecasts(self.write(payload))

    def test_a_missing_forecast_cannot_carry_a_score(self) -> None:
        payload = {"system": "X", "forecasts": [{"event_id": "E-01", "status": "missing", "score": 50}]}
        with self.assertRaisesRegex(RecordError, "must not carry a score"):
            load_forecasts(self.write(payload))


class SavedOutputTest(unittest.TestCase):
    def test_example_output_matches_the_saved_reports_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _, _ = run_cli("run", str(EXAMPLE), "--out", tmp)
            self.assertEqual(code, 0)
            for name in ("scorecard.md", "scorecard.json"):
                self.assertEqual(
                    (Path(tmp) / name).read_text(encoding="utf-8"),
                    (EXAMPLE / "expected" / name).read_text(encoding="utf-8"),
                    f"{name} differs from examples/earnings/expected/{name}",
                )


if __name__ == "__main__":
    unittest.main()
