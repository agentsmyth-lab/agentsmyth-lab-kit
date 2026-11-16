"""The record format: events, their market outcomes, and the forecasts saved for them.

Every input is validated on load. A malformed record raises ``RecordError`` with the file and
the field at fault; nothing is silently skipped, because a skipped record would quietly change a
denominator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

OutcomeStatus = Literal["settled", "pending", "unresolved"]
ForecastStatus = Literal["scored", "missing"]
ReleasePhase = Literal["before_open", "after_close", "intraday_or_ambiguous"]

_OUTCOME_STATUSES = ("settled", "pending", "unresolved")
_FORECAST_STATUSES = ("scored", "missing")
_RELEASE_PHASES = ("before_open", "after_close", "intraday_or_ambiguous")


class RecordError(ValueError):
    """An input record is malformed. The message names the file and the field."""


@dataclass(frozen=True)
class Outcome:
    """The stock's reaction to one release.

    ``settled`` carries a return. ``pending`` means the ending session has not closed yet.
    ``unresolved`` means a price needed for the return is missing; it is never treated as zero.
    """

    status: OutcomeStatus
    return_pct: float | None
    start_date: str | None
    end_date: str | None
    start_price: float | None
    end_price: float | None
    source: str
    note: str


@dataclass(frozen=True)
class Event:
    event_id: str
    company: str
    ticker: str
    release_date: str
    release_phase: ReleasePhase
    #: A forecast must be saved strictly before this instant to count as on time.
    reference_time: datetime
    outcome: Outcome
    synthetic: bool


@dataclass(frozen=True)
class Forecast:
    """One system's saved forecast for one event.

    ``missing`` is an explicit record that the system produced no forecast for the event (a
    failed or skipped run). It is different from leaving the event out of the file, which the
    comparison treats as an incomplete record and refuses to grade.
    """

    event_id: str
    status: ForecastStatus
    score: int | None
    saved_at: datetime | None
    note: str


@dataclass(frozen=True)
class ForecastFile:
    system: str
    description: str
    forecasts: tuple[Forecast, ...]
    path: Path


def _require(obj: dict[str, Any], key: str, where: str) -> Any:
    if key not in obj:
        raise RecordError(f"{where}: missing required field {key!r}")
    return obj[key]


def _parse_time(value: Any, where: str) -> datetime:
    if not isinstance(value, str):
        raise RecordError(f"{where}: expected an ISO 8601 timestamp string, got {value!r}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RecordError(f"{where}: {value!r} is not an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise RecordError(f"{where}: {value!r} has no UTC offset; every timestamp must carry one")
    return parsed


def _optional_number(obj: dict[str, Any], key: str, where: str) -> float | None:
    value = obj.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RecordError(f"{where}.{key}: expected a number, got {value!r}")
    return float(value)


def _parse_outcome(raw: Any, where: str) -> Outcome:
    if not isinstance(raw, dict):
        raise RecordError(f"{where}: expected an object")
    status = _require(raw, "status", where)
    if status not in _OUTCOME_STATUSES:
        raise RecordError(f"{where}.status: {status!r} is not one of {_OUTCOME_STATUSES}")
    start_price = _optional_number(raw, "start_price", where)
    end_price = _optional_number(raw, "end_price", where)
    return_pct = _optional_number(raw, "return_pct", where)
    if status == "settled":
        if start_price is not None and end_price is not None:
            if start_price <= 0:
                raise RecordError(f"{where}.start_price: must be positive")
            computed = (end_price / start_price - 1) * 100
            if return_pct is not None and abs(computed - return_pct) > 0.005:
                raise RecordError(
                    f"{where}: return_pct {return_pct} disagrees with the prices ({computed:.4f}%)"
                )
            return_pct = computed
        if return_pct is None:
            raise RecordError(f"{where}: a settled outcome needs prices or return_pct")
    elif return_pct is not None:
        raise RecordError(f"{where}: a {status} outcome must not carry a return")
    return Outcome(
        status=status,
        return_pct=return_pct,
        start_date=raw.get("start_date"),
        end_date=raw.get("end_date"),
        start_price=start_price,
        end_price=end_price,
        source=str(_require(raw, "source", where)),
        note=str(raw.get("note", "")),
    )


def load_events(path: Path) -> tuple[Event, ...]:
    payload = _load_json(path)
    raw_events = _require(payload, "events", str(path))
    if not isinstance(raw_events, list) or not raw_events:
        raise RecordError(f"{path}: 'events' must be a non-empty list")
    events: list[Event] = []
    seen: set[str] = set()
    for i, raw in enumerate(raw_events):
        where = f"{path} events[{i}]"
        if not isinstance(raw, dict):
            raise RecordError(f"{where}: expected an object")
        event_id = str(_require(raw, "event_id", where))
        if event_id in seen:
            raise RecordError(f"{where}: duplicate event_id {event_id!r}")
        seen.add(event_id)
        phase = _require(raw, "release_phase", where)
        if phase not in _RELEASE_PHASES:
            raise RecordError(f"{where}.release_phase: {phase!r} is not one of {_RELEASE_PHASES}")
        events.append(
            Event(
                event_id=event_id,
                company=str(_require(raw, "company", where)),
                ticker=str(_require(raw, "ticker", where)),
                release_date=str(_require(raw, "release_date", where)),
                release_phase=phase,
                reference_time=_parse_time(_require(raw, "reference_time", where), f"{where}.reference_time"),
                outcome=_parse_outcome(_require(raw, "outcome", where), f"{where}.outcome"),
                synthetic=bool(_require(raw, "synthetic", where)),
            )
        )
    return tuple(events)


def load_forecasts(path: Path) -> ForecastFile:
    payload = _load_json(path)
    where_file = str(path)
    raw_forecasts = _require(payload, "forecasts", where_file)
    if not isinstance(raw_forecasts, list):
        raise RecordError(f"{path}: 'forecasts' must be a list")
    forecasts: list[Forecast] = []
    seen: set[str] = set()
    for i, raw in enumerate(raw_forecasts):
        where = f"{path} forecasts[{i}]"
        if not isinstance(raw, dict):
            raise RecordError(f"{where}: expected an object")
        event_id = str(_require(raw, "event_id", where))
        if event_id in seen:
            raise RecordError(f"{where}: duplicate forecast for event {event_id!r}")
        seen.add(event_id)
        status = _require(raw, "status", where)
        if status not in _FORECAST_STATUSES:
            raise RecordError(f"{where}.status: {status!r} is not one of {_FORECAST_STATUSES}")
        score: int | None = None
        saved_at: datetime | None = None
        if status == "scored":
            raw_score = _require(raw, "score", where)
            if isinstance(raw_score, bool) or not isinstance(raw_score, int) or not 0 <= raw_score <= 100:
                raise RecordError(f"{where}.score: expected an integer from 0 to 100, got {raw_score!r}")
            score = raw_score
            saved_at = _parse_time(_require(raw, "saved_at", where), f"{where}.saved_at")
        elif "score" in raw and raw["score"] is not None:
            raise RecordError(f"{where}: a missing forecast must not carry a score")
        forecasts.append(
            Forecast(event_id=event_id, status=status, score=score, saved_at=saved_at, note=str(raw.get("note", "")))
        )
    return ForecastFile(
        system=str(_require(payload, "system", where_file)),
        description=str(payload.get("description", "")),
        forecasts=tuple(forecasts),
        path=path,
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RecordError(f"{path}: file not found") from exc
    except json.JSONDecodeError as exc:
        raise RecordError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise RecordError(f"{path}: expected a JSON object at the top level")
    return payload
