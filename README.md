# AgentSmyth Lab Kit

A small, runnable kit for checking earnings forecasts the way the [AgentSmyth Lab](https://lab.agentsmyth.com/) does: settle each saved call against what the stock did, count every forecast that could not be graded, and compare two systems on the same events with every denominator shown.

It runs on a laptop with Python 3.10 or later and nothing else: no packages to install, no account, no market data feed, no model calls.

```
python -m labkit run examples/earnings
```

It also carries the records behind the Lab's [interim earnings scorecard](https://lab.agentsmyth.com/notes/lab-2-first-earnings-scorecard), and recomputes its results:

```
python -m labkit season data/earnings-interim-2026-11-13 --check
```

## What it does

Given a list of earnings events and two files of saved forecasts (a candidate and a baseline), the Kit:

1. **Settles every forecast** under section 2 of the Lab's published [rubric](https://lab.agentsmyth.com/methodology/rubric-v1). A score of 55 or above is a bullish call, 45 or below is bearish, and 46 to 54 is neutral, which counts as an abstention, not a forecast of a small move.
2. **Keeps every forecast that can't be graded in the record**, under its own label: a neutral call, a tie at exactly zero, a forecast saved too late, a missing forecast, an outcome still pending, and an outcome missing a price. None of them is folded into accuracy or quietly dropped.
3. **Refuses an incomplete comparison.** Every forecast file must account for every event, with a score or an explicit `missing` record. If an event is simply absent, the Kit reports which one, prints no accuracy for either system, and exits with code 1. Deleting an awkward case cannot improve a headline.
4. **Reports with denominators**: directional accuracy, coverage, the calls-against-returns table, accuracy against coverage at the rubric's fixed neutral ranges, a paired comparison on identical events, and every event's verdict. Output is Markdown for reading and JSON for checking, and it is byte-for-byte reproducible.

## Try it

```
python -m labkit run examples/earnings --out out/
```

prints the scorecard and writes `out/scorecard.md` and `out/scorecard.json`. They match the saved copies in [`examples/earnings/expected/`](examples/earnings/expected/).

Then run the control, a candidate file with one wrong call deleted:

```
python -m labkit run examples/earnings --candidate examples/earnings/controls/candidate-dropped-case.json
```

The Kit names the absent event, reports no accuracy and exits with code 1.

Run the tests:

```
python -m unittest discover -s tests -t .
```

## The example

[`examples/earnings/`](examples/earnings/) holds twelve **synthetic** events. Every company, price and timestamp is invented; each event exercises one rule: correct and wrong calls in both directions, scores exactly at 45, 46, 50, 54 and 55, a tie at exactly zero, a forecast saved after the release, an outcome missing its ending price, a failed run recorded as missing, and a release whose reaction session has not closed. The example's [README](examples/earnings/README.md) lists them.

## Engineering Note 1 examples

```
python -m labkit engineering examples/engineering-1 --check
```

The [17 synthetic fixtures](examples/engineering-1/) illustrate evidence timing, a grader's
known-bad control, the trade-ticket requirement and a fictional broker's additional rules.
They reproduce pass, fail and unproven verdicts without calling a model. They also include the
near miss: an explanation must not produce a trade ticket. The command checks the expected
verdicts; it does not claim that the live platform passed these tests.

## The interim scorecard

[`data/earnings-interim-2026-11-13/`](data/earnings-interim-2026-11-13/) holds the season records behind the Lab's interim earnings scorecard: 607 eligible releases, each with its timing, outcome and frozen scores, plus the 1,544 candidate releases screened for eligibility.

The scores were recalculated from saved pre-release judgments under the season reference policy, without using later returns. The Kit grades those frozen scores; it does not regenerate them. The generation formulas, weights and individual judgments remain private.

[`labkit/season.py`](labkit/season.py) computes the pregame scorecard's headline, paired comparison, accuracy against coverage, reaction-size and period splits, ranking measures, day-resampled confidence intervals, universe and missing-forecast counts, and outcomes within the frozen reasoning categories. These are the 29 figure groups checked below. The postgame forward calls, business-quality grades, forecast quotations and financial figures in the narrative examples are outside this dataset.

```
python -m labkit season data/earnings-interim-2026-11-13 --check
```

prints the headline and checks each figure against the dataset's `figures.json`; `--out figures.json` writes them. The dataset's [README](data/earnings-interim-2026-11-13/README.md) lists every public field and what remains private.

Coverage uses **all eligible releases**, including missing forecasts and unresolved outcomes.
Average precision groups equal scores at one threshold, so changing the order of tied records
cannot change the result. Neither calculation treats the 0–100 assessment score as a probability.

## Using your own records

Put an `events.json` and a `forecasts/` folder in a directory and point the Kit at it. The formats are in [`docs/record-format.md`](docs/record-format.md). Every timestamp needs a UTC offset, every score is an integer from 0 to 100, and a settled outcome carries its prices or its return (when both are given, they must agree).

The Kit grades the record you give it. It does not fetch prices, generate forecasts, or check that a timestamp is genuine; those belong to whoever keeps the record.

## What is not in 0.1

- The general `run` report does not yet compute benchmark-relative returns, the company-scaled small-move band, ranking measures or score bands. The `season` command computes the ones the interim scorecard uses, for its dataset.
- Grading the business half of a forecast (revenue, earnings per share, guidance) is not included.

## Versions

See [CHANGELOG.md](CHANGELOG.md). Releases are tagged `vX.Y.Z`; the history of this repository holds releases only.

## Contributing

Issues are welcome. This repository receives releases only, so pull requests can't be merged here directly; accepted changes are carried into the next release with credit.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
