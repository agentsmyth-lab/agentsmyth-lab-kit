"""The published season dataset reproduces the interim scorecard's figures."""

import copy
import json
import itertools
import unittest
from pathlib import Path

from labkit import season

DATASET = Path(__file__).resolve().parent.parent / "data" / "earnings-interim-2026-11-13"


class SeasonFiguresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events, cls.universe = season.load(DATASET)
        cls.figures = season.figures(cls.events, cls.universe)

    def test_matches_published_figures(self):
        published = json.loads((DATASET / "figures.json").read_text(encoding="utf-8"))
        for key in sorted(set(published) | set(self.figures)):
            with self.subTest(figure=key):
                self.assertEqual(published.get(key), self.figures.get(key))

    def test_headline(self):
        f = self.figures
        self.assertEqual((f["eligible"], f["settled"], f["rose"], f["fell"]), (607, 606, 311, 295))
        self.assertEqual((f["agent"]["right"], f["agent"]["called"], f["agent"]["missing"]), (118, 214, 40))
        self.assertEqual((f["baseline"]["right"], f["baseline"]["called"], f["baseline"]["missing"]), (250, 487, 30))
        self.assertEqual((f["agent"]["neutral"], f["baseline"]["neutral"]), (353, 90))

    def test_curve_keeps_missing_and_unsettled_events_in_coverage(self):
        for system in ("agent", "baseline"):
            curve = self.figures["curve"][system]
            self.assertEqual(curve["total"], 607)
            self.assertLess(curve["scored_settled"], curve["total"])
            point = next(p for p in curve["points"] if p[0] == 5)
            self.assertEqual(point[1], self.figures[system]["called"])
            self.assertEqual(point[3], self.figures[system]["called_share"])

    def test_universe_and_missing_reasons(self):
        u = self.figures["universe"]
        self.assertEqual((u["eligible"], u["below_10b_on_release_day_included"], u["below_10b_on_release_day_left_out"]),
                         (604, 3, 17))
        self.assertEqual(u["not_sec_registrant"] + u["no_periodic_reports"], 369)
        self.assertEqual(self.figures["agent_missing_reasons"]["outage_2026_10_21"], 11)
        self.assertEqual(sum(self.figures["agent_missing_reasons"].values()), 40)

    def test_reasoning_groups(self):
        r = self.figures["reasoning"]["season"]
        self.assertEqual(r["bullish_positive_guidance"], [31, 48])
        self.assertEqual(r["bullish_without_support"], [13, 31])
        self.assertEqual(r["bearish_adverse"], [46, 76])
        self.assertEqual(r["bearish_in_line"], [10, 22])
        self.assertEqual((r["bearish_no_central"], r["bearish_tied"]), ([16, 34], [2, 3]))
        bull = [v for k, v in r.items() if k.startswith("bullish")]
        bear = [v for k, v in r.items() if k.startswith("bearish")]
        self.assertEqual((sum(x[0] for x in bull), sum(x[1] for x in bull)), tuple(self.figures["agent"]["bullish"]))
        self.assertEqual((sum(x[0] for x in bear), sum(x[1] for x in bear)), tuple(self.figures["agent"]["bearish"]))

    def test_records_carry_only_the_public_score_fields(self):
        for r in self.events:
            self.assertEqual(set(r), {"event", "ticker", "company", "cik", "sp500", "sector", "release_date",
                                      "release_time", "release_time_basis", "below_10b_on_release_day", "outcome",
                                      "agent", "baseline"})
            self.assertEqual(set(r["outcome"]), {"status", "start_date", "end_date", "return_pct",
                                                "market_return_pct", "sector_return_pct"})
            a, b = r["agent"], r["baseline"]
            self.assertEqual(set(a), {"status", "saved_at", "assessment_score", "evidence_adjusted_score", "reasoning_group"}
                             if a["status"] == "scored" else {"status", "missing_reason"})
            self.assertEqual(set(b), {"status", "saved_at", "assessment_score"}
                             if b["status"] == "scored" else {"status"})

    def test_a_missing_or_malformed_score_is_not_a_neutral_call(self):
        r = copy.deepcopy(next(r for r in self.events if r["agent"]["status"] == "scored"))
        for value in (True, 55.0, -1, 101, None):
            r["agent"]["evidence_adjusted_score"] = value
            with self.assertRaises(ValueError):
                season.derive([r])
        del r["agent"]["evidence_adjusted_score"]
        with self.assertRaises(KeyError):
            season.derive([r])

    def test_every_forecast_was_saved_before_the_release(self):
        derived = season.derive(self.events)
        self.assertFalse([e["event"] for e in derived if "late" in (e["agent_status"], e["baseline_status"])])

    def test_a_late_save_stops_counting(self):
        events = copy.deepcopy(self.events)
        target = next(r for r in events if r["agent"]["status"] == "scored")
        target["agent"]["saved_at"] = target["release_time"]
        self.assertEqual(season.derive([target])[0]["agent_status"], "late")
        self.assertEqual(season.figures(events, self.universe)["agent"]["missing"], 41)


class AveragePrecisionTest(unittest.TestCase):
    def test_ties_enter_at_one_threshold_in_any_order(self):
        # One rise at the first threshold, then one rise and one fall tied:
        # AP = (1/2)*1 + (1/2)*(2/3) = 5/6.
        for rows in itertools.permutations([(70, 1), (50, 1), (50, -1)]):
            ap, prevalence = season._ap(rows, True)
            self.assertAlmostEqual(ap, 5 / 6)
            self.assertAlmostEqual(prevalence, 2 / 3)

    def test_all_equal_scores_have_only_the_base_rate(self):
        for positive in (True, False):
            self.assertEqual(season._ap([(50, 1), (50, -1)], positive), (0.5, 0.5))

    def test_downward_ranking_and_zero_return_ties(self):
        self.assertEqual(season._ap([(30, -1), (70, 1), (10, 0)], False), (1.0, 0.5))

    def test_undefined_target_class_is_not_reported_as_zero(self):
        for rows in ([], [(50, 0)], [(50, -1)]):
            with self.assertRaises(ValueError):
                season._ap(rows, True)


if __name__ == "__main__":
    unittest.main()
