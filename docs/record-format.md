# Record format

Two kinds of file, both JSON.

## `events.json`

```json
{
  "description": "optional",
  "events": [
    {
      "event_id": "E-01",
      "company": "Northwind Robotics",
      "ticker": "SYN-NWR",
      "release_date": "2026-10-14",
      "release_phase": "after_close",
      "reference_time": "2026-10-14T16:00:00-04:00",
      "synthetic": true,
      "outcome": {
        "status": "settled",
        "start_price": 50.0,
        "end_price": 53.1,
        "source": "where the prices came from"
      }
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `event_id` | Unique within the file. Forecast files refer to events by this id. |
| `release_phase` | `before_open`, `after_close` or `intraday_or_ambiguous`. It records which sessions the return spans (rubric section 2); the Kit does not look up sessions itself. |
| `reference_time` | A forecast must be saved strictly before this instant to count as on time. Must carry a UTC offset. |
| `synthetic` | `true` when the event is invented. |
| `outcome.status` | `settled`, `pending` (the ending session has not closed) or `unresolved` (a price needed for the return is missing). |
| `outcome.start_price`, `outcome.end_price` | Split-adjusted closes. The return is `end / start − 1`. |
| `outcome.return_pct` | The return in percent, if prices are not given. When both are given they must agree to within 0.005 points. |
| `outcome.source`, `outcome.note`, `outcome.start_date`, `outcome.end_date` | Provenance, carried into nothing that is graded. |

Only a `settled` outcome may carry a return. A `pending` or `unresolved` outcome is never treated as a zero return.

## `forecasts/<system>.json`

```json
{
  "system": "Candidate",
  "description": "optional",
  "forecasts": [
    {"event_id": "E-01", "status": "scored", "score": 62, "saved_at": "2026-10-13T22:00:00-04:00"},
    {"event_id": "E-11", "status": "missing", "note": "the run failed; no forecast was saved"}
  ]
}
```

| Field | Meaning |
|---|---|
| `status` | `scored`, or `missing` when the system produced no forecast for the event. |
| `score` | Integer, 0 to 100. Required when scored; not allowed when missing. |
| `saved_at` | When the forecast was saved. Required when scored; must carry a UTC offset. |

A forecast file must contain exactly one record for every event in `events.json`. An event that is absent (as opposed to recorded as `missing`) makes the record incomplete, and the Kit reports no accuracy until it is fixed.

## Verdicts

| Verdict | When |
|---|---|
| `missing` | The forecast record says `missing`. |
| `late` | Saved at or after the event's reference time. |
| `pending` | The outcome is pending. |
| `unresolved` | The outcome is missing a price. |
| `neutral` | A settled outcome and a score from 46 to 54. |
| `tie` | A directional call and a return of exactly zero. |
| `correct` | A directional call whose sign matches the return. |
| `wrong` | A directional call whose sign does not match the return. |

The rules apply in that order. Directional accuracy is `correct / (correct + wrong)`; every other verdict is reported beside it.
