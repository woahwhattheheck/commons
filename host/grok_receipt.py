#!/usr/bin/env python3
"""host/grok_receipt.py — Grok envelopes stay CANDIDATE; catalogs must match HEAD.

Slack 1787649265.015869 (DEMON HEAVY RECEIPT RECONCILIATION):
every Grok envelope is CANDIDATE. Only its single final fenced JSON
is authoritative. Scratch/thought text is excluded. Current-main
bytes + non-Grok tests decide. Do not blindly act on ARCHITECT
rank 1. SKEPTIC-proven catalog edges are the land.

Unique leftover: Grok receipt normalizer + current catalog delta
reconciliation/land + H-009 exact plan. Do not remint H-002,
HEAVY_LANES, SUPERGROK_HEAVY, PIXEL_HEARTBEAT leftover, STRANDED_MAP
leftover, BUILD_SWEEP_ACT leftover, HUMAN_OUTCOMES, or JOJO
LDA/Subzero lanes. Device false-zero patches wait for H-009.
Peers announce collision first. titan: NOT_WRITTEN. No auth.
No gate. Miss is FINDER-FAILED / FINDER-UNVERIFIED. Never 0.

  python3 host/grok_receipt.py
  python3 host/grok_receipt.py --root .
  python3 host/grok_receipt.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "GROK_RECEIPT.json")
DEFAULT_CARD = os.path.join("ground", "GROK_RECEIPT.md")
H009_CARD = os.path.join("ground", "H009.md")
H009_CATALOG = os.path.join("ground", "H009.json")
SLACK_TS = "1787649265.015869"
FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
SEARCH_SPACE = (
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    os.path.join("host", "grok_receipt.py"),
    H009_CARD,
    H009_CATALOG,
    os.path.join("ground", "PIXEL_HEARTBEAT.json"),
    os.path.join("ground", "OWNER_MACHINE_BUILD_SWEEP.md"),
    os.path.join("ground", "STRANDED_MAP.json"),
    os.path.join("ground", "WORKING_BUILDS.json"),
    os.path.join("ground", "GEMMA_TOKENIZER_MAP.md"),
    os.path.join("ground", "GEMMA_INGRESS.md"),
    os.path.join("pixels", "RIVET.json"),
    os.path.join("pixels", "index.json"),
    "pixel.js",
    "swarm.js",
    os.path.join(".github", "workflows", "lda-android.yml"),
    os.path.join("ground", "MCP_INVENTORY.json"),
    os.path.join("infra", "host", "muhl_dump_litertlm.py"),
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
ALREADY_LANDED = (
    os.path.join("ground", "H002.md"),
    os.path.join("ground", "HEAVY_LANES.md"),
    os.path.join("ground", "SUPERGROK_HEAVY.md"),
    os.path.join("ground", "PIXEL_HEARTBEAT.md"),
    os.path.join("ground", "STRANDED_MAP.md"),
    os.path.join("ground", "BUILD_SWEEP_ACT.md"),
    os.path.join("ground", "HUMAN_OUTCOMES.md"),
)
REQUIRED_PHRASES = (
    "grok receipt leftover",
    "do not blindly act on architect rank 1",
    "last fenced json",
    "every grok envelope is candidate",
    "h-009 exact plan",
    "known-present",
    "known-missing",
    "never 0",
    "finder-failed",
    "finder-unverified",
    "open door",
    "no auth",
    "no gate",
    "talk is not a land",
)
CANDIDATE_RECEIPTS = (
    "H-001 ARCHITECT",
    "SKEPTIC",
    "H-004 FALSE-ZERO",
    "H-003 integration",
    "H-005 frontier",
    "H-002 contamination",
)
H009_BUGS = (
    {
        "id": "device_ls_tree_collapse",
        "path": "host/device_path_census.py",
        "fn": "ls_tree",
        "defect": "missing-dir and failed git ls-tree return [] and collapse counts to 0",
        "required_tests": (
            "known-present fixture must recover at least one path",
            "known-missing ref / missing dir must be FINDER-FAILED, never 0",
        ),
    },
    {
        "id": "device_missing_dir_zero",
        "path": "host/device_churn.py",
        "fn": "listing",
        "defect": "missing-dir listing collapses to 0",
        "required_tests": (
            "known-present results dir is counted",
            "missing dir is FINDER-FAILED / UNMEASURED, never 0",
        ),
    },
    {
        "id": "wake_missing_dir_empty",
        "path": "host/mcp_wake.py",
        "fn": "_wake_state / _wake_job_rows",
        "defect": "missing wake_jobs/ returns [] and classifies EMPTY",
        "required_tests": (
            "known-present DONE job is VERIFIED",
            "missing dir is FINDER-FAILED / UNMEASURED, never EMPTY-as-success",
        ),
    },
    {
        "id": "fleet_listing_zero",
        "path": "host/fleet_ids.py",
        "fn": "measure_paths listing",
        "defect": "listing OSError becomes [] and prints 0/N",
        "required_tests": (
            "known-present p/{id}.md is counted",
            "listing failure is FINDER-FAILED, never 0/N",
        ),
    },
    {
        "id": "taking_listing_zero",
        "path": "host/taking_trace.py",
        "fn": "measure_paths listing",
        "defect": "listing OSError becomes [] and prints 0/N",
        "required_tests": (
            "known-present taking id is counted",
            "listing failure is FINDER-FAILED, never 0/N",
        ),
    },
    {
        "id": "verify_listing_zero",
        "path": "host/verify_cite.py",
        "fn": "listing",
        "defect": "listing failures become 0/N",
        "required_tests": (
            "known-present cite is counted",
            "listing failure is FINDER-FAILED, never 0/N",
        ),
    },
    {
        "id": "finder_zero_self_audit",
        "path": "host/finder_zero.py",
        "fn": "measure_tree",
        "defect": "audits host/finder_zero.py rather than host/*.py",
        "required_tests": (
            "known-present bare-find fixture under host/ must be named",
            "known-missing miss-branch under host/ must be FINDER UNVERIFIED",
        ),
    },
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
    """Parse the grok-receipt catalog. Invalid is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "catalog is not JSON", "receipts": []}
    if not isinstance(data, dict):
        return {"error": "catalog is not an object", "receipts": []}
    receipts = []
    for item in data.get("receipts") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("id") or item.get("name") or "").strip()
        if name:
            receipts.append(
                {
                    "id": name,
                    "status": str(item.get("status") or "CANDIDATE").strip()
                    or "CANDIDATE",
                    "tokens": item.get("tokens"),
                }
            )
    return {
        "slack_ts": str(data.get("slack_ts") or "").strip(),
        "titan": str(data.get("titan") or "NOT_WRITTEN").strip() or "NOT_WRITTEN",
        "posting": str(data.get("posting") or "").strip(),
        "no_auth": bool(data.get("no_auth", True)),
        "no_gate": bool(data.get("no_gate", True)),
        "architect_rank_1": str(data.get("architect_rank_1") or "").strip(),
        "receipts": receipts,
        "error": "",
    }


def normalize_envelope(text):
    """Last fenced JSON is authoritative. Scratch/thought is excluded.

    Every Grok envelope is CANDIDATE until current-main bytes + non-Grok
    tests decide. Missing fence is FINDER-FAILED, never a silent parse.
    """
    body = str(text or "")
    fences = list(FENCE_RE.finditer(body))
    if not fences:
        return {
            "status": "CANDIDATE",
            "authoritative": None,
            "error": "no fenced JSON. FINDER-FAILED, never 0.",
            "excluded": "scratch/thought/unfenced prose",
        }
    raw = fences[-1].group(1).strip()
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {
            "status": "CANDIDATE",
            "authoritative": None,
            "error": "last fence is not JSON. FINDER-FAILED, never 0.",
            "excluded": "scratch/thought plus earlier fences",
        }
    return {
        "status": "CANDIDATE",
        "authoritative": parsed,
        "error": "",
        "excluded": "scratch/thought plus earlier fences",
    }


def measure_from_rows(facts):
    """Classify measured file/phrase facts. Missing calibration is UNMEASURED."""
    facts = facts or {}
    return {
        "measured": True,
        "card_present": bool(facts.get("card_present")),
        "catalog_present": bool(facts.get("catalog_present")),
        "h009_present": bool(facts.get("h009_present")),
        "pixel_js_consumes": bool(facts.get("pixel_js_consumes")),
        "swarm_js_consumes": bool(facts.get("swarm_js_consumes")),
        "rivet_listed": bool(facts.get("rivet_listed")),
        "rivet_file": bool(facts.get("rivet_file")),
        "emitter_landed_named": bool(facts.get("emitter_landed_named")),
        "stranded_names_lda_android": bool(facts.get("stranded_names_lda_android")),
        "stranded_names_inventory": bool(facts.get("stranded_names_inventory")),
        "gemma_path_current": bool(facts.get("gemma_path_current")),
        "keyb_stale_field": bool(facts.get("keyb_stale_field")),
        "assemble_hides_fail": bool(facts.get("assemble_hides_fail")),
        "dump_impl_present": bool(facts.get("dump_impl_present")),
        "dump_stale_absent": bool(facts.get("dump_stale_absent")),
        "architect_rank_1_refused": bool(facts.get("architect_rank_1_refused")),
        "receipts_candidate": bool(facts.get("receipts_candidate")),
        "landed_present": list(facts.get("landed_present") or []),
        "landed_missing": list(facts.get("landed_missing") or []),
        "found_phrases": list(facts.get("found_phrases") or []),
        "posting_open": bool(facts.get("posting_open")),
        "no_auth": bool(facts.get("no_auth")),
        "no_gate": bool(facts.get("no_gate")),
        "calibration_ok": bool(facts.get("calibration_ok")),
        "calibration_hits": list(facts.get("calibration_hits") or []),
        "search_space": list(facts.get("search_space") or SEARCH_SPACE),
        "misses": list(facts.get("misses") or []),
        "titan": str(facts.get("titan") or "NOT_WRITTEN"),
        "h009_bugs": list(facts.get("h009_bugs") or []),
    }


def classify(row):
    """Turn a measured leftover census into a desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "grok-receipt leftover not read. Absence was not stillness. "
                "Talk is not a land."
            ),
        }
    if row.get("calibration_ok") is False:
        return {
            "state": "UNMEASURED",
            "note": (
                "known-present calibration failed: "
                + ", ".join(row.get("calibration_hits") or [])
                + ". Search-zero testing is instrument failure, not absence proof. "
                "FINDER-FAILED, never 0."
            ),
        }
    misses = list(row.get("misses") or [])
    landed_missing = list(row.get("landed_missing") or [])
    if (
        not row.get("card_present")
        or not row.get("catalog_present")
        or not row.get("h009_present")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/catalog/H-009"])
                + ". HEAVY RECEIPT RECONCILIATION / catalog-delta talk "
                "is CLAIMED until the leftover ships. FINDER-FAILED, never 0."
            ),
        }
    if landed_missing:
        return {
            "state": "NOT_LANDED",
            "note": (
                "named already-landed leftover(s) missing: "
                + ", ".join(landed_missing)
                + ". Do not remint. FINDER-FAILED, never 0."
            ),
        }
    if row.get("swarm_js_consumes") or not row.get("pixel_js_consumes"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "ARCHITECT rank 1 edge is stale. swarm.js does not consume "
                "pixels/*.json; pixel.js does. Do not blindly act on ARCHITECT "
                "rank 1. FINDER-FAILED, never 0."
            ),
        }
    needed = [phrase for phrase in REQUIRED_PHRASES if phrase not in (row.get("found_phrases") or [])]
    deltas = [
        name
        for name, ok in (
            ("rivet_listed", row.get("rivet_listed")),
            ("rivet_file", row.get("rivet_file")),
            ("emitter_landed_named", row.get("emitter_landed_named")),
            ("stranded_names_lda_android", row.get("stranded_names_lda_android")),
            ("stranded_names_inventory", row.get("stranded_names_inventory")),
            ("gemma_path_current", row.get("gemma_path_current")),
            ("keyb_stale_field", row.get("keyb_stale_field")),
            ("assemble_hides_fail", row.get("assemble_hides_fail")),
            ("dump_impl_present", row.get("dump_impl_present")),
            ("dump_stale_absent", row.get("dump_stale_absent")),
            ("architect_rank_1_refused", row.get("architect_rank_1_refused")),
            ("receipts_candidate", row.get("receipts_candidate")),
        )
        if not ok
    ]
    if (
        needed
        or deltas
        or not row.get("posting_open")
        or not row.get("no_auth")
        or not row.get("no_gate")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "leftover present but incomplete. Missing phrases: "
                + ", ".join(needed)
                + ". Unreconciled catalog deltas: "
                + ", ".join(deltas)
                + ". Open door + no auth + no gate required. Talk is CLAIMED. "
                "FINDER-FAILED, never 0."
            ),
        }
    if len(row.get("h009_bugs") or []) < len(H009_BUGS):
        return {
            "state": "NOT_LANDED",
            "note": (
                "H-009 exact plan missing required bugs. Peers must not "
                "patch device false-zero until the plan lands. "
                "FINDER-FAILED, never 0."
            ),
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "Grok-receipt leftover is on this tree. Last fenced JSON is "
            "authoritative. Catalog deltas match current-main bytes. "
            "H-009 exact plan is landed. A Slack receipt is still not the file."
        ),
    }


def _pixel_catalog_lists_rivet(text):
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    names = []
    for key in ("files", "index"):
        for item in data.get(key) or []:
            names.append(str(item or "").strip())
    return "RIVET.json" in names


def _keyb_stale_field_ok(text):
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    for item in data.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") != "keyb":
            continue
        stale = str(item.get("stale_container_sha256") or "").strip()
        live = str(item.get("container_sha256") or "").strip()
        state = str(item.get("hash_state") or "").upper()
        return bool(stale) and not live and state == "STALE"
    return False


def measure_root(root):
    root = os.path.abspath(root)
    misses = []
    blobs = []
    for rel in SEARCH_SPACE:
        text = _read(root, rel)
        if not text and rel not in (
            os.path.join("host", "muhl_dump_litertlm.py"),
        ):
            misses.append(rel)
        else:
            blobs.append(text)
    hay = "\n".join(blobs).lower()
    found = [phrase for phrase in REQUIRED_PHRASES if phrase in hay]
    landed_present = [rel for rel in ALREADY_LANDED if _exists(root, rel)]
    landed_missing = [rel for rel in ALREADY_LANDED if not _exists(root, rel)]
    catalog = load_catalog(_read(root, DEFAULT_CATALOG))
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    calibration_ok = len(calibration_hits) == len(CALIBRATION)
    if not calibration_ok:
        for rel in CALIBRATION:
            if rel not in calibration_hits and rel not in misses:
                misses.append("calibration:" + rel)
    pixel_js = _read(root, "pixel.js")
    swarm_js = _read(root, "swarm.js")
    pixel_hb = _read(root, os.path.join("ground", "PIXEL_HEARTBEAT.json"))
    sweep = _read(root, os.path.join("ground", "OWNER_MACHINE_BUILD_SWEEP.md"))
    stranded = _read(root, os.path.join("ground", "STRANDED_MAP.json"))
    gemma = (
        _read(root, os.path.join("ground", "GEMMA_TOKENIZER_MAP.md"))
        + "\n"
        + _read(root, os.path.join("ground", "GEMMA_INGRESS.md"))
    )
    working = _read(root, os.path.join("ground", "WORKING_BUILDS.json"))
    android = _read(root, os.path.join(".github", "workflows", "lda-android.yml"))
    h009 = _read(root, H009_CARD) + "\n" + _read(root, H009_CATALOG)
    receipts = catalog.get("receipts") or []
    receipt_ids = " ".join(item.get("id") or "" for item in receipts)
    receipts_candidate = all(
        name.lower() in receipt_ids.lower() for name in CANDIDATE_RECEIPTS
    ) and all(
        str(item.get("status") or "").upper() == "CANDIDATE" for item in receipts
    )
    h009_bugs = []
    for bug in H009_BUGS:
        blob = h009.lower()
        if bug["id"].lower() in blob and str(bug["path"]).lower() in blob:
            h009_bugs.append(bug["id"])
    posting_open = (
        catalog.get("posting") == "OPEN"
        and "open door" in hay
        and "unseated" in hay
    )
    facts = {
        "card_present": _exists(root, DEFAULT_CARD),
        "catalog_present": _exists(root, DEFAULT_CATALOG) and not catalog.get("error"),
        "h009_present": _exists(root, H009_CARD) and _exists(root, H009_CATALOG),
        "pixel_js_consumes": "pixels/" in pixel_js,
        "swarm_js_consumes": "pixels/" in swarm_js,
        "rivet_listed": _pixel_catalog_lists_rivet(pixel_hb),
        "rivet_file": _exists(root, os.path.join("pixels", "RIVET.json")),
        "emitter_landed_named": (
            "add a current pixel heartbeat emitter" not in sweep.lower()
            and "emitter landed" in sweep.lower()
        ),
        "stranded_names_lda_android": "lda-android.yml" in stranded,
        "stranded_names_inventory": (
            "MCP_INVENTORY.json" in stranded
            and "absent" not in stranded.lower().split("mcp")[-1][:200]
        )
        or ("inventory is present" in stranded.lower())
        or ("canonical inventory exists" in stranded.lower()),
        "gemma_path_current": (
            "infra/host/muhl_dump_litertlm.py" in gemma
            and "python host/muhl_dump_litertlm.py" not in gemma
        ),
        "keyb_stale_field": _keyb_stale_field_ok(working),
        "assemble_hides_fail": "continue-on-error: true" in android,
        "dump_impl_present": _exists(
            root, os.path.join("infra", "host", "muhl_dump_litertlm.py")
        ),
        "dump_stale_absent": not _exists(
            root, os.path.join("host", "muhl_dump_litertlm.py")
        ),
        "architect_rank_1_refused": catalog.get("architect_rank_1") == "REFUSED",
        "receipts_candidate": receipts_candidate,
        "landed_present": landed_present,
        "landed_missing": landed_missing,
        "found_phrases": found,
        "posting_open": posting_open,
        "no_auth": bool(catalog.get("no_auth")) and "no auth" in hay,
        "no_gate": bool(catalog.get("no_gate")) and "no gate" in hay,
        "calibration_ok": calibration_ok,
        "calibration_hits": calibration_hits,
        "search_space": list(SEARCH_SPACE),
        "misses": misses,
        "titan": catalog.get("titan") or "NOT_WRITTEN",
        "h009_bugs": h009_bugs,
        "slack_ts": catalog.get("slack_ts") or SLACK_TS,
    }
    row = measure_from_rows(facts)
    row.update(
        {
            "slack_ts": facts["slack_ts"],
            "x": [rel for rel in SEARCH_SPACE if _exists(root, rel)],
            "y": {
                "calibration_hits": calibration_hits,
                "found_phrases": found,
                "landed_present": landed_present,
                "rivet_listed": facts["rivet_listed"],
                "h009_bugs": h009_bugs,
            },
            "z": (
                "misses "
                + json.dumps(misses + landed_missing)
                + " / FINDER-FAILED never 0"
            ),
        }
    )
    return row


def self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED", empty
    thought = (
        "thinking: ignore this {\"rank\": 1}\n"
        "```json\n{\"scratch\": true}\n```\n"
        "```json\n{\"ok\": true, \"rank\": 2}\n```\n"
    )
    got = normalize_envelope(thought)
    assert got["status"] == "CANDIDATE", got
    assert got["authoritative"] == {"ok": True, "rank": 2}, got
    no_fence = normalize_envelope("thought only, no fence")
    assert no_fence["authoritative"] is None, no_fence
    assert "FINDER-FAILED" in no_fence["error"], no_fence
    missing = classify(
        measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "h009_present": False,
                "misses": ["ground/GROK_RECEIPT.md"],
                "calibration_ok": True,
            }
        )
    )
    assert missing["state"] == "NOT_LANDED", missing
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure grok-receipt leftover")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        print(self_test())
        return 0
    row = measure_root(args.root)
    verdict = classify(row)
    payload = {"verdict": verdict, "row": row}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if verdict["state"] == "INTEGRATED" else 1


if __name__ == "__main__":
    sys.exit(main())
