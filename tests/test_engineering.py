"""Known-good, known-bad and missing-evidence checks for the synthetic examples."""

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from labkit.__main__ import main
from labkit.engineering import evaluate, load_results, verdict


EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "engineering-1"


class EngineeringChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c["id"]: c for c in json.loads((EXAMPLES / "cases.json").read_text())}
        cls.profile = json.loads((EXAMPLES / "profile.json").read_text())

    def test_all_expected_verdicts_and_checks(self):
        results = load_results(EXAMPLES)
        self.assertEqual(results, json.loads((EXAMPLES / "expected.json").read_text()))
        self.assertEqual({r["verdict"] for r in results.values()}, {"pass", "fail", "unproven"})

    def test_profile_changes_a_house_pass_into_a_customer_failure(self):
        c = copy.deepcopy(self.cases["broker_restricts_product"])
        self.assertEqual(evaluate(c, self.profile)["verdict"], "fail")
        del c["profile"]
        self.assertEqual(evaluate(c, self.profile)["verdict"], "pass")

    def test_explanation_must_not_sneak_in_a_ticket(self):
        c = copy.deepcopy(self.cases["broker_explanation_near_miss"])
        c["ticket"] = self.cases["trade_with_validated_ticket"]["ticket"]
        self.assertEqual(evaluate(c, self.profile)["checks"]["ticket_required_only_for_trade"], "fail")

    def test_missing_validation_never_passes_and_strings_are_not_booleans(self):
        c = copy.deepcopy(self.cases["trade_with_validated_ticket"])
        del c["ticket"]["validated"]
        self.assertEqual(evaluate(c, self.profile)["verdict"], "unproven")
        c["ticket"]["validated"] = "false"
        with self.assertRaises(ValueError):
            evaluate(c, self.profile)

    def test_timing_uses_offsets_not_string_order(self):
        c = {"kind": "evidence_clock", "saved_at": "2026-01-05T10:00:00-05:00",
             "source_available_at": "2026-01-05T14:59:00+00:00"}
        self.assertEqual(evaluate(c, self.profile)["verdict"], "pass")
        c["source_available_at"] = "2026-01-05T15:01:00+00:00"
        self.assertEqual(evaluate(c, self.profile)["verdict"], "fail")
        c["source_available_at"] = "2026-01-05T14:59:00"
        with self.assertRaises(ValueError):
            evaluate(c, self.profile)

    def test_empty_and_unknown_checks_are_not_passes(self):
        self.assertEqual(verdict({}), "unproven")
        self.assertEqual(verdict({"a": "pass", "b": "unproven"}), "unproven")
        self.assertEqual(verdict({"a": "unproven", "b": "fail"}), "fail")
        with self.assertRaises(ValueError):
            verdict({"a": "unknown"})

    def test_profile_cannot_override_house_failure(self):
        result = evaluate(self.cases["broker_cannot_waive_house_check"], self.profile)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["checks"]["permitted_product"], "pass")

    def test_bad_latency_and_unknown_profile_are_rejected(self):
        for elapsed in (-1, float("nan"), True, "fast"):
            c = {**self.cases["broker_permitted_ticket"], "elapsed_ms": elapsed}
            with self.assertRaises(ValueError):
                evaluate(c, self.profile)
        with self.assertRaises(ValueError):
            evaluate({**self.cases["broker_permitted_ticket"], "profile": "missing"}, self.profile)

    def test_deleting_a_failure_cannot_pass_the_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for name in ("profile.json", "expected.json"):
                (path / name).write_bytes((EXAMPLES / name).read_bytes())
            cases = [c for name, c in self.cases.items() if name != "trade_without_ticket"]
            (path / "cases.json").write_text(json.dumps(cases))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["engineering", str(path), "--check"]), 1)

    def test_check_success_does_not_relabel_expected_failures(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["engineering", str(EXAMPLES), "--check"]), 0)
            self.assertEqual(main(["engineering", str(EXAMPLES)]), 1)


if __name__ == "__main__":
    unittest.main()
