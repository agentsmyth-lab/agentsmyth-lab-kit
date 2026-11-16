# Interim earnings scorecard: season records

The records behind the [interim earnings scorecard](https://lab.agentsmyth.com/notes/lab-2-first-earnings-scorecard)
and its [methodology companion](https://lab.agentsmyth.com/methodology/rubric-v1-interim-scorecard).

```
python -m labkit season data/earnings-interim-2026-11-13 --check
```

This reproduces **29 figure groups** from frozen scores and outcomes: call grades, accuracy,
coverage, paired comparisons, period and reaction-size splits, ranking measures, confidence
intervals, universe counts, missing-forecast counts and the published reasoning-category tables.
It does not regenerate the forecasts or their scores. The scores were recalculated from saved
pre-release judgments under the season reference policy, without using subsequent returns;
they are not a copy of the scores originally displayed.

## Files

| File | Contents |
|---|---|
| `events.jsonl` | 607 eligible releases: identity, timing, outcome, forecast status, frozen scores and category labels |
| `universe.jsonl` | 1,544 candidate releases, with membership and exclusion labels |
| `figures.json` | Expected results for `season --check` |

The postgame forward calls, business-quality grades, forecast quotations and financial figures
in the narrative worked examples are outside this dataset. The Kit recomputes the pregame
scorecard arithmetic from supplied records; it does not independently authenticate their sources.

## Rules

| Item | Rule |
|---|---|
| Season | Releases from October 13, 2026 whose first full reaction session closed by November 13, 2026 |
| Universe | Fixed at the September 30 close: S&P 500 members, plus companies with a primary U.S. listing that file 10-K and 10-Q reports and were worth at least $10 billion that day. Foreign private issuers, depositary receipts and companies primarily listed outside the U.S. are excluded. |
| Release-day market value | A non-S&P company below $10 billion on release day is included only if the agent forecast it. The `below_10b_on_release_day` flag identifies these cases. |
| Release clock | An observed release or filing clock where available; otherwise the confirmed release side, represented as 7:00 a.m. ET before the open or 4:00 p.m. ET after the close |
| Outcome | Split-adjusted close-to-close return over the first full reaction session. A release during market hours is unresolved. |
| On time | The underlying forecast was saved before the release clock. A save clock is not a verified publication clock. |
| Calls | Bullish at 55 and above; bearish at 45 and below; 46–54 neutral, an abstention |
| Accuracy | Right directional calls divided by graded directional calls; exact-zero returns are ungraded ties |
| Coverage | Graded directional calls divided by **all 607 eligible releases**, including missing forecasts and unresolved outcomes |
| Average precision | Distinct score thresholds; tied scores enter together, independent of record order |

## What is public

| Fields | Meaning |
|---|---|
| `event`, `ticker`, `company`, `cik` | Event identity and SEC company identity |
| `sp500`, `sector`, `below_10b_on_release_day` | Membership and grouping needed for the reported comparisons |
| `release_date`, `release_time`, `release_time_basis` | Release clock and whether it is observed by side or supported by a specific clock |
| `outcome.status`, `start_date`, `end_date` | Settlement status and close-to-close window |
| `outcome.return_pct`, `market_return_pct`, `sector_return_pct` | Percentage returns, rounded to four decimal places; no absolute price observations |
| `agent.status`, `baseline.status` | `scored` or `missing` |
| `agent.saved_at`, `baseline.saved_at` | The saved pre-release forecast's clock |
| `agent.assessment_score` | Frozen 0–100 assessment before the evidence adjustment |
| `agent.evidence_adjusted_score` | Frozen 0–100 score used for the primary agent comparison |
| `baseline.assessment_score` | Frozen 0–100 Baseline comparison score |
| `agent.reasoning_group` | A category for a directional call; null for neutral calls |
| `agent.missing_reason` | The recorded coverage gap: outage, early reported flag, scheduler list, market-value gate, post-release stage, not considered, or late/wrong-date run |

Scores are ordinal assessments, not probabilities. The `raw` figure group in `figures.json`
refers to the assessment score before the evidence adjustment.

### Reasoning categories

The labels are `bullish_positive_guidance`, `bullish_without_support`, `bearish_adverse`,
`bearish_in_line`, `bearish_no_central`, `bearish_tied` and, if unavailable, `bearish_unlabelled`.
They preserve the frozen classification used for the published analysis. Comparison labels
were assigned with returns and grades withheld; the same method was applied to later calls.
The Kit recomputes the counts and outcomes **within** those groups. It does not rerun the classifier
or expose the row-level judgments used to assign the groups.

## What remains private

The generation formulas and weights, individual KPI and guidance judgments, component votes,
model prompts, source excerpts, written reasoning, analyst-reference values, raw price
observations and operational identifiers. None is required to reproduce the scorecard from
its frozen scores and returns.

The grading rules and metric calculations remain open in [`labkit/season.py`](../../labkit/season.py).
