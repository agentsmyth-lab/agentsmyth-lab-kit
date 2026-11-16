# Earnings settlement example

Twelve synthetic events. Every company, price and timestamp is invented. Each event exercises one rule from section 2 of the rubric.

| Event | What it tests | Candidate | Baseline |
|---|---|---|---|
| E-01 | Bullish calls on a rise | 62, correct | 58, correct |
| E-02 | Bearish call on a fall; a neutral score abstains | 38, correct | 52, neutral |
| E-03 | A wrong bearish call (deleted in the control) | 41, wrong | 60, correct |
| E-04 | Both bullish on a fall | 57, wrong | 66, wrong |
| E-05 | Scores exactly at the boundaries: 55 is bullish, 45 is bearish | 55, correct | 45, wrong |
| E-06 | Scores just inside the neutral range: 46 and 54 | 46, neutral | 54, neutral |
| E-07 | A return of exactly zero is a tie | 60, tie | 40, tie |
| E-08 | A score of exactly 50 abstains | 50, neutral | 70, correct |
| E-09 | A forecast saved after the release is late | 65, late | 35, correct |
| E-10 | The ending price is missing, so the outcome is unresolved | 58, unresolved | 44, unresolved |
| E-11 | A failed run is recorded as missing, not neutral | missing | 48, neutral |
| E-12 | The reaction session has not closed | 61, pending | 39, pending |

`controls/candidate-dropped-case.json` is the candidate file with E-03 deleted. Without the completeness check, deleting that wrong call would lift the candidate's accuracy from 3 of 5 to 3 of 4; the Kit refuses the comparison instead.

`expected/` holds the saved output of `python -m labkit run examples/earnings --out <dir>`.
