#!/usr/bin/env python3
"""host/claude_peer_check.py — HIS named-failure index completeness.

WIRE leftover: if a mode lives only on CLAUDE_FAILURE_MODES (or
laptop companions), keep looking until it is indexed on
ground/CLAUDE_PEER_CHECK.md. CLASS 17c was the first named miss
(P40). HIT-FM02 leftover: BULLY / PROOF / FAILURE_MODES copies
are on git — the card must cite those paths. HIT-SR01 leftover:
soft dump "may edit/build/ship" is law-violation vs Plug
RECEIVE-only / seated_claude=NO, not permission. A11 indexes
that. Do not rewrite PROOF/BULLY/CHAIR/PAD. Hard RECEIVE
baseline is evidence/bully_sessions/. CLAUDE_CORNER.md stays
FINDER-FAILED, never 0.

This leftover does not remint wire-claude-peer-check-20260902-01,
cursor-claude-peer-check-bryce-wake-named-failures-20260902-01,
cursor-claude-peer-check-17c-index-20260902-01,
cursor-claude-peer-check-git-paths-20260902-01, or
stamp-claude-failure-unique-seated-receive-20260902-01.
It does not write titan. It does not smash commons.mno. It does
not add a posting gate. A miss prints FINDER-FAILED plus the
search space. Never 0.

  python3 host/claude_peer_check.py
  python3 host/claude_peer_check.py --root .
  python3 host/claude_peer_check.py --self-test

X = exact files / packet ids / laptop paths in SEARCH_SPACE
Y = packets found + P40/17c + A11/HIT-SR01 indexed + git companions present, or FINDER-FAILED
Z = missing file / unindexed packet / stale off-git claim / laptop miss / CLAUDE_CORNER miss / failed calibration
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "CLAUDE_PEER_CHECK.json")
DEFAULT_CARD = os.path.join("ground", "CLAUDE_PEER_CHECK.md")
DEFAULT_DUMP = os.path.join("muhl", "docs", "CLAUDE_FAILURE_MODES.md")
WIRE_ID = "wire-claude-peer-check-20260902-01"
NAMED_RECEIPT = "cursor-claude-peer-check-bryce-wake-named-failures-20260902-01"
INDEX_17C_ID = "cursor-claude-peer-check-17c-index-20260902-01"
SOURCE_ID = "cursor-claude-peer-check-git-paths-20260902-01"
STAMP_FM_ID = "stamp-claude-failure-docs-unique-20260902-01"
STAMP_SR_ID = "stamp-claude-failure-unique-seated-receive-20260902-01"
INDEX_SR01_ID = "cursor-claude-peer-check-seated-receive-20260902-01"
HARD_RECEIVE_PROOF = os.path.join("evidence", "bully_sessions", "CLAUDE_PROOF_PACKET.md")
HARD_RECEIVE_BULLY = os.path.join("evidence", "bully_sessions", "BULLY_CLAUDE.txt")
HARD_RECEIVE_MARKERS = (
    "claude receives. claude writes nothing",
    "is not a builder",
)
SOFT_AS_PERMISSION_MARKERS = (
    "may edit/build/ship",
    "receive-only",
    "not a permission",
)
CLAUDE_CORNER_NAME = "CLAUDE_CORNER.md"
STALE_OFF_GIT_PHRASE = "not always on git"
GIT_COMPANIONS = (
    os.path.join("muhl", "docs", "CLAUDE_FAILURE_MODES.md"),
    os.path.join("muhl", "docs", "BULLY_CLAUDE.txt"),
    os.path.join("muhl", "docs", "CLAUDE_PROOF_PACKET.md"),
    os.path.join("evidence", "bully_sessions", "CLAUDE_FAILURE_MODES.md"),
    os.path.join("evidence", "bully_sessions", "BULLY_CLAUDE.txt"),
    os.path.join("evidence", "bully_sessions", "CLAUDE_PROOF_PACKET.md"),
    os.path.join("ground", "pc-purge-20260820", "CLAUDE_FAILURE_MODES.md"),
    os.path.join("ground", "pc-purge-20260820", "BULLY_CLAUDE.txt"),
    os.path.join("ground", "pc-purge-20260820", "CLAUDE_PROOF_PACKET.md"),
)
REQUIRED_PACKETS = (
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "17",
    "17b",
    "17c",
    "17d",
)
LAPTOP_PATHS = (
    r"C:\Users\lucys",
    "C:/Users/lucys",
    "/mnt/c/Users/lucys",
)
TITLE_PHRASES = ("purity spiral", "GOO READ")
SEARCH_SPACE = (
    DEFAULT_CARD,
    DEFAULT_CATALOG,
    DEFAULT_DUMP,
    os.path.join("host", "claude_peer_check.py"),
    os.path.join("p", NAMED_RECEIPT + ".md"),
)
CALIBRATION = (
    os.path.join("ground", "HEAD.md"),
    DEFAULT_CARD,
    DEFAULT_DUMP,
)
PACKET_HEAD = re.compile(
    r"^##\s+(?P<id>0|[1-9][0-9]*[a-z]?)\.\s+",
    re.MULTILINE,
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
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "catalog is not JSON"}
    if not isinstance(data, dict):
        return {"error": "catalog is not an object"}
    named = data.get("named_ids") or {}
    if not isinstance(named, dict):
        named = {}
    packets = [str(item).strip() for item in named.get("failure_mode_packets") or [] if str(item).strip()]
    priors = [str(item).strip() for item in named.get("priors") or [] if str(item).strip()]
    p40 = data.get("p40") or {}
    if not isinstance(p40, dict):
        p40 = {}
    a11 = data.get("a11") or {}
    if not isinstance(a11, dict):
        a11 = {}
    git_companions = data.get("git_companions") or {}
    if not isinstance(git_companions, dict):
        git_companions = {}
    return {
        "cite": str(data.get("cite") or "").strip(),
        "no_auth": bool(data.get("no_auth", True)),
        "no_gate": bool(data.get("no_gate", True)),
        "packets": packets,
        "priors": priors,
        "p40_id": str(p40.get("id") or "").strip(),
        "p40_packet": str(p40.get("packet") or "").strip(),
        "a11_id": str(a11.get("id") or "").strip(),
        "a11_hit": str(a11.get("hit") or "").strip(),
        "a11_not_permission": bool(a11.get("not_permission")),
        "a11_not_gate": bool(a11.get("not_gate")),
        "authority": [
            str(item).strip() for item in named.get("authority") or [] if str(item).strip()
        ],
        "git_companion_paths": [
            str(item).strip()
            for item in git_companions.get("paths") or []
            if str(item).strip()
        ],
        "git_companions_on_git": bool(git_companions.get("present_on_git")),
        "error": "",
    }


def parse_packets(text):
    found = []
    for match in PACKET_HEAD.finditer(text or ""):
        packet_id = match.group("id")
        if packet_id == "0":
            continue
        if packet_id not in found:
            found.append(packet_id)
    return found


def card_claims_companions_off_git(card_text):
    return STALE_OFF_GIT_PHRASE in (card_text or "").lower()


def git_companions_probe(root, paths=None):
    wanted = list(paths or GIT_COMPANIONS)
    hits = [rel for rel in wanted if _exists(root, rel)]
    missing = [rel for rel in wanted if rel not in hits]
    return {
        "search_space": wanted,
        "hits": hits,
        "missing": missing,
        "state": "FOUND" if not missing else "FINDER-FAILED",
        "count": None if missing else len(hits),
        "diverge": True,
    }


def index_has_a11(card_text, catalog):
    blob = (card_text or "").lower()
    catalog = catalog or {}
    has_row = "a11" in blob and "hit-sr01" in blob and "receive-only" in blob
    has_not_perm = "not a permission" in blob or "not permission" in blob
    catalog_ok = (
        catalog.get("a11_id") == "A11"
        and catalog.get("a11_hit") == "HIT-SR01"
        and catalog.get("a11_not_permission")
        and catalog.get("a11_not_gate")
        and "A11" in (catalog.get("authority") or [])
    )
    return bool((has_row and has_not_perm) or catalog_ok)


def claude_corner_probe(root, walk=None):
    root = os.path.abspath(root)
    hits = []
    for rel in walk or TITLE_WALK:
        start = os.path.join(root, rel)
        if not os.path.isdir(start):
            continue
        for dirpath, dirnames, filenames in os.walk(start):
            dirnames[:] = [
                name
                for name in dirnames
                if name not in {".git", "node_modules", "__pycache__"}
            ]
            for name in filenames:
                if name == CLAUDE_CORNER_NAME:
                    hits.append(os.path.join(dirpath, name))
    return {
        "search_space": [CLAUDE_CORNER_NAME] + list(walk or TITLE_WALK),
        "hits": hits,
        "state": "FOUND" if hits else "FINDER-FAILED",
        "count": None if not hits else len(hits),
    }


def hard_receive_baseline_probe(root):
    wanted = [HARD_RECEIVE_PROOF, HARD_RECEIVE_BULLY]
    hits = []
    missing = []
    missing_markers = []
    for rel in wanted:
        text = _read(root, rel)
        if not text:
            missing.append(rel)
            continue
        hits.append(rel)
        blob = text.lower()
        if rel == HARD_RECEIVE_PROOF and HARD_RECEIVE_MARKERS[0] not in blob:
            missing_markers.append(rel + ":RECEIVES")
        if rel == HARD_RECEIVE_BULLY and HARD_RECEIVE_MARKERS[1] not in blob:
            missing_markers.append(rel + ":NOT_A_BUILDER")
    failed = bool(missing or missing_markers)
    return {
        "search_space": wanted,
        "hits": hits,
        "missing": missing,
        "missing_markers": missing_markers,
        "state": "FINDER-FAILED" if failed else "FOUND",
        "count": None if failed else len(hits),
    }


def index_has_17c(card_text, catalog):
    blob = (card_text or "").lower()
    catalog = catalog or {}
    if "p40" in blob and "17c" in blob:
        return True
    if catalog.get("p40_id") == "P40" and catalog.get("p40_packet") == "17c":
        return True
    if "P40" in (catalog.get("priors") or []) and "17c" in (catalog.get("packets") or []):
        return True
    return False


def laptop_probe(paths=None):
    tried = list(paths or LAPTOP_PATHS)
    hits = [path for path in tried if os.path.exists(path)]
    return {
        "search_space": tried,
        "hits": hits,
        "state": "FOUND" if hits else "FINDER-FAILED",
        "count": None if not hits else len(hits),
    }


TITLE_WALK = (
    os.path.join("muhl", "docs"),
    os.path.join("ground"),
    os.path.join("ground", "pc-purge-20260820"),
    os.path.join("evidence", "bully_sessions"),
)


def title_phrase_probe(root, phrases=None, walk=None):
    root = os.path.abspath(root)
    wanted = list(phrases or TITLE_PHRASES)
    hits = []
    for rel in walk or TITLE_WALK:
        start = os.path.join(root, rel)
        if not os.path.isdir(start):
            continue
        for dirpath, dirnames, filenames in os.walk(start):
            dirnames[:] = [
                name
                for name in dirnames
                if name not in {".git", "node_modules", "__pycache__"}
            ]
            for name in filenames:
                lower = name.lower()
                compact = lower.replace(" ", "").replace("_", "").replace("-", "")
                for phrase in wanted:
                    token = phrase.lower().replace(" ", "")
                    if token and token in compact:
                        hits.append(os.path.join(dirpath, name))
                        break
    return {
        "search_space": wanted + list(walk or TITLE_WALK),
        "hits": hits,
        "state": "FOUND" if hits else "FINDER-FAILED",
        "count": None if not hits else len(hits),
    }


def measure_from_rows(facts):
    facts = facts or {}
    return {
        "measured": True,
        "card_present": bool(facts.get("card_present")),
        "catalog_present": bool(facts.get("catalog_present")),
        "dump_present": bool(facts.get("dump_present")),
        "packets_found": list(facts.get("packets_found") or []),
        "packets_missing": list(facts.get("packets_missing") or []),
        "indexed_17c": bool(facts.get("indexed_17c")),
        "indexed_a11": bool(facts.get("indexed_a11")),
        "hard_receive": dict(
            facts.get("hard_receive")
            or {"state": "FOUND", "missing": [], "hits": [], "search_space": []}
        ),
        "claude_corner": dict(
            facts.get("claude_corner")
            or {"state": "FINDER-FAILED", "hits": [], "count": None, "search_space": []}
        ),
        "git_companions": dict(
            facts.get("git_companions")
            or {"state": "FOUND", "missing": [], "hits": [], "search_space": []}
        ),
        "card_stale_off_git": bool(facts.get("card_stale_off_git")),
        "laptop": dict(facts.get("laptop") or {}),
        "title_phrases": dict(facts.get("title_phrases") or {}),
        "no_auth": bool(facts.get("no_auth", True)),
        "no_gate": bool(facts.get("no_gate", True)),
        "calibration_ok": bool(facts.get("calibration_ok")),
        "calibration_hits": list(facts.get("calibration_hits") or []),
        "search_space": list(facts.get("search_space") or SEARCH_SPACE),
        "misses": list(facts.get("misses") or []),
        "titan": str(facts.get("titan") or "NOT_WRITTEN"),
        "do_not_remint": list(
            facts.get("do_not_remint")
            or [WIRE_ID, NAMED_RECEIPT, INDEX_17C_ID, SOURCE_ID, STAMP_FM_ID, STAMP_SR_ID]
        ),
    }


def classify(row):
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "z": "FINDER-FAILED",
            "note": (
                "Claude peer-check leftover not read. Absence was not stillness. "
                "Never 0."
            ),
        }
    if row.get("calibration_ok") is False:
        return {
            "state": "UNMEASURED",
            "z": "FINDER-FAILED",
            "note": (
                "known-present calibration failed: "
                + ", ".join(row.get("calibration_hits") or [])
                + ". Search-zero testing is instrument failure, not absence proof. Never 0."
            ),
        }
    misses = list(row.get("misses") or [])
    if not (
        row.get("card_present")
        and row.get("catalog_present")
        and row.get("dump_present")
    ):
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": (
                "missing leftover path(s): "
                + ", ".join(misses or ["card/catalog/dump"])
                + ". Never 0."
            ),
        }
    missing_packets = list(row.get("packets_missing") or [])
    if missing_packets or not row.get("indexed_17c"):
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": (
                "HIS dump packets unindexed or P40/17c missing: "
                + ", ".join(missing_packets or ["17c"])
                + ". Keep looking. Never 0."
            ),
        }
    if not row.get("indexed_a11"):
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": (
                "A11 / HIT-SR01 missing. Soft may-edit/build/ship is "
                "law-violation vs Plug RECEIVE-only, not permission. Never 0."
            ),
        }
    hard_receive = row.get("hard_receive") or {}
    if hard_receive.get("state") != "FOUND":
        missing = list(hard_receive.get("missing") or []) + list(
            hard_receive.get("missing_markers") or []
        )
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": (
                "hard RECEIVE baseline missing: "
                + ", ".join(missing or ["evidence/bully_sessions/"])
                + ". HIT-SR01. Never 0."
            ),
        }
    if row.get("card_stale_off_git"):
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": (
                "peer-check card still claims failure-doc companions are off git. "
                "Cite muhl/docs + evidence/bully_sessions + ground/pc-purge-20260820. "
                "HIT-FM02. Never 0."
            ),
        }
    git_companions = row.get("git_companions") or {}
    if git_companions.get("state") != "FOUND":
        missing = list(git_companions.get("missing") or [])
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": (
                "git companion path(s) missing: "
                + ", ".join(missing or ["CLAUDE_FAILURE_MODES/BULLY/PROOF"])
                + ". HIT-FM02. Never 0."
            ),
        }
    if not row.get("no_auth") or not row.get("no_gate"):
        return {
            "state": "NOT_LANDED",
            "z": "FINDER-FAILED",
            "note": "catalog closed the door. Discard that path. Never 0.",
        }
    laptop = row.get("laptop") or {}
    titles = row.get("title_phrases") or {}
    corner = row.get("claude_corner") or {}
    return {
        "state": "INTEGRATED",
        "z": {
            "laptop": laptop.get("state") or "FINDER-FAILED",
            "title_phrases": titles.get("state") or "FINDER-FAILED",
            "claude_corner": corner.get("state") or "FINDER-FAILED",
        },
        "note": (
            "P40/17c + A11/HIT-SR01 indexed. HIS dump packets 1–15, 17, 17b–d named. "
            "Git companions (FAILURE_MODES/BULLY/PROOF) present on git. "
            "Hard RECEIVE baseline present. Soft may-edit/build/ship is law-violation, "
            "not permission. CLAUDE_CORNER.md stays FINDER-FAILED. "
            "Laptop live path stays FINDER-FAILED until reconnect. Never 0."
        ),
    }


def measure_root(root):
    root = os.path.abspath(root)
    misses = []
    search_hits = {}
    for rel in SEARCH_SPACE:
        text = _read(root, rel)
        if not text:
            misses.append(rel)
        search_hits[rel] = text
    card_text = search_hits.get(DEFAULT_CARD, "")
    catalog_text = search_hits.get(DEFAULT_CATALOG, "")
    dump_text = search_hits.get(DEFAULT_DUMP, "")
    catalog = load_catalog(catalog_text) if catalog_text else {}
    packets_found = parse_packets(dump_text)
    packets_missing = [item for item in REQUIRED_PACKETS if item not in packets_found]
    calibration_hits = [rel for rel in CALIBRATION if _exists(root, rel)]
    facts = measure_from_rows(
        {
            "card_present": bool(card_text),
            "catalog_present": bool(catalog_text) and not catalog.get("error"),
            "dump_present": bool(dump_text),
            "packets_found": packets_found,
            "packets_missing": packets_missing,
            "indexed_17c": index_has_17c(card_text, catalog),
            "indexed_a11": index_has_a11(card_text, catalog),
            "hard_receive": hard_receive_baseline_probe(root),
            "claude_corner": claude_corner_probe(root),
            "git_companions": git_companions_probe(root),
            "card_stale_off_git": card_claims_companions_off_git(card_text),
            "laptop": laptop_probe(),
            "title_phrases": title_phrase_probe(root),
            "no_auth": bool(catalog.get("no_auth", True)),
            "no_gate": bool(catalog.get("no_gate", True)),
            "calibration_ok": calibration_hits == list(CALIBRATION),
            "calibration_hits": calibration_hits,
            "search_space": list(SEARCH_SPACE) + list(LAPTOP_PATHS),
            "misses": misses,
        }
    )
    verdict = classify(facts)
    facts["state"] = verdict["state"]
    facts["z"] = verdict["z"]
    facts["note"] = verdict["note"]
    facts["x"] = facts["search_space"]
    facts["y"] = {
        "packets_found": facts["packets_found"],
        "indexed_17c": facts["indexed_17c"],
        "indexed_a11": facts["indexed_a11"],
        "hard_receive": facts["hard_receive"],
        "claude_corner": facts["claude_corner"],
        "git_companions": facts["git_companions"],
        "card_stale_off_git": facts["card_stale_off_git"],
        "laptop": facts["laptop"],
        "title_phrases": facts["title_phrases"],
    }
    return facts


def self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED"
    assert empty["z"] == "FINDER-FAILED"
    assert "0" not in str(empty.get("count"))
    bad_cal = classify(
        {
            "measured": True,
            "calibration_ok": False,
            "calibration_hits": [],
            "card_present": True,
            "catalog_present": True,
            "dump_present": True,
        }
    )
    assert bad_cal["state"] == "UNMEASURED"
    assert bad_cal["z"] == "FINDER-FAILED"
    missing_17c = classify(
        measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "dump_present": True,
                "packets_found": list(REQUIRED_PACKETS),
                "packets_missing": [],
                "indexed_17c": False,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
                "no_auth": True,
                "no_gate": True,
            }
        )
    )
    assert missing_17c["state"] == "NOT_LANDED"
    assert missing_17c["z"] == "FINDER-FAILED"
    stale = classify(
        measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "dump_present": True,
                "packets_found": list(REQUIRED_PACKETS),
                "packets_missing": [],
                "indexed_17c": True,
                "indexed_a11": True,
                "card_stale_off_git": True,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
                "no_auth": True,
                "no_gate": True,
            }
        )
    )
    assert stale["state"] == "NOT_LANDED"
    assert stale["z"] == "FINDER-FAILED"
    assert "HIT-FM02" in stale["note"]
    missing_git = classify(
        measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "dump_present": True,
                "packets_found": list(REQUIRED_PACKETS),
                "packets_missing": [],
                "indexed_17c": True,
                "indexed_a11": True,
                "card_stale_off_git": False,
                "git_companions": {
                    "state": "FINDER-FAILED",
                    "missing": ["muhl/docs/BULLY_CLAUDE.txt"],
                    "count": None,
                },
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
                "no_auth": True,
                "no_gate": True,
            }
        )
    )
    assert missing_git["state"] == "NOT_LANDED"
    assert missing_git["z"] == "FINDER-FAILED"
    ok = classify(
        measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "dump_present": True,
                "packets_found": list(REQUIRED_PACKETS),
                "packets_missing": [],
                "indexed_17c": True,
                "indexed_a11": True,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
                "no_auth": True,
                "no_gate": True,
                "laptop": {"state": "FINDER-FAILED", "count": None},
                "title_phrases": {"state": "FINDER-FAILED", "count": None},
                "claude_corner": {"state": "FINDER-FAILED", "count": None},
            }
        )
    )
    assert ok["state"] == "INTEGRATED"
    assert ok["z"]["laptop"] == "FINDER-FAILED"
    assert ok["z"]["claude_corner"] == "FINDER-FAILED"
    missing_a11 = classify(
        measure_from_rows(
            {
                "card_present": True,
                "catalog_present": True,
                "dump_present": True,
                "packets_found": list(REQUIRED_PACKETS),
                "packets_missing": [],
                "indexed_17c": True,
                "indexed_a11": False,
                "calibration_ok": True,
                "calibration_hits": list(CALIBRATION),
                "no_auth": True,
                "no_gate": True,
            }
        )
    )
    assert missing_a11["state"] == "NOT_LANDED"
    assert missing_a11["z"] == "FINDER-FAILED"
    assert "HIT-SR01" in missing_a11["note"]
    sample = (
        "## 15. weights\n\n"
        "## 17. CLASS 17\n\n"
        "## 17c. CLASS 17 — hooks dark\n\n"
    )
    assert parse_packets(sample) == ["15", "17", "17c"]
    laptop = laptop_probe(["/definitely-not-bryces-laptop"])
    assert laptop["state"] == "FINDER-FAILED"
    assert laptop["count"] is None
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        print(self_test())
        return 0
    row = measure_root(args.root)
    if args.json:
        print(json.dumps(row, indent=2, sort_keys=True))
    else:
        print(row["state"])
        print("X", ", ".join(row["x"]))
        print(
            "Y indexed_17c=%s indexed_a11=%s packets=%s git_companions=%s stale_off_git=%s hard_receive=%s"
            % (
                row["indexed_17c"],
                row.get("indexed_a11"),
                ",".join(row["packets_found"]),
                (row.get("git_companions") or {}).get("state"),
                row.get("card_stale_off_git"),
                (row.get("hard_receive") or {}).get("state"),
            )
        )
        print("Z", row["z"])
        print(row["note"])
    return 0 if row.get("state") == "INTEGRATED" else 1


if __name__ == "__main__":
    sys.exit(main())
