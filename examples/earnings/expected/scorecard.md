# Earnings scorecard: Candidate against Baseline

Events: 12. Calls: bullish at 55 and above, bearish at 45 and below, neutral between (an abstention). Accuracy is correct / (correct + wrong); ties, neutral, pending, unresolved, late and missing forecasts are counted beside it, never inside it.

## Results

| | Candidate | Baseline |
|---|---:|---:|
| Directional accuracy | 3 of 5 (60.0%) | 4 of 6 (66.7%) |
| Settled directional coverage | 6 of 8 (75.0%) | 7 of 10 (70.0%) |
| Operational forecast coverage | 10 of 12 (83.3%) | 12 of 12 (100.0%) |
| Correct | 3 | 4 |
| Wrong | 2 | 2 |
| Tie | 1 | 1 |
| Neutral | 2 | 3 |
| Pending | 1 | 1 |
| Unresolved | 1 | 1 |
| Late | 1 | 0 |
| Missing | 1 | 0 |

### Candidate: calls against returns

| Call | Rose | Fell | Exactly zero |
|---|---:|---:|---:|
| Bullish | 2 | 1 | 1 |
| Bearish | 1 | 1 | 0 |
| Neutral | 1 | 1 | 0 |

### Baseline: calls against returns

| Call | Rose | Fell | Exactly zero |
|---|---:|---:|---:|
| Bullish | 3 | 1 | 0 |
| Bearish | 1 | 1 | 1 |
| Neutral | 1 | 2 | 0 |

## Accuracy against coverage

Fixed neutral ranges around 50. Half-width 5 is the season rule.

| Half-width | Candidate | Baseline |
|---:|---:|---:|
| 0 | 4 of 6 (66.7%) on 87.5% | 4 of 9 (44.4%) on 100.0% |
| 2 | 4 of 6 (66.7%) on 87.5% | 4 of 9 (44.4%) on 100.0% |
| 5 | 3 of 5 (60.0%) on 75.0% | 4 of 6 (66.7%) on 70.0% |
| 7.5 | 2 of 3 (66.7%) on 50.0% | 4 of 5 (80.0%) on 60.0% |
| 10 | 2 of 2 (100.0%) on 37.5% | 3 of 4 (75.0%) on 50.0% |
| 15 | 0 of 0 (n/a) on 0.0% | 2 of 3 (66.7%) on 30.0% |
| 20 | 0 of 0 (n/a) on 0.0% | 1 of 1 (100.0%) on 10.0% |

## Paired comparison

8 events where both systems have an on-time forecast and a settled outcome.

| | Events | Candidate correct | Baseline correct |
|---|---:|---:|---:|
| Both called, same direction | 2 | 1 | 1 |
| Both called, opposite directions | 3 | 1 | 1 |
| Only the candidate called | 1 | 1 | 0 |
| Only the baseline called | 1 | 0 | 1 |
| Neither called | 1 | 0 | 0 |

## Every event

| Event | Return | Candidate score | Candidate verdict | Baseline score | Baseline verdict |
|---|---:|---:|---|---:|---|
| `E-01` Northwind Robotics | +6.20% | 62 | correct | 58 | correct |
| `E-02` Harbor Lane Foods | -4.50% | 38 | correct | 52 | neutral |
| `E-03` Copperline Utilities | +2.50% | 41 | wrong | 60 | correct |
| `E-04` Bluefield Semiconductor | -10.00% | 57 | wrong | 66 | wrong |
| `E-05` Juniper Freight | +3.00% | 55 | correct | 45 | wrong |
| `E-06` Ridgeway Insurance | -1.00% | 46 | neutral | 54 | neutral |
| `E-07` Saltmarsh Retail | +0.00% | 60 | tie | 40 | tie |
| `E-08` Tallgrass Energy | +4.00% | 50 | neutral | 70 | correct |
| `E-09` Orchard Health | -6.00% | 65 | late | 35 | correct |
| `E-10` Lanternfish Media | unresolved | 58 | unresolved | 44 | unresolved |
| `E-11` Westbrook Materials | +5.00% | — | missing | 48 | neutral |
| `E-12` Kestrel Payments | pending | 61 | pending | 39 | pending |
