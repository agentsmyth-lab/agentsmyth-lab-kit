"""The Lab's interim earnings scorecard, recomputed from the published season records.

``load(directory)`` reads ``events.jsonl`` and ``universe.jsonl``; ``figures(events, universe)``
grades frozen scores and computes the scorecard figures the note, the methodology companion
and the worked examples cite. The scores were recalculated from saved pre-release judgments
under the season reference policy. The public Kit does not regenerate those judgments or scores.

Conventions (section 2 of the rubric): bullish at 55 and above, bearish at 45 and below, neutral
between (an abstention). A call is right when its direction matches the sign of the close-to-close
return over the first full session after the release; a return of exactly zero is a tie and is not
graded. A forecast saved at or after the release is late and does not count as a forecast.
"""

from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Any, Callable, Iterable

SYSTEMS = ("agent", "baseline", "raw")  # raw: the agent's score before the evidence adjustment
PERIODS = (("Oct 13-28", "2026-10-13", "2026-10-28"), ("Oct 29-Nov 4", "2026-10-29", "2026-11-04"),
           ("Nov 5-13", "2026-11-05", "2026-11-13"))
SIZES = (("<1", 0, 1), ("1-5", 1, 5), ("5-10", 5, 10), (">=10", 10, 1e9), ("<5", 0, 5), (">=5", 5, 1e9))
BANDS = (("<35", lambda x: x < 35), ("35-45", lambda x: 35 <= x <= 45), ("46-54", lambda x: 45 < x < 55),
         ("55-65", lambda x: 55 <= x <= 65), (">65", lambda x: x > 65))
HALF_WIDTHS = (0, 2, 5, 7.5, 10, 15, 20)
EXAMPLES = ("UBER", "T", "PLTR", "NOW", "INTC", "AXON", "C", "JPM", "GS", "PGR", "BNY", "MMC", "WFC", "BAC", "MS",
            "STT", "SCHW")
BOOTSTRAP_DRAWS = 4000
BOOTSTRAP_SEED = 20261111


def call(x: int) -> str:
    return "bullish" if x >= 55 else "bearish" if x <= 45 else "neutral"


def wide_call(x: int) -> str:
    """The Baseline's own, wider neutral range (40-60)."""
    return "bullish" if x > 60 else "bearish" if x < 40 else "neutral"


def pct(a: float, b: float) -> float | None:
    return round(100 * a / b, 1) if b else None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load(directory: Path | str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    directory = Path(directory)
    return _read_jsonl(directory / "events.jsonl"), _read_jsonl(directory / "universe.jsonl")


def _on_time(saved_at: str | None, release_time: str | None) -> bool:
    if not saved_at or not release_time:
        return False
    return datetime.fromisoformat(saved_at) < datetime.fromisoformat(release_time)


def derive(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten frozen scores and check whether their underlying forecasts were on time."""
    out = []
    for r in events:
        o, a, b = r["outcome"], r["agent"], r["baseline"]
        e = {k: r[k] for k in ("event", "ticker", "company", "sector", "release_date", "release_time",
                               "below_10b_on_release_day")}
        e.update(outcome_status=o["status"], start_date=o.get("start_date"), end_date=o.get("end_date"),
                 return_pct=o.get("return_pct"), market_return_pct=o.get("market_return_pct"),
                 sector_return_pct=o.get("sector_return_pct"), agent_missing_reason=a.get("missing_reason"))
        if a["status"] == "scored":
            e["reasoning_group"] = a.get("reasoning_group")
            on_time = _on_time(a.get("saved_at"), r["release_time"])
            e.update(agent_status="scored" if on_time else "late",
                     agent_score=_score(a, "evidence_adjusted_score"),
                     agent_score_before_adjustment=_score(a, "assessment_score"))
        else:
            e["agent_status"] = a["status"]
        if b["status"] == "scored":
            on_time = _on_time(b.get("saved_at"), r["release_time"])
            e.update(baseline_status="scored" if on_time else "late",
                     baseline_score=_score(b, "assessment_score"))
        else:
            e["baseline_status"] = b["status"]
        out.append(e)
    return out


def _score(record: dict[str, Any], key: str) -> int:
    value = record[key]
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        raise ValueError(f"{key} must be an integer between 0 and 100")
    return value


SCORE = {"agent": "agent_score", "baseline": "baseline_score", "raw": "agent_score_before_adjustment"}
STATUS = {"agent": "agent_status", "baseline": "baseline_status", "raw": "agent_status"}
Graded = list[tuple[dict[str, Any], str, bool]]


def figures(events: list[dict[str, Any]], universe: list[dict[str, Any]]) -> dict[str, Any]:
    """Every figure the interim pages cite, as a JSON-ready dict (tuples become lists)."""
    S = derive(events)
    SETTLED = [e for e in S if e["outcome_status"] == "settled"]

    def scored(s: str, evs: list[dict[str, Any]] = SETTLED) -> list[dict[str, Any]]:
        return [e for e in evs if e[STATUS[s]] == "scored"]

    def graded(s: str, evs: list[dict[str, Any]] = SETTLED, rule: Callable[[int], str] = call) -> Graded:
        out = []
        for e in scored(s, evs):
            k = rule(e[SCORE[s]])
            if k == "neutral" or e["return_pct"] == 0:
                continue
            out.append((e, k, (k == "bullish") == (e["return_pct"] > 0)))
        return out

    def acc(g: Graded) -> tuple[int, int]:
        return sum(r for _, _, r in g), len(g)

    R: dict[str, Any] = {}
    n = len(S)
    R["eligible"] = n
    R["settled"] = len(SETTLED)
    R["rose"] = sum(e["return_pct"] > 0 for e in SETTLED)
    R["fell"] = sum(e["return_pct"] < 0 for e in SETTLED)
    R["reaction_days"] = len({e["end_date"] for e in SETTLED})
    for s in SYSTEMS:
        g = graded(s)
        c, d = acc(g)
        R[s] = dict(right=c, wrong=d - c, called=d, accuracy=pct(c, d),
                    neutral=sum(call(e[SCORE[s]]) == "neutral" for e in scored(s)),
                    missing=sum(e[STATUS[s]] != "scored" for e in S), called_share=pct(d, n),
                    bullish=acc([x for x in g if x[1] == "bullish"]), bearish=acc([x for x in g if x[1] == "bearish"]),
                    called_rose=sum(e["return_pct"] > 0 for e, _, _ in g),
                    called_fell=sum(e["return_pct"] < 0 for e, _, _ in g),
                    score_range=(min(e[SCORE[s]] for e in scored(s)), max(e[SCORE[s]] for e in scored(s))))
        up = [x for x in g if x[0]["return_pct"] > 0]
        dn = [x for x in g if x[0]["return_pct"] < 0]
        R[s]["balanced"] = round(100 * (sum(k == "bullish" for _, k, _ in up) / len(up)
                                        + sum(k == "bearish" for _, k, _ in dn) / len(dn)) / 2, 1)
        R[s]["vs_spy"] = sum((k == "bullish") == (e["return_pct"] - e["market_return_pct"] > 0)
                             for e, k, _ in g if e["market_return_pct"] is not None)
        sec = [(e, k) for e, k, _ in g if e["sector_return_pct"] is not None]
        R[s]["vs_sector"] = (sum((k == "bullish") == (e["return_pct"] - e["sector_return_pct"] > 0) for e, k in sec), len(sec))

    R["baseline_wide"] = acc(graded("baseline", rule=wide_call))

    # Paired comparison on releases where both systems have a forecast and the outcome settled.
    pair = [e for e in SETTLED if e["agent_status"] == "scored" and e["baseline_status"] == "scored"]
    rows: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for e in pair:
        a, b = call(e["agent_score"]), call(e["baseline_score"])
        up = e["return_pct"] > 0
        ar = a != "neutral" and e["return_pct"] != 0 and (a == "bullish") == up
        br = b != "neutral" and e["return_pct"] != 0 and (b == "bullish") == up
        key = (("same" if a == b else "opposite") if a != "neutral" and b != "neutral"
               else "agent_only" if a != "neutral" else "baseline_only" if b != "neutral" else "neither")
        rows[key][0] += 1
        rows[key][1] += ar
        rows[key][2] += br
    R["paired"] = dict(events=len(pair), **dict(rows))
    R["paired_agent"] = acc(graded("agent", pair))
    no_base = [e for e in SETTLED if e["baseline_status"] != "scored"]
    R["agent_no_baseline"] = acc(graded("agent", no_base))
    R["agent_no_baseline_events"] = len([e for e in no_base if e["agent_status"] == "scored"])

    # Accuracy against coverage at fixed half-widths around 50.
    R["curve"] = {}
    for s in ("agent", "baseline"):
        pool = scored(s)
        pts = []
        for w in HALF_WIDTHS:
            called = right = 0
            for e in pool:
                x = e[SCORE[s]]
                if x == 50 or not (x >= 50 + w or x <= 50 - w) or e["return_pct"] == 0:
                    continue
                called += 1
                right += (x > 50) == (e["return_pct"] > 0)
            pts.append((w, called, right, pct(called, n), pct(right, called)))
        R["curve"][s] = dict(total=n, scored_settled=len(pool), points=pts)

    R["by_call"] = {s: {k: (sum(e["return_pct"] > 0 for e in scored(s) if call(e[SCORE[s]]) == k),
                            sum(call(e[SCORE[s]]) == k for e in scored(s)))
                        for k in ("bearish", "neutral", "bullish")} for s in ("agent", "baseline")}
    R["bands"] = {}
    for s in ("agent", "baseline"):
        R["bands"][s] = []
        for name, f in BANDS:
            rs = [e["return_pct"] for e in scored(s) if f(e[SCORE[s]])]
            R["bands"][s].append((name, len(rs), pct(sum(r > 0 for r in rs), len(rs)),
                                  round(statistics.mean(rs), 2) if rs else None, round(statistics.median(rs), 2) if rs else None))

    R["constant"] = {"all": (R["rose"], R["fell"])}
    for s in SYSTEMS:
        R["constant"][s] = (R[s]["called_rose"], R[s]["called_fell"])

    R["size"] = {s: {nm: acc([x for x in graded(s) if lo <= abs(x[0]["return_pct"]) < hi]) for nm, lo, hi in SIZES}
                 for s in ("agent", "baseline")}

    R["periods"] = []
    for nm, lo, hi in PERIODS:
        ev = [e for e in SETTLED if lo <= e["end_date"] <= hi]
        row: dict[str, Any] = dict(name=nm, events=len(ev), rose=pct(sum(e["return_pct"] > 0 for e in ev), len(ev)))
        for s in ("agent", "baseline"):
            g = graded(s, ev)
            row[s] = acc(g)
            row[s + "_bearish"] = acc([x for x in g if x[1] == "bearish"])
            row[s + "_bullish"] = acc([x for x in g if x[1] == "bullish"])
        R["periods"].append(row)

    ev = [e for e in SETTLED if e["end_date"] == "2026-11-06"]
    g = graded("agent", ev)
    R["nov6"] = dict(agent=acc(g), misses=[(e["ticker"], round(e["return_pct"], 1),
                                            e["sector_return_pct"] and round(e["sector_return_pct"], 1))
                                           for e, k, r in g if not r])

    R["ranking"] = {}
    for s in SYSTEMS:
        pr = [(e[SCORE[s]], e["return_pct"]) for e in scored(s)]
        x = [a for a, _ in pr]
        y = [b for _, b in pr]
        R["ranking"][s] = dict(n=len(pr), auc=round(_auc(pr), 3), spearman=round(_pearson(_ranks(x), _ranks(y)), 3),
                               pearson=round(_pearson(x, y), 3), ap_up=tuple(round(v, 3) for v in _ap(pr, True)),
                               ap_down=tuple(round(v, 3) for v in _ap(pr, False)))

    # Uncertainty: resample whole reaction days (stocks reacting the same day move together).
    days = sorted({e["end_date"] for e in SETTLED})
    by_day = defaultdict(list)
    for e in SETTLED:
        by_day[e["end_date"]].append(e)
    rng = random.Random(BOOTSTRAP_SEED)
    boot: dict[str, list[float]] = defaultdict(list)
    for _ in range(BOOTSTRAP_DRAWS):
        sample = [e for d in (rng.choice(days) for _ in days) for e in by_day[d]]
        vals = {}
        for s in SYSTEMS:
            c, d = acc(graded(s, sample))
            vals[s] = 100 * c / d if d else None
        for s, v in vals.items():
            boot[s].append(v)
        boot["diff"].append(vals["agent"] - vals["baseline"])
    R["ci"] = {k: _ci(v) for k, v in boot.items()}
    R["loo"] = {}
    for s in ("agent", "baseline"):
        vals = []
        for d in days:
            c, k = acc(graded(s, [e for e in SETTLED if e["end_date"] != d]))
            vals.append(100 * c / k)
        R["loo"][s] = (round(min(vals), 1), round(max(vals), 1))

    bw = [e for e in SETTLED if e["sector"] == "Financials" and "2026-10-13" <= e["end_date"] <= "2026-10-16"]
    R["bank_week"] = dict(events=len(bw), fell=sum(e["return_pct"] < 0 for e in bw))
    for s in ("agent", "baseline"):
        g = graded(s, bw)
        c, d = acc(g)
        R["bank_week"][s] = dict(called=d, right=c, wrong=d - c,
                                 neutral=sum(call(e[SCORE[s]]) == "neutral" for e in scored(s, bw)),
                                 missing=sum(e[STATUS[s]] != "scored" for e in bw),
                                 calls=[(e["ticker"], k, round(e["return_pct"], 1), r) for e, k, r in g])
    R["bank_week"]["tickers"] = sorted(e["ticker"] for e in bw)

    R["examples"] = {e["ticker"]: dict(release=e["release_date"],
                                       ret=round(e["return_pct"], 1) if e.get("return_pct") is not None else None,
                                       agent=e.get("agent_score"), baseline=e.get("baseline_score"),
                                       agent_status=e["agent_status"])
                     for e in S if e["ticker"] in EXAMPLES}

    # Which reasoning held up: bullish calls by guidance support, bearish calls by leading comparison.
    R["reasoning"] = {}
    for nm, lo, hi in (("through_nov_4", "2026-10-13", "2026-11-04"), ("nov_5_13", "2026-11-05", "2026-11-13"),
                       ("season", "2026-10-13", "2026-11-13")):
        groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for e, k, right in graded("agent", [x for x in SETTLED if lo <= x["end_date"] <= hi]):
            g = e["reasoning_group"]
            allowed = {"bullish_positive_guidance", "bullish_without_support", "bearish_adverse",
                       "bearish_in_line", "bearish_no_central", "bearish_tied", "bearish_unlabelled"}
            if g not in allowed or not g.startswith(k + "_"):
                raise ValueError(f"missing or incompatible reasoning group for {e['event']}")
            groups[g][0] += right
            groups[g][1] += 1
        R["reasoning"][nm] = {g: tuple(v) for g, v in sorted(groups.items())}

    # Who is in the universe, and why the agent has no forecast for some releases.
    included_below = sum(e["below_10b_on_release_day"] for e in S)
    counts: dict[str, int] = defaultdict(int)
    for u in universe:
        counts[u["eligibility"]] += 1
    R["universe"] = dict(eligible=n - included_below, below_10b_on_release_day_included=included_below,
                         below_10b_on_release_day_left_out=counts["eligible_if_forecast"] - included_below,
                         **{k.split(":", 1)[1]: v for k, v in sorted(counts.items()) if k.startswith("ineligible:")})
    reasons: dict[str, int] = defaultdict(int)
    for e in S:
        if e["agent_status"] != "scored":
            reasons[e["agent_missing_reason"] or "unknown"] += 1
    R["agent_missing_reasons"] = dict(sorted(reasons.items()))
    R["missing_both"] = sum(e["agent_status"] != "scored" and e["baseline_status"] != "scored" for e in S)
    return json.loads(json.dumps(R))


def _ranks(v: list[float]) -> list[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def _pearson(x: list[float], y: list[float]) -> float:
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return num / (sum((a - mx) ** 2 for a in x) ** 0.5 * sum((b - my) ** 2 for b in y) ** 0.5)


def _auc(pairs: list[tuple[float, float]]) -> float:
    pos = [s for s, r in pairs if r > 0]
    neg = [s for s, r in pairs if r < 0]
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def _ap(pairs: list[tuple[float, float]], positive: bool) -> tuple[float, float]:
    """Non-interpolated average precision at distinct score thresholds, and the base rate.

    Equal scores enter together. Their input order cannot change the result. Exact-zero
    returns are ungraded ties, consistent with the directional accuracy and ROC calculation.
    """
    xs = sorted((p for p in pairs if p[1] != 0), key=lambda t: t[0], reverse=positive)
    npos = sum((r > 0) == positive for _, r in xs)
    if not xs or not npos:
        raise ValueError("average precision needs at least one outcome in the target class")
    hits = seen = 0
    total = 0.0
    for _, group in groupby(xs, key=lambda t: t[0]):
        rows = list(group)
        added_hits = sum((r > 0) == positive for _, r in rows)
        hits += added_hits
        seen += len(rows)
        total += added_hits * hits / seen
    return total / npos, npos / len(xs)


def _ci(v: list[float]) -> tuple[float, float]:
    s = sorted(v)
    return round(s[int(0.025 * len(s))], 1), round(s[int(0.975 * len(s)) - 1], 1)
