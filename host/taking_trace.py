#!/usr/bin/env python3
"""host/taking_trace.py — Slack TAKING ids are files, or they are talk.

Slack 1787634411.405189 (DEMON rolling utilization report): four
responsive grok.exe sessions and three claimed TAKING ids. Trace those
ids against official Commons main. LocalDeviceAgent is a private repo;
this public instrument does not fetch or copy those bytes.

A Slack capacity report is CLAIMED. Missing Commons p/{id}.md is
NOT_LANDED. A private LDA path without a supplied listing is
UNMEASURED. Do not remint the grok46 ids. Do not take the revenue
jobs. Do not remint fleet_ids / unused_invoke leftovers.

  python3 host/taking_trace.py
  python3 host/taking_trace.py --catalog ground/TAKING_TRACE.json --posts-dir p
  python3 host/taking_trace.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys


DEFAULT_CATALOG = os.path.join("ground", "TAKING_TRACE.json")


def load_catalog(text):
    """Parse the taking-id catalog. Empty or invalid is measured empty."""
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {
            "commons_ids": [],
            "source_id": "",
            "error": "catalog is not JSON",
        }
    if not isinstance(data, dict):
        return {
            "commons_ids": [],
            "source_id": "",
            "error": "catalog is not an object",
        }
    raw = data.get("commons_ids") or data.get("ids") or []
    ids = []
    seen = set()
    for item in raw:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ids.append(name)
    lda = data.get("lda") if isinstance(data.get("lda"), dict) else {}
    return {
        "commons_ids": ids,
        "source_id": str(data.get("source_id") or "").strip(),
        "slack_ts": str(data.get("slack_ts") or "").strip(),
        "hands_off": list(data.get("hands_off") or []),
        "lda_repo": str(lda.get("repo") or "").strip(),
        "lda_claimed_sha": str(lda.get("claimed_sha") or "").strip(),
        "lda_claimed_paths": [
            str(path or "").strip()
            for path in (lda.get("claimed_paths") or [])
            if str(path or "").strip()
        ],
        "lda_visibility": str(lda.get("visibility") or "").strip(),
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


def present_paths(paths, listing):
    """Which claimed paths appear in a supplied listing."""
    names = set()
    for entry in listing or []:
        name = str(entry or "").strip().replace("\\", "/")
        if name:
            names.add(name)
            names.add(os.path.basename(name))
    present = []
    for path in paths or []:
        norm = str(path or "").strip().replace("\\", "/")
        if not norm:
            continue
        if norm in names or os.path.basename(norm) in names:
            present.append(path)
    return present


def classify(row):
    """Turn a measured Commons + LDA census into a land-desk state."""
    row = row or {}
    if not row.get("measured"):
        return {
            "state": "UNMEASURED",
            "note": (
                "taking catalog / p/{id}.md listing not read. "
                "Absence was not measured."
            ),
        }
    ids = list(row.get("commons_ids") or [])
    present = list(row.get("commons_present") or [])
    if not ids:
        return {
            "state": "NOT_LANDED",
            "note": (
                "taking catalog has no Commons ids. A Slack utilization "
                "report is CLAIMED until the ids are named on current main."
            ),
        }
    missing = [item for item in ids if item not in present]
    lda_measured = bool(row.get("lda_measured"))
    lda_note = (
        " LDA listing measured."
        if lda_measured
        else (
            " LDA is private/unlisted here — UNMEASURED, not stillness. "
            "Do not copy private bytes onto Commons."
        )
    )
    if not missing:
        if lda_measured:
            lda_paths = list(row.get("lda_claimed_paths") or [])
            lda_present = list(row.get("lda_present") or [])
            lda_missing = [item for item in lda_paths if item not in lda_present]
            if lda_paths and not lda_missing:
                return {
                    "state": "INTEGRATED",
                    "note": (
                        "all %s claimed Commons taking ids are p/{id}.md "
                        "and the supplied LDA listing has the claimed paths. "
                        "A Slack capacity report is still not the file."
                    )
                    % len(ids),
                }
            return {
                "state": "CANDIDATE",
                "note": (
                    "Commons taking ids are durable. LDA listing missing: %s."
                    % (", ".join(lda_missing) or "unnamed")
                ),
            }
        return {
            "state": "CANDIDATE",
            "note": (
                "all %s claimed Commons taking ids are p/{id}.md."
                % len(ids)
            )
            + lda_note,
        }
    if present:
        return {
            "state": "CANDIDATE",
            "note": (
                "%s/%s Commons taking ids durable. Missing: %s. "
                "A Slack utilization report is not current main."
            )
            % (len(present), len(ids), ", ".join(missing))
            + lda_note,
        }
    return {
        "state": "NOT_LANDED",
        "note": (
            "0/%s claimed Commons taking ids are p/{id}.md. Rolling "
            "utilization / grok-capacity-active talk is CLAIMED. Do not "
            "remint. Claim only the verification leftover."
        )
        % len(ids)
        + lda_note,
    }


def measure_from_parts(catalog_text, commons_listing, lda_listing=None):
    """Pure measurer so tests do not need a private repo."""
    catalog = load_catalog(catalog_text)
    ids = list(catalog.get("commons_ids") or [])
    present = present_ids(ids, commons_listing)
    lda_paths = list(catalog.get("lda_claimed_paths") or [])
    lda_measured = lda_listing is not None
    lda_present = present_paths(lda_paths, lda_listing) if lda_measured else []
    return {
        "measured": True,
        "commons_ids": ids,
        "commons_present": present,
        "commons_missing": [item for item in ids if item not in present],
        "commons_present_count": len(present),
        "commons_missing_count": len(ids) - len(present),
        "source_id": catalog.get("source_id") or "",
        "slack_ts": catalog.get("slack_ts") or "",
        "hands_off": list(catalog.get("hands_off") or []),
        "lda_repo": catalog.get("lda_repo") or "",
        "lda_claimed_sha": catalog.get("lda_claimed_sha") or "",
        "lda_claimed_paths": lda_paths,
        "lda_visibility": catalog.get("lda_visibility") or "",
        "lda_measured": lda_measured,
        "lda_present": lda_present,
        "lda_missing": (
            [item for item in lda_paths if item not in lda_present]
            if lda_measured
            else list(lda_paths)
        ),
        "titan": "NOT_WRITTEN",
    }


def measure_paths(catalog_path, posts_dir=None, lda_listing_path=None):
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
    lda_listing = None
    if lda_listing_path:
        listing_path = os.path.abspath(lda_listing_path)
        if os.path.isfile(listing_path):
            with open(listing_path, "r", encoding="utf-8") as handle:
                lda_listing = [
                    line.strip()
                    for line in handle.read().splitlines()
                    if line.strip()
                ]
        else:
            lda_listing = []
    row = measure_from_parts(catalog_text, listing, lda_listing)
    row["catalog"] = path
    if root:
        row["posts_dir"] = root
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Trace claimed TAKING ids against Commons p/{id}.md"
    )
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--posts-dir", default="p", help="optional p/ listing")
    parser.add_argument(
        "--lda-listing",
        default="",
        help="optional path list for private LDA; omit to leave LDA UNMEASURED",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the stdlib fixtures and exit",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return 0 if _self_test() else 1
    row = measure_paths(
        args.catalog, args.posts_dir or None, args.lda_listing or None
    )
    verdict = classify(row)
    payload = dict(row)
    payload.update(verdict)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if row.get("measured") else 2


def _self_test():
    empty = classify({})
    assert empty["state"] == "UNMEASURED"
    none = measure_from_parts('{"commons_ids":[]}', [])
    assert none["commons_ids"] == []
    assert classify(none)["state"] == "NOT_LANDED"
    catalog = json.dumps(
        {
            "source_id": "demon-rolling-utilization-20260825-01",
            "commons_ids": [
                "grok46-revenue-discovery-20260825-01",
                "grok46-open-revenue-desk-20260825-01",
            ],
            "lda": {
                "claimed_paths": ["host/muhl_revenue.py"],
                "visibility": "private",
            },
        }
    )
    missing = measure_from_parts(catalog, ["unrelated.md"])
    assert missing["commons_present_count"] == 0
    assert missing["lda_measured"] is False
    assert classify(missing)["state"] == "NOT_LANDED"
    half = measure_from_parts(
        catalog, ["grok46-revenue-discovery-20260825-01.md"]
    )
    assert half["commons_present"] == ["grok46-revenue-discovery-20260825-01"]
    assert classify(half)["state"] == "CANDIDATE"
    both = measure_from_parts(
        catalog,
        [
            "grok46-revenue-discovery-20260825-01.md",
            "grok46-open-revenue-desk-20260825-01.md",
        ],
        ["host/muhl_revenue.py"],
    )
    assert classify(both)["state"] == "INTEGRATED"
    assert both["titan"] == "NOT_WRITTEN"
    return True


if __name__ == "__main__":
    sys.exit(main())
