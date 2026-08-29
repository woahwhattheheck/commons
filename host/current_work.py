#!/usr/bin/env python3
"""host/current_work.py — unfinished-now ledger.

DIRECTIVES.md OPEN/HALF text is historical. This instrument reads
ground/CURRENT_WORK.json and reconciles live status from a main
snapshot. Chat, Slack, ntfy, and open PRs never close an item.

  python3 host/current_work.py
  python3 host/current_work.py --root .
  python3 host/current_work.py --main-sha <40-hex>
  python3 host/current_work.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "CURRENT_WORK.json")
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
KINDS = ("BUILDABLE", "OWNER_PLATFORM", "DEVICE_PINNED")
SCHEMA = "commons-current-work-v1"
SHIP_LOOP = "gpt-grok-ship-loop.html"
SHIP_SKILL = ".agents/skills/gpt-grok-ship-loop/SKILL.md"


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def load_catalog(text):
    try:
        data = json.loads(str(text or "") or "{}")
    except ValueError:
        return {"error": "catalog is not JSON"}
    if not isinstance(data, dict):
        return {"error": "catalog is not an object"}
    return data


def validate_catalog(data):
    problems = []
    if not isinstance(data, dict):
        return ["catalog is not an object"]
    if data.get("schema") != SCHEMA:
        problems.append("schema must be %s" % SCHEMA)
    add_work = data.get("add_work") or {}
    if add_work.get("preferred") != SHIP_LOOP:
        problems.append("add_work.preferred must be %s" % SHIP_LOOP)
    items = data.get("items")
    if not isinstance(items, list):
        problems.append("items must be a list")
        return problems
    seen = {}
    for item in items:
        problems.extend(validate_item(item, seen))
    historical = data.get("historical_directives") or []
    if not isinstance(historical, list):
        problems.append("historical_directives must be a list")
        return problems
    for row in historical:
        if not isinstance(row, dict):
            problems.append("historical row is not an object")
            continue
        if row.get("current") is not False:
            problems.append("historical_directives must set current=false")
    return problems


def validate_item(item, seen=None):
    problems = []
    if not isinstance(item, dict):
        return ["item is not an object"]
    job_id = str(item.get("id") or "")
    if not ID_RE.match(job_id):
        problems.append("id must match %s" % ID_RE.pattern)
    elif seen is not None:
        blob = json.dumps(item, sort_keys=True, separators=(",", ":"))
        prior = seen.get(job_id)
        if prior is None:
            seen[job_id] = blob
        elif prior != blob:
            problems.append("CONFLICT same id different bytes: %s" % job_id)
    kind = item.get("kind")
    if kind not in KINDS:
        problems.append("kind not in enum")
    title = str(item.get("title") or "")
    if len(title) < 8:
        problems.append("title too short")
    paths = item.get("claimed_paths")
    if paths is None:
        paths = []
    if not isinstance(paths, list) or any(not isinstance(p, str) or not p for p in paths):
        problems.append("claimed_paths must be a list of nonempty strings")
    return problems


def mint_job_id(title, day, n):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(title or "item")).strip("-").lower()
    slug = slug[:32] or "item"
    job_id = "cw-%s-%s-%02d" % (day, slug, int(n))
    if not ID_RE.match(job_id):
        job_id = "cw-%s-item-%02d" % (day, int(n))
    return job_id


def add_item(catalog, item):
    """Append a peer item. Same id + same bytes is idempotent."""
    if not isinstance(catalog, dict):
        return catalog, ["catalog is not an object"]
    items = list(catalog.get("items") or [])
    job_id = str(item.get("id") or "")
    incoming = json.dumps(item, sort_keys=True, separators=(",", ":"))
    for existing in items:
        if str(existing.get("id") or "") != job_id:
            continue
        prior = json.dumps(existing, sort_keys=True, separators=(",", ":"))
        if prior == incoming:
            return catalog, []
        return catalog, ["CONFLICT same id different bytes: %s" % job_id]
    problems = validate_item(item)
    if problems:
        return catalog, problems
    updated = dict(catalog)
    updated["items"] = items + [item]
    return updated, []


def reconcile_item(item, snapshot):
    snapshot = snapshot or {}
    item = item if isinstance(item, dict) else {}
    kind = item.get("kind")
    job_id = str(item.get("id") or "")
    claimed = [p for p in (item.get("claimed_paths") or []) if isinstance(p, str) and p]
    chat_ignored = bool(
        snapshot.get("chat_text")
        or snapshot.get("chat_said_done")
        or snapshot.get("assistant_message")
        or snapshot.get("slack_text")
        or snapshot.get("ntfy_200")
    )
    main_sha = str(snapshot.get("main_sha") or "")
    main_paths = snapshot.get("main_paths") or {}
    if not isinstance(main_paths, dict):
        main_paths = {}
    result = {
        "id": job_id,
        "kind": kind,
        "title": item.get("title"),
        "chat_ignored": chat_ignored,
        "main_sha": "",
        "executable": kind == "BUILDABLE",
        "status": "OPEN",
    }
    if kind == "DEVICE_PINNED":
        result["status"] = "PINNED"
        result["executable"] = False
        result["reason"] = "hazardous device op; not fired from this ledger"
        return result
    if kind == "OWNER_PLATFORM":
        result["executable"] = False
        result["reason"] = "external owner/platform act"
    if snapshot.get("open_prs") and not (
        SHA_RE.match(main_sha) and claimed and all(main_paths.get(p) for p in claimed)
    ):
        result["status"] = "OPEN"
        result["reason"] = result.get("reason") or "open PR is not close evidence"
        return result
    if SHA_RE.match(main_sha) and claimed and all(main_paths.get(p) for p in claimed):
        result["status"] = "CLOSED"
        result["main_sha"] = main_sha
        return result
    if kind == "OWNER_PLATFORM":
        result["status"] = "NEEDS_OWNER"
    else:
        result["status"] = "OPEN"
    return result


def project(catalog, snapshot):
    problems = validate_catalog(catalog)
    items = catalog.get("items") if isinstance(catalog, dict) else []
    if not isinstance(items, list):
        items = []
    live = [reconcile_item(item, snapshot) for item in items if isinstance(item, dict)]
    historical = []
    if isinstance(catalog, dict):
        for row in catalog.get("historical_directives") or []:
            if isinstance(row, dict):
                historical.append({
                    "n": row.get("n"),
                    "title": row.get("title"),
                    "status_in_directives": row.get("status_in_directives"),
                    "current": False,
                })
    open_now = [row for row in live if row.get("status") in ("OPEN", "NEEDS_OWNER", "PINNED")]
    return {
        "schema": SCHEMA,
        "problems": problems,
        "items": live,
        "open_now": open_now,
        "historical_directives": historical,
        "add_work": (catalog or {}).get("add_work") if isinstance(catalog, dict) else {},
        "open_work": {
            "human": "ground/open-work-structured-ids-on-current-main.md",
            "machine": "ground/open-work-structured-ids-on-current-main.json",
            "listing": "ground/open-work-listing",
            "pointer_human": "ground/OPEN_WORK.md",
            "instrument": "host/open_work.py",
            "schema": "commons-open-work-v1",
            "note": "sibling projector of structured work-order ids on this board. Not a second queue. Slack CLAIMED is not a land. Title-filenames on new outputs only; existing p/ slugs stay.",
        },
    }


def measure_tree(root, main_sha=""):
    catalog = load_catalog(_read(root, DEFAULT_CATALOG))
    if catalog.get("error"):
        return {"error": catalog["error"], "open_now": [], "items": []}
    snapshot = {"main_paths": {}, "main_sha": str(main_sha or "")}
    for item in catalog.get("items") or []:
        for path in item.get("claimed_paths") or []:
            snapshot["main_paths"][path] = os.path.exists(os.path.join(root, path))
    return project(catalog, snapshot)


def self_test():
    sample = {
        "schema": SCHEMA,
        "add_work": {"preferred": SHIP_LOOP, "skill": SHIP_SKILL},
        "historical_directives": [
            {"n": 19, "title": "Agent Swarm (Datacenter Workload)", "status_in_directives": "OPEN", "current": False}
        ],
        "items": [
            {
                "id": "current-work-ledger-20260828-01",
                "title": "One trustworthy current-work ledger",
                "kind": "BUILDABLE",
                "claimed_paths": ["ground/CURRENT_WORK.json"],
            }
        ],
    }
    assert validate_catalog(sample) == []
    queued = reconcile_item(sample["items"][0], {})
    assert queued["status"] == "OPEN"
    chatter = reconcile_item(sample["items"][0], {"chat_said_done": True, "ntfy_200": True, "slack_text": "done"})
    assert chatter["status"] == "OPEN"
    assert chatter["chat_ignored"] is True
    sha = "a" * 40
    closed = reconcile_item(sample["items"][0], {"main_sha": sha, "main_paths": {"ground/CURRENT_WORK.json": True}})
    assert closed["status"] == "CLOSED"
    assert closed["main_sha"] == sha
    short = reconcile_item(sample["items"][0], {"main_sha": "abc1234", "main_paths": {"ground/CURRENT_WORK.json": True}})
    assert short["status"] == "OPEN"
    pinned = reconcile_item(
        {"id": "device-pin-no-fire-20260828-01", "title": "Do not fire devices", "kind": "DEVICE_PINNED", "claimed_paths": []},
        {"main_sha": sha, "chat_said_done": True},
    )
    assert pinned["status"] == "PINNED"
    assert pinned["executable"] is False
    live = project(sample, {})
    assert live["historical_directives"][0]["current"] is False
    print("self-test ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Unfinished-now ledger")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--main-sha", default="", help="official 40-character main SHA")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    out = measure_tree(args.root, args.main_sha)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 1 if out.get("error") or out.get("problems") else 0


if __name__ == "__main__":
    sys.exit(main())
