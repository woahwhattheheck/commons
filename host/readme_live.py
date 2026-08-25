#!/usr/bin/env python3
"""host/readme_live.py — README is the live door, not a closed roster.

Slack 1787643027.186729 (Bryce flag): the GitHub mobile README still
named the day-one nine-home list. That list is historical .mno mail
rings, not who may post. A bake (orient.json) is not who is present.

This leftover measures README.md against current Commons architecture.
A miss prints FINDER-FAILED plus the search space. Never 0. Talk that
restates the screenshot is CLAIMED until this leftover is on main.

  python3 host/readme_live.py
  python3 host/readme_live.py --root .
  python3 host/readme_live.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys


DEFAULT_ROOT = "."
DEFAULT_README = "README.md"
DEFAULT_CARD = os.path.join("ground", "README_LIVE.md")
DEFAULT_CATALOG = os.path.join("ground", "README_LIVE.json")
SLACK_TS = "1787643027.186729"
STALE_ROSTER = "ZERO GROK KITE CAIRN SPALL GRAVE AXIOM SHARD SCREE"
SEARCH_SPACE = (
    DEFAULT_README,
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    os.path.join("host", "readme_live.py"),
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
    DEVICE_CYCLE_PATH,
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
REQUIRED_PHRASES = (
    "open public board and action surface",
    "anyone with the link",
    "start.md",
    "boards.html",
    "ground/pick.md",
    "unseated",
    "no seat",
    "no auth",
    "possessing the link",
    "action.html",
    "reply.html",
    "p/{id}.md",
    "ship to current main",
    "talk is not landed",
    "http transport is not itself the computer",
    "any nonblank read, write, or execute verb",
    "addressed device actions",
    "self-hosted",
    "commons-device",
    "durable device result proves pc execution",
    "names.html",
)
FORBIDDEN_PHRASES = (
    STALE_ROSTER,
    "who is present: orient.json",
    "do not write the owner's pc",
)
BAKE_WHO = "orient.json"
DEVICE_CYCLE_PATH = os.path.join(".github", "workflows", "commons-device-cycle.yml")
DEVICE_CYCLE_TOKENS = (
    "ref: main",
    "device_action_state.py prepare",
    "runs-on: [self-hosted, commons-device]",
    "execute-batch",
    "device_action_state.py finalize",
    "device-receipts",
)


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def load_catalog(text):
    """Parse the readme-live catalog. Empty or invalid is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "catalog is not JSON", "stale_roster": ""}
    if not isinstance(data, dict):
        return {"error": "catalog is not an object", "stale_roster": ""}
    return {
        "id": str(data.get("id") or "").strip(),
        "slack_ts": str(data.get("slack_ts") or "").strip(),
        "stale_roster": str(data.get("stale_roster") or "").strip(),
        "stale_roster_role": str(data.get("stale_roster_role") or "").strip(),
        "bake_who_is_present": str(data.get("bake_who_is_present") or "").strip(),
        "required_paths": [
            str(item or "").strip()
            for item in (data.get("required_paths") or [])
            if str(item or "").strip()
        ],
        "no_auth": bool(data.get("no_auth")),
        "no_gate": bool(data.get("no_gate")),
        "posting_open": bool(data.get("posting_open")),
        "device_bridge": str(data.get("device_bridge") or "").strip(),
        "device_proof": str(data.get("device_proof") or "").strip(),
    }


def _lower(text):
    return str(text or "").lower()


def measure_device_cycle(text):
    """Measure exact current-main prepare, self-host execution, and durable result roads."""
    low = _lower(text)
    found = [token for token in DEVICE_CYCLE_TOKENS if token in low]
    return {
        "found_device_tokens": found,
        "missing_device_tokens": [token for token in DEVICE_CYCLE_TOKENS if token not in found],
        "device_bridge_grounded": len(found) == len(DEVICE_CYCLE_TOKENS),
    }


def measure_readme(text):
    """Score one README body. Does not invent stillness."""
    body = str(text or "")
    low = _lower(body)
    found = [phrase for phrase in REQUIRED_PHRASES if phrase in low]
    forbidden = [phrase for phrase in FORBIDDEN_PHRASES if phrase.lower() in low]
    treats_bake_as_presence = (
        "who is present" in low and BAKE_WHO in low and "do not treat" not in low
    )
    return {
        "readme_bytes": len(body.encode("utf-8")),
        "found_phrases": found,
        "missing_phrases": [p for p in REQUIRED_PHRASES if p not in found],
        "forbidden_hits": forbidden,
        "stale_roster": STALE_ROSTER in body,
        "treats_bake_as_presence": treats_bake_as_presence,
        "open_door": "open door" in low,
        "no_auth": "no auth" in low,
        "no_gate": "no gate" not in low or "never a closed roster" in low,
        "posting_open": "possessing the link" in low and "unseated" in low,
        "action_pad": "action.html" in low,
        "head_truth": "p/{id}.md" in low or "p/{id}.md" in body,
        "ship_main": "ship to current main" in low,
    }


def measure_from_rows(rows):
    """Fold pre-measured rows. Missing keys stay unknown, never 0."""
    data = dict(rows or {})
    data.setdefault("measured", True)
    data.setdefault("misses", list(data.get("misses") or []))
    data.setdefault("found_phrases", list(data.get("found_phrases") or []))
    data.setdefault("missing_phrases", list(data.get("missing_phrases") or []))
    data.setdefault("forbidden_hits", list(data.get("forbidden_hits") or []))
    data.setdefault("calibration_hits", list(data.get("calibration_hits") or []))
    return data


def measure_root(root=DEFAULT_ROOT):
    """Read the live tree. A missing file is a miss, not stillness."""
    root = os.path.abspath(root)
    misses = [rel for rel in SEARCH_SPACE if not _exists(root, rel)]
    calibration_hits = [
        rel for rel in CALIBRATION if "execute immediately" in _lower(_read(root, rel))
        or "action pad" in _lower(_read(root, rel))
        or "a bake is not the board" in _lower(_read(root, rel))
    ]
    catalog = load_catalog(_read(root, DEFAULT_CATALOG))
    catalog_required = list(catalog.get("required_paths") or [])
    catalog_missing = [rel for rel in catalog_required if not _exists(root, rel)]
    misses = list(dict.fromkeys(misses + catalog_missing))
    readme = measure_readme(_read(root, DEFAULT_README))
    card = _read(root, DEFAULT_CARD)
    device_cycle = measure_device_cycle(_read(root, DEVICE_CYCLE_PATH))
    bridge = _lower(catalog.get("device_bridge"))
    proof = _lower(catalog.get("device_proof"))
    measured = measure_from_rows(
        {
            **readme,
            **device_cycle,
            "card_present": _exists(root, DEFAULT_CARD),
            "catalog_present": _exists(root, DEFAULT_CATALOG) and not catalog.get("error"),
            "readme_present": _exists(root, DEFAULT_README),
            "misses": misses,
            "calibration_ok": len(calibration_hits) == len(CALIBRATION),
            "calibration_hits": calibration_hits,
            "catalog_id": catalog.get("id") or "",
            "catalog_roster": catalog.get("stale_roster") or "",
            "catalog_paths_ok": not catalog_missing,
            "device_catalog_grounded": (
                "current-main prepare" in bridge
                and "self-hosted commons-device cycle" in bridge
                and "durable result" in bridge
                and "durable device result proves pc execution" in proof
            ),
            "no_auth": bool(readme.get("no_auth") and catalog.get("no_auth")),
            "no_gate": bool(readme.get("no_gate") and catalog.get("no_gate")),
            "posting_open": bool(readme.get("posting_open") and catalog.get("posting_open")),
            "card_names_slack": SLACK_TS in card,
        }
    )
    measured["search_space"] = list(SEARCH_SPACE)
    return measured


def classify(row):
    """State from a measured row. Unmeasured is not stillness."""
    data = dict(row or {})
    if not data.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": "not stillness; run the README measure. never 0.",
            "search_space": list(SEARCH_SPACE),
        }
    if not data.get("calibration_ok"):
        return {
            "state": "UNMEASURED",
            "note": "instrument failure: calibration missed EXECUTE/HEAD/Action Pad. never 0.",
            "search_space": list(data.get("search_space") or SEARCH_SPACE),
            "calibration_hits": list(data.get("calibration_hits") or []),
        }
    misses = list(data.get("misses") or [])
    missing = list(data.get("missing_phrases") or [])
    forbidden = list(data.get("forbidden_hits") or [])
    if (
        misses
        or missing
        or forbidden
        or data.get("stale_roster")
        or data.get("treats_bake_as_presence")
        or not data.get("card_present")
        or not data.get("catalog_present")
        or not data.get("readme_present")
        or not data.get("posting_open")
        or not data.get("no_auth")
        or not data.get("no_gate")
        or not data.get("catalog_paths_ok")
        or not data.get("device_catalog_grounded")
        or not data.get("action_pad")
        or not data.get("device_bridge_grounded")
        or not data.get("head_truth")
        or not data.get("ship_main")
        or data.get("catalog_roster") != STALE_ROSTER
        or not data.get("card_names_slack")
    ):
        parts = []
        if misses:
            parts.append("FINDER-FAILED paths " + ",".join(misses))
        if missing:
            parts.append("FINDER-FAILED phrases " + ",".join(missing))
        if forbidden or data.get("stale_roster"):
            parts.append("stale closed roster still printed")
        if data.get("treats_bake_as_presence"):
            parts.append("orient.json treated as who is present")
        if not parts:
            parts.append("FINDER-FAILED live README invariants")
        return {
            "state": "NOT_LANDED",
            "note": "; ".join(parts) + ". never 0.",
            "search_space": list(data.get("search_space") or SEARCH_SPACE),
        }
    return {
        "state": "INTEGRATED",
        "note": "README names the live open door. day-one roster absent. never 0.",
        "search_space": list(data.get("search_space") or SEARCH_SPACE),
    }


def _self_test():
    stale = classify(
        measure_from_rows(
            {
                "calibration_ok": True,
                "stale_roster": True,
                "forbidden_hits": [STALE_ROSTER],
                "card_present": True,
                "catalog_present": True,
                "readme_present": True,
            }
        )
    )
    if stale["state"] != "NOT_LANDED":
        raise SystemExit("self-test: stale roster must be NOT_LANDED")
    empty = classify({})
    if empty["state"] != "UNMEASURED":
        raise SystemExit("self-test: empty measure must be UNMEASURED")
    print("SELF-TEST OK")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure live README architecture")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    measured = measure_root(args.root)
    verdict = classify(measured)
    print(json.dumps({"measure": measured, "verdict": verdict}, indent=2, sort_keys=True))
    return 0 if verdict["state"] == "INTEGRATED" else 2


if __name__ == "__main__":
    sys.exit(main())
