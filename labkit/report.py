"""Render a scorecard as readable Markdown and as machine-readable JSON.

Every rate is printed beside its numerator and denominator. Output is deterministic: the same
inputs always produce byte-identical files, so a saved report can be checked with a plain diff.
"""

from __future__ import annotations

import json
from typing import Any

from labkit import __version__
from labkit.scorecard import Scorecard, SystemResult
from labkit.settle import BEARISH_AT, BULLISH_AT, VERDICTS

PAIRED_LABELS = {
    "both_called_same_direction": "Both called, same direction",
    "both_called_opposite": "Both called, opposite directions",
    "only_candidate_called": "Only the candidate called",
    "only_baseline_called": "Only the baseline called",
    "neither_called": "Neither called",
}


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _fraction(numerator: int, denominator: int) -> str:
    rate = None if denominator == 0 else numerator / denominator
    return f"{numerator} of {denominator} ({_pct(rate)})"


def to_markdown(card: Scorecard, *, candidate_name: str, baseline_name: str) -> str:
    lines = [f"# Earnings scorecard: {candidate_name} against {baseline_name}", ""]
    lines += [
        f"Events: {len(card.events)}. Calls: bullish at {BULLISH_AT} and above, bearish at {BEARISH_AT} and below, "
        "neutral between (an abstention). Accuracy is correct / (correct + wrong); ties, neutral, pending, "
        "unresolved, late and missing forecasts are counted beside it, never inside it.",
        "",
    ]

    if not card.complete:
        lines += ["## Incomplete record: no accuracy is reported", ""]
        lines += [
            "Every forecast file must account for every event, with a score or an explicit missing record. "
            "These do not, so the comparison stops here rather than grade a smaller set.",
            "",
        ]
        for c in card.completeness:
            if c.absent:
                lines.append(f"- **{c.system}**: {len(c.absent)} event(s) absent: " + ", ".join(f"`{e}`" for e in c.absent))
            if c.unknown:
                lines.append(f"- **{c.system}**: {len(c.unknown)} forecast(s) for unknown events: " + ", ".join(f"`{e}`" for e in c.unknown))
        return "\n".join(lines) + "\n"

    lines += ["## Results", "", "| | " + " | ".join(s.system for s in card.systems) + " |", "|---|" + "---:|" * len(card.systems)]
    rows: list[tuple[str, Any]] = [
        ("Directional accuracy", lambda s: _fraction(s.counts["correct"], s.directional)),
        ("Settled directional coverage", lambda s: _fraction(s.directional + s.counts["tie"], s.settled_scored)),
        ("Operational forecast coverage", lambda s: _fraction(s.eligible_events - s.counts["late"] - s.counts["missing"], s.eligible_events)),
    ]
    rows += [(verdict.capitalize(), (lambda v: lambda s: str(s.counts[v]))(verdict)) for verdict in VERDICTS]
    for label, fn in rows:
        lines.append(f"| {label} | " + " | ".join(fn(s) for s in card.systems) + " |")

    for s in card.systems:
        lines += ["", f"### {s.system}: calls against returns", ""]
        lines += ["| Call | Rose | Fell | Exactly zero |", "|---|---:|---:|---:|"]
        for call, cols in s.primary_table.items():
            lines.append(f"| {call.capitalize()} | {cols['up']} | {cols['down']} | {cols['zero']} |")

    lines += ["", "## Accuracy against coverage", "", "Fixed neutral ranges around 50. Half-width 5 is the season rule.", ""]
    lines += ["| Half-width | " + " | ".join(s.system for s in card.systems) + " |", "|---:|" + "---:|" * len(card.systems)]
    for i, w in enumerate(card.systems[0].curve):
        cells = []
        for s in card.systems:
            p = s.curve[i]
            cells.append(f"{p['correct']} of {p['called']} ({_pct(p['accuracy'])}) on {_pct(p['coverage'])}")
        lines.append(f"| {w['half_width']:g} | " + " | ".join(cells) + " |")

    assert card.paired is not None
    lines += ["", "## Paired comparison", ""]
    lines += [f"{card.paired.events} events where both systems have an on-time forecast and a settled outcome.", ""]
    lines += [f"| | Events | {candidate_name} correct | {baseline_name} correct |", "|---|---:|---:|---:|"]
    for key, label in PAIRED_LABELS.items():
        row = card.paired.rows.get(key, {"events": 0, "candidate_correct": 0, "baseline_correct": 0})
        lines.append(f"| {label} | {row['events']} | {row['candidate_correct']} | {row['baseline_correct']} |")

    lines += ["", "## Every event", ""]
    lines += ["| Event | Return | " + " | ".join(f"{s.system} score | {s.system} verdict" for s in card.systems) + " |"]
    lines += ["|---|---:|" + "---:|---|" * len(card.systems)]
    for i, event in enumerate(card.events):
        ret = event.outcome.return_pct
        ret_text = f"{ret:+.2f}%" if ret is not None else event.outcome.status
        cells = []
        for s in card.systems:
            st = s.settlements[i]
            cells.append(f"{'—' if st.score is None else st.score} | {st.verdict}")
        lines.append(f"| `{event.event_id}` {event.company} | {ret_text} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _system_json(s: SystemResult) -> dict[str, Any]:
    return {
        "system": s.system,
        "description": s.description,
        "eligible_events": s.eligible_events,
        "counts": s.counts,
        "directional_accuracy": {"correct": s.counts["correct"], "directional": s.directional, "rate": _round(s.accuracy)},
        "settled_directional_coverage": {
            "directional_including_ties": s.directional + s.counts["tie"],
            "settled_scored": s.settled_scored,
            "rate": _round(s.settled_directional_coverage),
        },
        "operational_forecast_coverage": {
            "on_time_forecasts": s.eligible_events - s.counts["late"] - s.counts["missing"],
            "eligible_events": s.eligible_events,
            "rate": _round(s.operational_forecast_coverage),
        },
        "primary_table": s.primary_table,
        "accuracy_coverage_curve": [
            {**p, "accuracy": _round(p["accuracy"]), "coverage": _round(p["coverage"])}  # type: ignore[arg-type]
            for p in s.curve
        ],
        "settlements": [
            {
                "event_id": st.event_id,
                "score": st.score,
                "call": st.call,
                "return_pct": _round(st.return_pct),
                "verdict": st.verdict,
                "reason": st.reason,
            }
            for st in s.settlements
        ],
    }


def to_json(card: Scorecard, *, candidate_name: str, baseline_name: str) -> str:
    payload: dict[str, Any] = {
        "kit_version": __version__,
        "rules": {"bullish_at": BULLISH_AT, "bearish_at": BEARISH_AT, "rubric": "AgentSmyth Lab rubric v1, section 2"},
        "candidate": candidate_name,
        "baseline": baseline_name,
        "events": len(card.events),
        "complete": card.complete,
        "completeness": [
            {"system": c.system, "absent": list(c.absent), "unknown": list(c.unknown)} for c in card.completeness
        ],
    }
    if card.complete:
        assert card.paired is not None
        payload["systems"] = [_system_json(s) for s in card.systems]
        payload["paired"] = {"events": card.paired.events, "rows": card.paired.rows}
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
