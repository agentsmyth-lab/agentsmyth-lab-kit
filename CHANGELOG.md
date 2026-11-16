# Changelog

## 0.1.0 (November 16, 2026)

First release.

- Record format for earnings events and saved forecasts, validated on load.
- Settlement under section 2 of the AgentSmyth Lab rubric: bullish at 55 and above, bearish at 45 and below, neutral between; ties, late, missing, pending and unresolved forecasts kept and counted.
- A comparison that refuses an incomplete record: an event absent from a forecast file stops the scorecard (exit code 1) instead of shrinking the denominator.
- Reports in Markdown and JSON: directional accuracy with its counts, coverage, calls against returns, accuracy against coverage at the rubric's fixed neutral ranges, a paired comparison, and every event's verdict.
- A synthetic earnings example with one event per rule, a dropped-case control, saved expected output, and tests.
- Seventeen synthetic Engineering Note 1 fixtures: evidence clocks, disclosure controls, the trade-ticket requirement and a fictional broker profile. Missing evidence stays unproven; customer checks cannot waive a house failure.
- The interim scorecard's frozen records: 607 eligible releases with recalculated scores, rounded returns, timing and status; 1,544 candidate releases with eligibility labels. Generation formulas, weights, row-level judgments and source text remain private.
- Frozen reasoning-category labels let readers reproduce group counts and outcomes without rerunning the classifier.
- `python -m labkit season`: recomputes 29 pregame scorecard figure groups and checks them against `figures.json`. Postgame calls, business-quality grades and financial figures quoted in narrative examples are outside this dataset.

- Accuracy-against-coverage uses every eligible release as its denominator. Average precision groups tied scores at one threshold rather than depending on record order.
