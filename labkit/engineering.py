"""Small, deterministic checks illustrated by Engineering Note 1.

Inputs are synthetic observations, not live agent traces. A validator receipt is an input;
this module does not validate a real trade or decide whether an explanation is causal.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


def verdict(checks: dict[str, str]) -> str:
    if set(checks.values()) - {"pass", "fail", "unproven"}:
        raise ValueError("unknown check verdict")
    if "fail" in checks.values():
        return "fail"
    return "unproven" if not checks or "unproven" in checks.values() else "pass"


def _bool(value: Any) -> str:
    if value is None:
        return "unproven"
    if not isinstance(value, bool):
        raise ValueError("a boolean observation must be true, false or null")
    return "pass" if value else "fail"


def _clock(value: str) -> datetime:
    clock = datetime.fromisoformat(value)
    if clock.tzinfo is None:
        raise ValueError("evidence clocks must include a UTC offset")
    return clock


def evaluate(case: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    kind = case["kind"]
    checks: dict[str, str] = {}
    if kind == "evidence_clock":
        saved, available = case.get("saved_at"), case.get("source_available_at")
        checks["evidence_available_when_saved"] = (
            _bool(_clock(available) <= _clock(saved)) if available and saved else "unproven")
    elif kind == "disclosure":
        claim, key = case.get("claim_disclosed"), case.get("key_disclosed")
        _bool(claim)
        _bool(key)
        checks["disclosure_matches_key"] = (
            _bool(claim == key) if claim is not None and key is not None else "unproven")
    elif kind == "ticket":
        intent, ticket = case["intent"], case.get("ticket")
        if intent not in ("trade", "explain"):
            raise ValueError("ticket intent must be trade or explain")
        checks["ticket_required_only_for_trade"] = _bool(
            ticket is not None if intent == "trade" else ticket is None)
        if ticket is not None:
            checks["ticket_has_validation_receipt"] = _bool(ticket.get("validated"))
            checks["ticket_states_worst_case"] = _bool(ticket.get("worst_case_stated"))
        if case.get("profile"):
            if case["profile"] != profile["id"]:
                raise ValueError("unknown customer profile")
            # Customer checks are additive: they never replace the house checks above.
            sources = case.get("sources")
            if sources is not None and (not isinstance(sources, list) or any(not isinstance(s, str) for s in sources)):
                raise ValueError("sources must be a list of identifiers or null")
            checks["approved_sources"] = (
                _bool(bool(sources) and set(sources) <= set(profile["approved_sources"]))
                if sources is not None else "unproven")
            disclaimer = case.get("disclaimer_id")
            checks["required_disclaimer"] = (
                _bool(disclaimer == profile["disclaimer_id"]) if disclaimer is not None else "unproven")
            elapsed = case.get("elapsed_ms")
            if elapsed is not None and (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
                                        or not math.isfinite(elapsed) or elapsed < 0):
                raise ValueError("elapsed_ms must be a finite, nonnegative number or null")
            checks["within_time_limit"] = (
                _bool(elapsed <= profile["max_elapsed_ms"]) if elapsed is not None else "unproven")
            if ticket is not None:
                product = ticket.get("product")
                checks["permitted_product"] = (
                    _bool(product in profile["allowed_products"]) if product is not None else "unproven")
    else:
        raise ValueError(f"unknown engineering example kind: {kind}")
    return {"verdict": verdict(checks), "checks": checks}


def load_results(directory: Path) -> dict[str, dict[str, Any]]:
    cases = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
    profile = json.loads((directory / "profile.json").read_text(encoding="utf-8"))
    results = {}
    for case in cases:
        if case["id"] in results:
            raise ValueError(f"duplicate case: {case['id']}")
        results[case["id"]] = evaluate(case, profile)
    if not results:
        raise ValueError("engineering example suite is empty")
    return results
