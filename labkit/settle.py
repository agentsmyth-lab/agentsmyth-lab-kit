"""Settle saved forecasts against market outcomes, following section 2 of the published rubric.

The rules, in the order they apply to one forecast:

1. A missing forecast is ``missing``. It is not neutral.
2. A forecast saved at or after the event's reference time is ``late``. It is kept in the
   record and counted separately, never graded as if it were on time.
3. The score is classified: 55 or above is bullish, 45 or below is bearish, 46 to 54 is
   neutral. Neutral is an abstention, not a forecast of a small move.
4. An outcome that has not closed yet is ``pending``; one missing a price is ``unresolved``.
   Neither is ever counted as a zero return.
5. On a settled outcome, a neutral call is ``neutral``. A directional call is ``correct`` when
   its sign matches the return, ``wrong`` when it does not, and a ``tie`` at exactly zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from labkit.records import Event, Forecast

Call = Literal["bullish", "bearish", "neutral"]
Verdict = Literal["correct", "wrong", "tie", "neutral", "pending", "unresolved", "late", "missing"]

VERDICTS: tuple[Verdict, ...] = ("correct", "wrong", "tie", "neutral", "pending", "unresolved", "late", "missing")

BULLISH_AT = 55
BEARISH_AT = 45


@dataclass(frozen=True)
class Settlement:
    event_id: str
    system: str
    score: int | None
    call: Call | None
    return_pct: float | None
    verdict: Verdict
    reason: str


def classify(score: int, *, bullish_at: int = BULLISH_AT, bearish_at: int = BEARISH_AT) -> Call:
    """The season reference policy: bullish at 55 and above, bearish at 45 and below."""
    if score >= bullish_at:
        return "bullish"
    if score <= bearish_at:
        return "bearish"
    return "neutral"


def settle(event: Event, forecast: Forecast, system: str) -> Settlement:
    if forecast.event_id != event.event_id:
        raise ValueError(f"forecast for {forecast.event_id!r} settled against event {event.event_id!r}")

    def result(verdict: Verdict, reason: str, call: Call | None = None) -> Settlement:
        return Settlement(
            event_id=event.event_id,
            system=system,
            score=forecast.score,
            call=call,
            return_pct=event.outcome.return_pct,
            verdict=verdict,
            reason=reason,
        )

    if forecast.status == "missing":
        return result("missing", forecast.note or "no forecast was saved for this event")
    assert forecast.score is not None and forecast.saved_at is not None  # guaranteed by records.py
    if forecast.saved_at >= event.reference_time:
        return result("late", f"saved at {forecast.saved_at.isoformat()}, not before {event.reference_time.isoformat()}")

    call = classify(forecast.score)
    outcome = event.outcome
    if outcome.status == "pending":
        return result("pending", outcome.note or "the ending session has not closed", call)
    if outcome.status == "unresolved":
        return result("unresolved", outcome.note or "a price needed for the return is missing", call)

    assert outcome.return_pct is not None  # a settled outcome always carries a return
    if call == "neutral":
        return result("neutral", "a neutral score abstains", call)
    if outcome.return_pct == 0:
        return result("tie", "the return was exactly zero", call)
    rose = outcome.return_pct > 0
    if (call == "bullish") == rose:
        return result("correct", "the call's direction matched the return", call)
    return result("wrong", "the call's direction did not match the return", call)
