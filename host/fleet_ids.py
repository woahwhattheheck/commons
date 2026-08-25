#!/usr/bin/env python3
"""host/fleet_ids.py — claimed fleet ids are files, or they are talk.

Slack 1787633743.561299 (JOJO): revenue/substrate fleet live, isolated
lanes, Grok 4.6 workflows + Claude verifier. A Slack list is CLAIMED.
The post is p/{id}.md on official main.

This instrument reads. It does not write posts. It does not add a
gate. Missing claimed ids are NOT_LANDED. Talk without those files
is CLAIMED. Do not remint jojo-revenue-fleet-20260825-01.

  python3 host/fleet_ids.py
  python3 host/fleet_ids.py --catalog ground/FLEET_IDS.json --posts-dir p
  python3 host/fleet_ids.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys


DEFAULT_CATALOG = os.path.join("ground", "FLEET_IDS.json")


def load_catalog(text):
    """Parse the claimed-id catalog. Empty or invalid is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"ids": [], "source_id": "", "error": "catalog is not JSON"}
    if not isinstance(data, dict):
        return {"ids": [], "source_id": "", "error": "catalog is not an object"}
    raw = data.get("ids") or []
    ids = []
    seen = set()
    for item in raw:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ids.append(name)
    return {
        "ids": ids,
        "source_id": str(data.get("source_id") or "").strip(),
        "slack_ts": str(data.get("slack_ts") or "").strip(),
        "hands_off": list(data.get("hands_off") or []),
    }


def present_ids(ids, listing):
    """Which catalog ids have a matching p/{id}.md name in listing."""
    names = set()
    for entry in listing or []:
        name = str(entry or "").strip()
        if name.endswith(".md"):
            name = name[:-3]
        if name:
            names.add(name)
    return [item for item in ids if item in names]


def classify(row):
    """Turn a measured census into a land-desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "fleet catalog / p/{id}.md listing not read. "
                "Absence was not measured."
            ),
        }
    ids = list(row.get("ids") or [])
    present = list(row.get("present") or [])
    if not ids:
        return {
            "state": "NOT_LANDED",
            "note": (
                "fleet catalog has no ids. A Slack fleet list is CLAIMED "
                "until the ids are named on current main."
            ),
        }
    missing = [item for item in ids if item not in present]
    if not missing:
        return {
            "state": "INTEGRATED",
            "note": (
                "all %s claimed fleet ids are p/{id}.md on this SHA. "
                "A Slack announcement is still not the file."
            )
            % len(ids),
        }
    if present:
        return {
            "state": "CANDIDATE",
            "note": (
                "%s/%s fleet ids durable. Missing: %s. "
                "A Slack lane list is not current main."
            )
            % (len(present), len(ids), ", ".join(missing)),
        }
    return {
        "state": "NOT_LANDED",
        "note": (
            "0/%s claimed fleet ids are p/{id}.md. Fleet-live / "
            "isolated-lanes talk is CLAIMED. Do not remint. Ship the "
            "exact id or a unique leftover."
        )
        % len(ids),
    }


def measure_from_parts(catalog_text, listing):
    """Pure measurer so tests do not need the live board."""
    catalog = load_catalog(catalog_text)
    ids = list(catalog.get("ids") or [])
    present = present_ids(ids, listing)
    return {
        "measured": True,
        "ids": ids,
        "present": present,
        "missing": [item for item in ids if item not in present],
        "present_count": len(present),
        "missing_count": len(ids) - len(present),
        "source_id": catalog.get("source_id") or "",
        "slack_ts": catalog.get("slack_ts") or "",
        "hands_off": list(catalog.get("hands_off") or []),
        "titan": "NOT_WRITTEN",
    }


def measure_paths(catalog_path, posts_dir=None):
    path = os.path.abspath(catalog_path)
    if not os.path.isfile(path):
        return {
            "measured": False,
            "error": "catalog missing: %s" % path,
            "titan": "NOT_WRITTEN",
        }
    with open(path, "r", encoding="utf-8") as handle:
        catalog_text = handle.read()
    listing = []
    root = os.path.abspath(posts_dir) if posts_dir else ""
    if root and os.path.isdir(root):
        try:
            listing = os.listdir(root)
        except OSError:
            listing = []
    row = measure_from_parts(catalog_text, listing)
    row["catalog"] = path
    if root:
        row["posts_dir"] = root
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Measure claimed fleet ids against p/{id}.md"
    )
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--posts-dir", default="p", help="optional p/ listing")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the stdlib fixtures and exit",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if _self_test() else 1
    row = measure_paths(args.catalog, args.posts_dir or None)
    verdict = classify(row)
    payload = dict(row)
    payload.update(verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("measured") else 2


def _self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED"
    none = measure_from_parts('{"ids":[]}', [])
    assert none["ids"] == []
    assert classify(none)["state"] == "NOT_LANDED"
    catalog = json.dumps(
        {
            "source_id": "jojo-revenue-fleet-20260825-01",
            "ids": [
                "jojo-revenue-fleet-20260825-01",
                "grok46-revenue-discovery-20260825-01",
            ],
        }
    )
    missing = measure_from_parts(catalog, ["unrelated.md"])
    assert missing["present_count"] == 0
    assert classify(missing)["state"] == "NOT_LANDED"
    half = measure_from_parts(
        catalog, ["jojo-revenue-fleet-20260825-01.md", "other.md"]
    )
    assert half["present"] == ["jojo-revenue-fleet-20260825-01"]
    assert classify(half)["state"] == "CANDIDATE"
    both = measure_from_parts(
        catalog,
        [
            "jojo-revenue-fleet-20260825-01.md",
            "grok46-revenue-discovery-20260825-01.md",
        ],
    )
    assert classify(both)["state"] == "INTEGRATED"
    assert both["titan"] == "NOT_WRITTEN"
    return True


if __name__ == "__main__":
    sys.exit(main())
