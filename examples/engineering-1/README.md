# Engineering Note 1: small runnable examples

These synthetic fixtures illustrate checks from [Engineering Note 1](https://lab.agentsmyth.com/notes/engineering-1-ready-to-ship)
and its [case studies](https://lab.agentsmyth.com/methodology/verdict-v1-worked-examples).
They contain no original reports, client records or model calls.

```
python -m labkit engineering examples/engineering-1 --check
```

The command evaluates 17 cases and compares every check with `expected.json`. Some cases must
**fail**; others must remain **unproven**. Exit code 0 with `--check` means those expected verdicts
were reproduced, not that all cases passed. A deleted case makes the comparison fail.
Without `--check`, any failed or unproven case produces exit code 1. Malformed inputs exit 2.
Add `--out out/engineering.json` to save the results.

| Published case study | What you can run here | What it establishes |
|---|---|---|
| 1. Grade what was said at the time | Available, later and missing source clocks | Later evidence cannot backfill a saved claim; a missing clock is unproven |
| 2. Grade the grader | A correct disclosure claim, its known-bad opposite, and an incomplete answer key | A disclosed fact cannot be called undisclosed; absence from an incomplete key is not proof of error |
| 3. Write the requirement down | A trade with a validated ticket, a missing ticket, a missing validation receipt | A trade request needs a ticket and evidence of validation |
| 4. Register before the outcome | The separate [earnings fixtures](../earnings/) | An otherwise correct call saved after release does not count |
| 5. Customer rules add to the house rules | The fictional broker below | Passing customer checks cannot waive a failed house check |

## The fictional broker

Its profile requires approved sources, a disclaimer and delivery within **25 seconds**. It permits
only cash-equity recommendations. A `restricted_product` ticket fails even when its supplied
validation receipt passes. An explanation about that product without a ticket passes the near-miss
case. Product names are generic; this is a small analogue of the published example.

The house checks still require a validation receipt and a stated worst case for every ticket.
Fixtures separately test a forbidden product, unapproved source, wrong disclaimer, late response,
missing timing, and a house failure that the customer cannot waive.

## What the fixtures do not establish

These are deterministic checks on supplied structured observations. They do not parse prose,
prove the cause of a market move, reproduce the published live-agent trial counts, authenticate
timestamps or verify that a real ticket's arithmetic is correct. The disclosure key and ticket
validation receipt are inputs. In a real system their producers need their own tests.

The profile check runs after an output. It does not demonstrate the platform's tool restrictions
before generation. No synthetic result here is a new measurement of the production system.

Inspect `cases.json` for the observations, `profile.json` for the customer rules and
`expected.json` for the expected checks. The evaluator is [`labkit/engineering.py`](../../labkit/engineering.py).
