"""Build a scorecard: settle each system's forecasts, then compare them on identical events.

The comparison refuses an incomplete record. Every forecast file must account for every event,
either with a score or with an explicit ``missing`` record. An event left out of a file is not
treated as neutral or skipped: the scorecard marks the comparison incomplete, lists the absent
events first, and reports no accuracy figures for any system until the record is whole. Dropping
an awkward case therefore cannot improve a headline.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from labkit.records import Event, ForecastFile
from labkit.settle import VERDICTS, Settlement, settle

#: The rubric's fixed abstention half-widths for the accuracy-coverage curve.
HALF_WIDTHS: tuple[float, ...] = (0, 2, 5, 7.5, 10, 15, 20)


@dataclass(frozen=True)
class Completeness:
    system: str
    absent: tuple[str, ...]
    unknown: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.absent and not self.unknown


@dataclass(frozen=True)
class SystemResult:
    system: str
    description: str
    settlements: tuple[Settlement, ...]
    counts: dict[str, int]
    eligible_events: int
    #: Rows bullish/bearish/neutral against columns up/down/zero, on-time settled forecasts only.
    primary_table: dict[str, dict[str, int]]
    curve: tuple[dict[str, float | int | None], ...]

    @property
    def directional(self) -> int:
        return self.counts["correct"] + self.counts["wrong"]

    @property
    def accuracy(self) -> float | None:
        return _ratio(self.counts["correct"], self.directional)

    @property
    def settled_scored(self) -> int:
        """On-time scored forecasts whose outcome settled: the base of directional coverage."""
        return sum(self.counts[v] for v in ("correct", "wrong", "tie", "neutral"))

    @property
    def settled_directional_coverage(self) -> float | None:
        return _ratio(self.directional + self.counts["tie"], self.settled_scored)

    @property
    def operational_forecast_coverage(self) -> float | None:
        on_time = self.settled_scored + self.counts["pending"] + self.counts["unresolved"]
        return _ratio(on_time, self.eligible_events)


@dataclass(frozen=True)
class PairedPanel:
    """Events where both systems have an on-time forecast with a settled outcome."""

    events: int
    rows: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class Scorecard:
    events: tuple[Event, ...]
    completeness: tuple[Completeness, ...]
    systems: tuple[SystemResult, ...]
    paired: PairedPanel | None

    @property
    def complete(self) -> bool:
        return all(c.ok for c in self.completeness)

    @property
    def exit_code(self) -> int:
        return 0 if self.complete else 1


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def check_completeness(events: tuple[Event, ...], file: ForecastFile) -> Completeness:
    event_ids = [e.event_id for e in events]
    forecast_ids = {f.event_id for f in file.forecasts}
    return Completeness(
        system=file.system,
        absent=tuple(e for e in event_ids if e not in forecast_ids),
        unknown=tuple(sorted(forecast_ids - set(event_ids))),
    )


def _primary_table(settlements: tuple[Settlement, ...]) -> dict[str, dict[str, int]]:
    table = {call: {"up": 0, "down": 0, "zero": 0} for call in ("bullish", "bearish", "neutral")}
    for s in settlements:
        if s.verdict not in ("correct", "wrong", "tie", "neutral") or s.call is None or s.return_pct is None:
            continue
        column = "up" if s.return_pct > 0 else "down" if s.return_pct < 0 else "zero"
        table[s.call][column] += 1
    return table


def _curve(settlements: tuple[Settlement, ...]) -> tuple[dict[str, float | int | None], ...]:
    """Accuracy against coverage at fixed half-widths around 50, over on-time settled forecasts.

    A score at or beyond either boundary (50 + w, 50 - w) is directional; exactly 50 abstains even
    at zero width. Exact-zero returns are counted apart and left out of accuracy.
    """
    settled = [s for s in settlements if s.verdict in ("correct", "wrong", "tie", "neutral")]
    points: list[dict[str, float | int | None]] = []
    for w in HALF_WIDTHS:
        called = right = ties = 0
        for s in settled:
            assert s.score is not None and s.return_pct is not None
            if s.score == 50 or not (s.score >= 50 + w or s.score <= 50 - w):
                continue
            if s.return_pct == 0:
                ties += 1
                continue
            called += 1
            if (s.score > 50) == (s.return_pct > 0):
                right += 1
        points.append(
            {
                "half_width": w,
                "called": called,
                "correct": right,
                "ties": ties,
                "settled": len(settled),
                "accuracy": _ratio(right, called),
                "coverage": _ratio(called + ties, len(settled)),
            }
        )
    return tuple(points)


def _system_result(events: tuple[Event, ...], file: ForecastFile) -> SystemResult:
    by_id = {f.event_id: f for f in file.forecasts}
    settlements = tuple(settle(e, by_id[e.event_id], file.system) for e in events)
    counts = Counter(s.verdict for s in settlements)
    return SystemResult(
        system=file.system,
        description=file.description,
        settlements=settlements,
        counts={v: counts.get(v, 0) for v in VERDICTS},
        eligible_events=len(events),
        primary_table=_primary_table(settlements),
        curve=_curve(settlements),
    )


def _paired(candidate: SystemResult, baseline: SystemResult) -> PairedPanel:
    graded = ("correct", "wrong", "tie", "neutral")
    pairs = [
        (c, b)
        for c, b in zip(candidate.settlements, baseline.settlements, strict=True)
        if c.verdict in graded and b.verdict in graded
    ]
    rows: dict[str, dict[str, int]] = {}

    def add(row: str, c: Settlement, b: Settlement) -> None:
        entry = rows.setdefault(row, {"events": 0, "candidate_correct": 0, "baseline_correct": 0})
        entry["events"] += 1
        entry["candidate_correct"] += c.verdict == "correct"
        entry["baseline_correct"] += b.verdict == "correct"

    for c, b in pairs:
        c_dir = c.call in ("bullish", "bearish")
        b_dir = b.call in ("bullish", "bearish")
        if c_dir and b_dir:
            add("both_called_same_direction" if c.call == b.call else "both_called_opposite", c, b)
        elif c_dir:
            add("only_candidate_called", c, b)
        elif b_dir:
            add("only_baseline_called", c, b)
        else:
            add("neither_called", c, b)
    return PairedPanel(events=len(pairs), rows=rows)


def build_scorecard(events: tuple[Event, ...], candidate: ForecastFile, baseline: ForecastFile) -> Scorecard:
    if candidate.system == baseline.system:
        raise ValueError(f"both forecast files name the same system ({candidate.system!r})")
    completeness = (check_completeness(events, candidate), check_completeness(events, baseline))
    if not all(c.ok for c in completeness):
        return Scorecard(events=events, completeness=completeness, systems=(), paired=None)
    cand, base = _system_result(events, candidate), _system_result(events, baseline)
    return Scorecard(events=events, completeness=completeness, systems=(cand, base), paired=_paired(cand, base))
