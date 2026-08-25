#!/usr/bin/env python3
"""host/subzero_explorer.py — JOJO inventory talk is not a land.

Slack 1787646413.997539 (JOJO TECHNICAL_HANDOFF
jojo-model-work-profitability-bridge-20260825-01): Subzero /
custom-model / Muhlnickel training inventory for DEMON panels.

PANEL 1/3 and buyers 2/3 leftovers are already on main. Do not
remint them. Unique leftover: a read-only Artifact Explorer plus
a hash-verified validation packet with explicit STRUCTURAL_ONLY
labels. Git copies do not run. This leftover does not evaluate
organs. It does not sell host training or live Titan mutation.
LDA subagent execution stays BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT.
Do not copy private LocalDeviceAgent source.

Miss is FINDER-FAILED / FINDER-UNVERIFIED. Never 0.
Open door. No auth. No gate. titan NOT_WRITTEN.

  python3 host/subzero_explorer.py
  python3 host/subzero_explorer.py --root .
  python3 host/subzero_explorer.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "SUBZERO_EXPLORER.json")
DEFAULT_CARD = os.path.join("ground", "SUBZERO_EXPLORER.md")
DEFAULT_DOOR = "subzero.html"
PACKET = os.path.join("excerpts", "20260823", "titan_move_packet.json")
EXCERPT_DIR = os.path.join("excerpts", "20260823")
ARCH = os.path.join("muhl", "desktop", "MUHL_SUBZERO_ARCHETYPES")
SLACK_TS = "1787646413.997539"
HANDOFF_ID = "jojo-model-work-profitability-bridge-20260825-01"
LDA_SHA = "fb0b0b2f59f8ca81741371b6ddd8036b164e77e8"
LDA_BLOCK = "BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT"
EXPECTED_EXCERPTS = 31
SEARCH_SPACE = (
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    os.path.join("host", "subzero_explorer.py"),
    DEFAULT_DOOR,
    PACKET,
    EXCERPT_DIR,
    ARCH,
    os.path.join("ground", "SUBZERO_TECH.md"),
    os.path.join("ground", "SUBZERO_BUYERS.md"),
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
)
CALIBRATION = (
    os.path.join("ground", "EXECUTE.md"),
    os.path.join("ground", "HEAD.md"),
    os.path.join("p", "bryce-action-pad-open-door-directive-20260822-01.md"),
    os.path.join("excerpts", "20260823", "muhl_grbn.mno"),
)
ALREADY_LANDED = (
    os.path.join("ground", "SUBZERO_TECH.md"),
    os.path.join("host", "subzero_tech.py"),
    os.path.join("ground", "SUBZERO_BUYERS.md"),
    os.path.join("host", "subzero_buyers.py"),
    os.path.join("p", "demon-redteam-subzero-tech-ip-20260825-04.md"),
    os.path.join("p", "grok-subzero-buyers-panel-20260825-01.md"),
)
REQUIRED_PHRASES = (
    "subzero artifact explorer",
    "structural_only",
    "blocked_on_published_wide_receiver_result",
    "host training",
    "not_sold",
    "never 0",
    "finder-failed",
    "finder-unverified",
    "open door",
    "no auth",
    "no gate",
    "talk is not a land",
    "do not remint",
    "1787646413.997539",
)


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _read_bytes(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return b""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def _isdir(root, rel):
    return os.path.isdir(os.path.join(root, rel))


def load_catalog(text):
    """Parse the explorer catalog. Invalid is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "catalog is not JSON", "rows": []}
    if not isinstance(data, dict):
        return {"error": "catalog is not an object", "rows": []}
    rows = []
    for item in data.get("rows") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "path": str(item.get("path") or "").strip(),
                "sha256": str(item.get("sha256") or "").strip().lower(),
                "label": str(item.get("label") or "").strip().upper(),
                "runtime_measured": bool(item.get("runtime_measured")),
            }
        )
    lda = data.get("lda_protocol") or {}
    if not isinstance(lda, dict):
        lda = {}
    archetypes = data.get("archetypes") or {}
    if not isinstance(archetypes, dict):
        archetypes = {}
    return {
        "slack_ts": str(data.get("slack_ts") or "").strip() or SLACK_TS,
        "handoff_id": str(data.get("handoff_id") or "").strip() or HANDOFF_ID,
        "titan": str(data.get("titan") or "NOT_WRITTEN").strip().upper() or "NOT_WRITTEN",
        "label": str(data.get("label") or "").strip().upper(),
        "host_training": str(data.get("host_training") or "").strip().upper(),
        "titan_mutation": str(data.get("titan_mutation") or "").strip().upper(),
        "lda_state": str(lda.get("state") or "").strip().upper(),
        "lda_sha": str(lda.get("sha") or "").strip().lower(),
        "copy_private_lda": bool(lda.get("copy_private_lda_source")),
        "expected_excerpts": int(data.get("expected_excerpts") or 0),
        "archetypes": {
            "fabricators": int(archetypes.get("fabricators") or 0),
            "tests": int(archetypes.get("tests") or 0),
            "docs": int(archetypes.get("docs") or 0),
            "html": int(archetypes.get("html") or 0),
            "other_py": int(archetypes.get("other_py") or 0),
        },
        "posting": str(data.get("posting") or "").strip(),
        "no_auth": bool(data.get("no_auth", True)),
        "no_gate": bool(data.get("no_gate", True)),
        "rows": rows,
        "error": "",
    }


def parse_excerpt(blob):
    """Read magic + LE header. Short or empty is FINDER-FAILED."""
    if len(blob) < 28:
        return {"ok": False, "reason": "header too short"}
    magic = blob[:8].decode("ascii", "replace")
    n_gate, n_wires, n_in, n_out, depth = struct.unpack_from("<IIIII", blob, 8)
    return {
        "ok": True,
        "magic": magic,
        "n_gate": n_gate,
        "n_wires": n_wires,
        "n_in": n_in,
        "n_out": n_out,
        "depth": depth,
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def count_archetypes(root):
    """Count checked-in archetype tree files. Absence is FINDER-FAILED."""
    base = os.path.join(root, ARCH)
    counts = {"fabricators": 0, "tests": 0, "docs": 0, "html": 0, "other_py": 0, "present": False}
    if not os.path.isdir(base):
        return counts
    counts["present"] = True
    for dirpath, _, files in os.walk(base):
        for name in files:
            if name.endswith(".py"):
                if name.startswith("muhl_fab_"):
                    counts["fabricators"] += 1
                elif name.startswith("test_"):
                    counts["tests"] += 1
                else:
                    counts["other_py"] += 1
            elif name.endswith((".md", ".txt")):
                counts["docs"] += 1
            elif name.endswith(".html"):
                counts["html"] += 1
    return counts


def measure_excerpts(root):
    """Hash every public excerpt against the MOVE packet. Does not evaluate."""
    packet_text = _read(root, PACKET)
    try:
        packet = json.loads(packet_text or "{}")
    except ValueError:
        packet = {}
    organs = packet.get("organs") if isinstance(packet, dict) else []
    by_container = {}
    for item in organs or []:
        if isinstance(item, dict) and item.get("container"):
            by_container[str(item.get("container"))] = item
    rows = []
    exdir = os.path.join(root, EXCERPT_DIR)
    names = []
    if os.path.isdir(exdir):
        names = sorted(name for name in os.listdir(exdir) if name.endswith(".mno"))
    for name in names:
        rel = os.path.join(EXCERPT_DIR, name)
        parsed = parse_excerpt(_read_bytes(root, rel))
        exp = by_container.get(name) or {}
        expected_sha = str(exp.get("sha256") or "").strip().lower()
        sha = str(parsed.get("sha256") or "")
        rows.append(
            {
                "name": str(exp.get("name") or name[:-4]),
                "path": rel.replace("\\", "/"),
                "bytes": parsed.get("bytes") or 0,
                "magic": parsed.get("magic") or "",
                "n_gate": parsed.get("n_gate"),
                "sha256": sha,
                "packet_sha256": expected_sha,
                "hash_match": bool(sha and expected_sha and sha == expected_sha),
                "header_ok": bool(parsed.get("ok")),
                "label": "STRUCTURAL_ONLY",
                "runtime_measured": False,
            }
        )
    return rows


def measure_from_rows(facts):
    """Classify measured explorer facts. Missing calibration is UNMEASURED."""
    facts = facts or {}
    return {
        "measured": True,
        "card_present": bool(facts.get("card_present")),
        "catalog_present": bool(facts.get("catalog_present")),
        "door_present": bool(facts.get("door_present")),
        "landed_present": list(facts.get("landed_present") or []),
        "landed_missing": list(facts.get("landed_missing") or []),
        "found_phrases": list(facts.get("found_phrases") or []),
        "excerpt_count": int(facts.get("excerpt_count") or 0),
        "hash_match_count": int(facts.get("hash_match_count") or 0),
        "runtime_sold": bool(facts.get("runtime_sold")),
        "host_training_sold": bool(facts.get("host_training_sold")),
        "titan_mutation_sold": bool(facts.get("titan_mutation_sold")),
        "lda_blocked": bool(facts.get("lda_blocked")),
        "copy_private_lda": bool(facts.get("copy_private_lda")),
        "structural_only": bool(facts.get("structural_only")),
        "posting_open": bool(facts.get("posting_open")),
        "no_auth": bool(facts.get("no_auth")),
        "no_gate": bool(facts.get("no_gate")),
        "calibration_ok": bool(facts.get("calibration_ok")),
        "calibration_hits": list(facts.get("calibration_hits") or []),
        "search_space": list(facts.get("search_space") or SEARCH_SPACE),
        "misses": list(facts.get("misses") or []),
        "titan": str(facts.get("titan") or "NOT_WRITTEN"),
    }


def classify(row):
    """Turn a measured explorer census into a desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "Subzero explorer leftover not read. Absence was not stillness. "
                "A Slack inventory is not a land."
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
    if not row.get("card_present") or not row.get("catalog_present") or not row.get("door_present"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/catalog/door"])
                + ". JOJO TECHNICAL_HANDOFF / Artifact Explorer talk is CLAIMED "
                "until the leftover ships. FINDER-FAILED, never 0."
            ),
        }
    if landed_missing:
        return {
            "state": "NOT_LANDED",
            "note": (
                "named already-landed leftover(s) missing: "
                + ", ".join(landed_missing)
                + ". Do not remint tech/buyers. FINDER-FAILED, never 0."
            ),
        }
    if row.get("runtime_sold") or row.get("host_training_sold") or row.get("titan_mutation_sold"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "catalog sold runtime-measured, host training, or live Titan "
                "mutation as finished capability. That is not this leftover. "
                "FINDER-FAILED, never 0."
            ),
        }
    if row.get("copy_private_lda"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "catalog asks to copy private LDA source. Do not. "
                "FINDER-FAILED, never 0."
            ),
        }
    if (
        row.get("excerpt_count") != EXPECTED_EXCERPTS
        or row.get("hash_match_count") != EXPECTED_EXCERPTS
        or not row.get("structural_only")
        or not row.get("lda_blocked")
    ):
        return {
            "state": "NOT_LANDED",
            "note": (
                "validation packet incomplete: excerpts %s/%s hash-match, "
                "STRUCTURAL_ONLY=%s, LDA blocked=%s. FINDER-FAILED, never 0."
                % (
                    row.get("hash_match_count"),
                    row.get("excerpt_count"),
                    row.get("structural_only"),
                    row.get("lda_blocked"),
                )
            ),
        }
    needed = [phrase for phrase in REQUIRED_PHRASES if phrase not in (row.get("found_phrases") or [])]
    if needed or not row.get("posting_open") or not row.get("no_auth") or not row.get("no_gate"):
        return {
            "state": "NOT_LANDED",
            "note": (
                "leftover present but incomplete. Missing phrases: "
                + ", ".join(needed)
                + ". Open door + no auth + no gate required. Talk is CLAIMED. "
                "FINDER-FAILED, never 0."
            ),
        }
    if str(row.get("titan") or "").upper() != "NOT_WRITTEN":
        return {
            "state": "NOT_LANDED",
            "note": "this leftover must stay titan NOT_WRITTEN. FINDER-FAILED, never 0.",
        }
    return {
        "state": "INTEGRATED",
        "note": (
            "Subzero Artifact Explorer leftover is on this tree. 31/31 public "
            "excerpts hash-match and stay STRUCTURAL_ONLY. LDA execution is "
            "BLOCKED_ON_PUBLISHED_WIDE_RECEIVER_RESULT. Host training is "
            "NOT_SOLD. A Slack TECHNICAL_HANDOFF is still not the file."
        ),
    }


def measure_root(root):
    root = os.path.abspath(root)
    misses = []
    blobs = []
    for rel in SEARCH_SPACE:
        if rel in (EXCERPT_DIR, ARCH):
            if not _isdir(root, rel):
                misses.append(rel)
            continue
        text = _read(root, rel)
        if not text:
            misses.append(rel)
        else:
            blobs.append(text)
    hay = "\n".join(blobs).lower()
    found = [phrase for phrase in REQUIRED_PHRASES if phrase in hay]
    landed_present = [rel for rel in ALREADY_LANDED if _exists(root, rel)]
    landed_missing = [rel for rel in ALREADY_LANDED if not _exists(root, rel)]
    catalog = load_catalog(_read(root, DEFAULT_CATALOG))
    excerpt_rows = measure_excerpts(root)
    archetypes = count_archetypes(root)
    hash_match_count = sum(1 for item in excerpt_rows if item.get("hash_match"))
    runtime_sold = bool(catalog.get("label") == "CROSS_PROCESS/RUNTIME_MEASURED") or any(
        item.get("runtime_measured") or item.get("label") == "CROSS_PROCESS/RUNTIME_MEASURED"
        for item in catalog.get("rows") or []
    )
    host_training_sold = catalog.get("host_training") in ("CUSTOMER_READY", "SOLD", "FINISHED")
    titan_mutation_sold = catalog.get("titan_mutation") in ("FINISHED", "CUSTOMER_READY", "SOLD")
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    calibration_ok = len(calibration_hits) == len(CALIBRATION)
    if not calibration_ok:
        for rel in CALIBRATION:
            if rel not in calibration_hits and rel not in misses:
                misses.append("calibration:" + rel)
    posting_open = (
        catalog.get("posting") == "OPEN"
        and "open door" in hay
        and "unseated" in hay
    )
    facts = {
        "card_present": _exists(root, DEFAULT_CARD),
        "catalog_present": _exists(root, DEFAULT_CATALOG) and not catalog.get("error"),
        "door_present": _exists(root, DEFAULT_DOOR),
        "landed_present": landed_present,
        "landed_missing": landed_missing,
        "found_phrases": found,
        "excerpt_count": len(excerpt_rows),
        "hash_match_count": hash_match_count,
        "runtime_sold": runtime_sold,
        "host_training_sold": host_training_sold,
        "titan_mutation_sold": titan_mutation_sold,
        "lda_blocked": catalog.get("lda_state") == LDA_BLOCK and catalog.get("lda_sha") == LDA_SHA,
        "copy_private_lda": bool(catalog.get("copy_private_lda")),
        "structural_only": catalog.get("label") == "STRUCTURAL_ONLY" and all(
            item.get("label") == "STRUCTURAL_ONLY" for item in excerpt_rows
        ),
        "posting_open": posting_open,
        "no_auth": bool(catalog.get("no_auth")) and "no auth" in hay,
        "no_gate": bool(catalog.get("no_gate")) and "no gate" in hay,
        "calibration_ok": calibration_ok,
        "calibration_hits": calibration_hits,
        "search_space": list(SEARCH_SPACE),
        "misses": misses,
        "titan": catalog.get("titan") or "NOT_WRITTEN",
    }
    row = measure_from_rows(facts)
    row.update(
        {
            "slack_ts": catalog.get("slack_ts") or SLACK_TS,
            "handoff_id": catalog.get("handoff_id") or HANDOFF_ID,
            "archetypes": archetypes,
            "excerpts": excerpt_rows,
            "x": [rel for rel in SEARCH_SPACE if (_exists(root, rel) or _isdir(root, rel))],
            "y": {
                "calibration_hits": calibration_hits,
                "found_phrases": found,
                "hash_match_count": hash_match_count,
                "excerpt_count": len(excerpt_rows),
                "archetypes": archetypes,
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
    missing = classify(
        measure_from_rows(
            {
                "card_present": False,
                "catalog_present": False,
                "door_present": False,
                "misses": ["ground/SUBZERO_EXPLORER.md"],
                "calibration_ok": True,
            }
        )
    )
    assert missing["state"] == "NOT_LANDED", missing
    sold = classify(
        measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "door_present": True,
                "landed_present": list(ALREADY_LANDED),
                "landed_missing": [],
                "found_phrases": list(REQUIRED_PHRASES),
                "excerpt_count": EXPECTED_EXCERPTS,
                "hash_match_count": EXPECTED_EXCERPTS,
                "runtime_sold": False,
                "host_training_sold": True,
                "titan_mutation_sold": False,
                "lda_blocked": True,
                "copy_private_lda": False,
                "structural_only": True,
                "posting_open": True,
                "no_auth": True,
                "no_gate": True,
                "calibration_ok": True,
                "titan": "NOT_WRITTEN",
            }
        )
    )
    assert sold["state"] == "NOT_LANDED", sold
    assert "host training" in sold["note"].lower(), sold
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure Subzero Artifact Explorer leftover")
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
