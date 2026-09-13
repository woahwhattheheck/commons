"""Authority-hardening facade for the opportunity qualification core.

The core remains a stable deterministic compiler. This facade tightens two
negative-authority rules: unverified buyer sources cannot force an expired
NO_BID or make teaming impossible.
"""
from __future__ import annotations

import engine_core as _core
from engine_core import *  # noqa: F401,F403 - preserve the public v1 surface

_original_compile = _core.compile_qualification


def _evaluate_team(requirements, sources, teaming, teaming_source_id):
    if teaming == "UNKNOWN" or not _core._buyer_official(teaming_source_id, sources):
        return False, True, ["TEAMING_NOT_OFFICIALLY_EVIDENCED"]
    if teaming == "PROHIBITED":
        return False, False, ["TEAMING_PROHIBITED"]
    return _core._evaluate_team_official_allowed(requirements, sources)


def _evaluate_team_official_allowed(requirements, sources):
    """Evaluate requirements after buyer-official teaming permission is known."""
    ready = True
    possible = True
    reasons = []
    for req in requirements:
        if not req["mandatory"]:
            continue
        prefix = req["gate_id"]
        if not _core._buyer_official(req["buyer_source_id"], sources):
            ready = False
            reasons.append(f"{prefix}:MANDATORY_SOURCE_NOT_OFFICIAL")
            continue

        route = req["route"]
        prime_state = req["prime_state"]
        team_state = req["team_state"]
        cure = req["cure"]

        if route == "PRIME":
            if prime_state == "PASS":
                continue
            if cure == "PARTNER" and team_state == "PASS":
                continue
            ready = False
            if prime_state == "FAIL" and cure == "NONE":
                possible = False
                reasons.append(f"{prefix}:NONCURABLE_PRIME_FAILURE")
            elif cure == "PARTNER" and team_state == "FAIL":
                possible = False
                reasons.append(f"{prefix}:PARTNER_CURE_FAILED")
            else:
                reasons.append(f"{prefix}:TEAM_ROUTE_MISSING_CURE")
            continue

        if route == "TEAM":
            if team_state == "PASS":
                continue
            ready = False
            if team_state == "FAIL":
                possible = False
                reasons.append(f"{prefix}:TEAM_FAILED")
            else:
                reasons.append(f"{prefix}:TEAM_MISSING")
            continue

        side_fail = False
        if prime_state != "PASS":
            ready = False
            side_fail = side_fail or prime_state == "FAIL"
            reasons.append(f"{prefix}:PRIME_{'FAILED' if prime_state == 'FAIL' else 'MISSING'}")
        if team_state != "PASS":
            ready = False
            side_fail = side_fail or team_state == "FAIL"
            reasons.append(f"{prefix}:TEAM_{'FAILED' if team_state == 'FAIL' else 'MISSING'}")
        if side_fail:
            possible = False
    return ready, possible, sorted(set(reasons))


# Keep the core compiler's dynamic lookup on the hardened team evaluator.
_core._evaluate_team_official_allowed = _evaluate_team_official_allowed
_core._evaluate_team = _evaluate_team


def compile_qualification(packet, *, trusted_as_of):
    receipt = _original_compile(packet, trusted_as_of=trusted_as_of)
    package = receipt["package"]

    # An expired timestamp has negative commercial authority only if both the
    # controlling package and the deadline source are buyer-official.
    if package["proposal_expired"] and (
        not package["controlling_source_official"]
        or not package["proposal_deadline_source_official"]
    ):
        reasons = []
        if not package["controlling_source_official"]:
            reasons.append("CONTROLLING_PACKAGE_NOT_OFFICIALLY_EVIDENCED")
        if not package["proposal_deadline_source_official"]:
            reasons.append("PROPOSAL_DEADLINE_NOT_OFFICIALLY_EVIDENCED")
        if not package["question_deadline_source_official"]:
            reasons.append("QUESTION_DEADLINE_SOURCE_NOT_OFFICIAL")
        receipt["disposition"] = HOLD
        receipt["reasons"] = sorted(reasons)
        receipt.pop("receipt_digest", None)
        receipt["receipt_digest"] = _core.digest(receipt)
    return receipt


# Core CLI resolves this name dynamically; patch it so `python engine.py` is safe.
_core.compile_qualification = compile_qualification


if __name__ == "__main__":
    raise SystemExit(_core._cli())
