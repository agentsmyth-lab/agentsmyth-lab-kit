"""Command line: ``python -m labkit run <example-dir>`` and ``python -m labkit season <dataset-dir>``.

The example directory holds ``events.json`` and ``forecasts/candidate.json`` and
``forecasts/baseline.json``. Either forecast file can be replaced with ``--candidate`` or
``--baseline``. The Markdown report prints to the terminal; ``--out`` also writes
``scorecard.md`` and ``scorecard.json``.

Exit codes: 0 the scorecard is complete; 1 the record is incomplete (an event is absent from a
forecast file) so no accuracy was reported; 2 an input file is malformed.

``season`` recomputes the figures of the Lab's published season scorecard from the season records
(``events.jsonl``, ``universe.jsonl``), grading both systems' frozen recalculated scores. It
prints the headline; ``--out`` writes every figure as JSON; ``--check`` compares them with the
dataset's ``figures.json`` and exits 1 on any difference.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from labkit.records import RecordError, load_events, load_forecasts
from labkit.report import to_json, to_markdown
from labkit.scorecard import build_scorecard
from labkit import engineering, season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m labkit", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="settle both systems' forecasts and compare them")
    run.add_argument("example", type=Path, help="directory holding events.json and forecasts/")
    run.add_argument("--candidate", type=Path, help="candidate forecast file (default: forecasts/candidate.json)")
    run.add_argument("--baseline", type=Path, help="baseline forecast file (default: forecasts/baseline.json)")
    run.add_argument("--out", type=Path, help="directory to write scorecard.md and scorecard.json")
    sea = sub.add_parser("season", help="recompute the figures of a published season scorecard")
    sea.add_argument("dataset", type=Path, help="directory holding events.jsonl and universe.jsonl")
    sea.add_argument("--out", type=Path, help="file to write every figure to, as JSON")
    sea.add_argument("--check", action="store_true", help="compare with the dataset's figures.json; exit 1 on a difference")
    eng = sub.add_parser("engineering", help="run synthetic checks from Engineering Note 1")
    eng.add_argument("example", type=Path, help="directory holding cases.json, profile.json and expected.json")
    eng.add_argument("--check", action="store_true", help="compare all case verdicts with expected.json")
    eng.add_argument("--out", type=Path, help="write the check results as JSON")
    args = parser.parse_args(argv)
    if args.command == "season":
        return run_season(args)
    if args.command == "engineering":
        return run_engineering(args)

    try:
        events = load_events(args.example / "events.json")
        candidate = load_forecasts(args.candidate or args.example / "forecasts" / "candidate.json")
        baseline = load_forecasts(args.baseline or args.example / "forecasts" / "baseline.json")
        card = build_scorecard(events, candidate, baseline)
    except (RecordError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    names = {"candidate_name": candidate.system, "baseline_name": baseline.system}
    markdown = to_markdown(card, **names)
    print(markdown, end="")
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "scorecard.md").write_text(markdown, encoding="utf-8")
        (args.out / "scorecard.json").write_text(to_json(card, **names), encoding="utf-8")
    if not card.complete:
        print("\nerror: incomplete record; see the list above", file=sys.stderr)
    return card.exit_code


def run_engineering(args: argparse.Namespace) -> int:
    try:
        results = engineering.load_results(args.example)
        expected = json.loads((args.example / "expected.json").read_text(encoding="utf-8")) if args.check else None
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("Synthetic engineering checks (not live platform acceptance):")
    for name, result in results.items():
        print(f"{name}: {result['verdict']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.check:
        changed = sorted(k for k in set(expected) | set(results) if expected.get(k) != results.get(k))
        if changed:
            print("error: missing or changed cases: " + ", ".join(changed), file=sys.stderr)
            return 1
        print(f"All {len(results)} cases match their expected verdicts, including fails and unproven checks.")
        return 0
    return 0 if all(r["verdict"] == "pass" for r in results.values()) else 1


def run_season(args: argparse.Namespace) -> int:
    try:
        events, universe = season.load(args.dataset)
        figures = season.figures(events, universe)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(figures, indent=1, sort_keys=True) + "\n"
    a, b = figures["agent"], figures["baseline"]
    print(f"{figures['eligible']} eligible releases, {figures['settled']} settled "
          f"({figures['rose']} rose, {figures['fell']} fell)")
    for name, f in (("Agent", a), ("Baseline", b)):
        print(f"{name:9} right {f['right']} of {f['called']} calls ({f['accuracy']}%), called {f['called_share']}% "
              f"of eligible, neutral {f['neutral']}, missing {f['missing']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    if args.check:
        published = json.loads((args.dataset / "figures.json").read_text(encoding="utf-8"))
        differ = sorted(k for k in set(published) | set(figures) if published.get(k) != figures.get(k))
        if differ:
            print("error: figures differ from figures.json: " + ", ".join(differ), file=sys.stderr)
            return 1
        print(f"All {len(published)} figure groups match figures.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
