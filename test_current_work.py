#!/usr/bin/env python3
"""Current-work ledger: close only from 40-char main SHA + claimed paths."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "host"))
import current_work as cw

ROOT = os.path.dirname(os.path.abspath(__file__))
FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("ok  ", name)
        return
    FAILED.append(name)
    print("FAIL", name, detail)


def test_self_and_catalog():
    check("self-test", cw.self_test() == 0)
    catalog = cw.load_catalog(cw._read(ROOT, cw.DEFAULT_CATALOG))
    check("catalog loads", "error" not in catalog, catalog)
    problems = cw.validate_catalog(catalog)
    check("catalog valid", problems == [], problems)
    check("schema", catalog.get("schema") == cw.SCHEMA)
    check("add_work preferred ship-loop", (catalog.get("add_work") or {}).get("preferred") == cw.SHIP_LOOP)
    historical = catalog.get("historical_directives") or []
    check("historical rows", isinstance(historical, list) and historical)
    check("historical current=false", all(row.get("current") is False for row in historical if isinstance(row, dict)))


def test_close_rule():
    catalog = cw.load_catalog(cw._read(ROOT, cw.DEFAULT_CATALOG))
    item = None
    pin = None
    for row in catalog.get("items") or []:
        if row.get("id") == "current-work-ledger-20260828-01":
            item = row
        if row.get("kind") == "DEVICE_PINNED":
            pin = row
    check("ledger item present", isinstance(item, dict))
    claimed = list(item.get("claimed_paths") or [])
    check("claimed paths nonempty", bool(claimed))
    for path in claimed:
        check("claimed exists %s" % path, os.path.isfile(os.path.join(ROOT, path)))

    queued = cw.reconcile_item(item, {})
    check("no snapshot stays OPEN", queued["status"] == "OPEN")

    chat = cw.reconcile_item(item, {"chat_text": "done", "chat_said_done": True, "slack_text": "landed", "ntfy_200": True})
    check("chat ignored", chat["chat_ignored"] is True)
    check("chat does not close", chat["status"] == "OPEN")

    open_pr = cw.reconcile_item(item, {"open_prs": [4889], "main_sha": "deadbeef"})
    check("open PR is not close", open_pr["status"] == "OPEN")

    short_sha = cw.reconcile_item(item, {"main_sha": "abc", "main_paths": {p: True for p in claimed}})
    check("short SHA does not close", short_sha["status"] == "OPEN")

    sha = "c" * 40
    closed = cw.reconcile_item(item, {"main_sha": sha, "main_paths": {p: True for p in claimed}})
    check("40-char SHA + claimed closes", closed["status"] == "CLOSED" and closed["main_sha"] == sha, closed)

    missing = dict((p, True) for p in claimed)
    if claimed:
        missing[claimed[0]] = False
    still_open = cw.reconcile_item(item, {"main_sha": sha, "main_paths": missing})
    check("missing claimed path stays OPEN", still_open["status"] == "OPEN")

    check("device pin present", isinstance(pin, dict))
    pinned = cw.reconcile_item(pin, {"main_sha": sha, "main_paths": {p: True for p in claimed}, "chat_said_done": True})
    check("DEVICE_PINNED stays PINNED", pinned["status"] == "PINNED")
    check("DEVICE_PINNED not executable", pinned["executable"] is False)


def test_conflict_same_id():
    catalog = cw.load_catalog(cw._read(ROOT, cw.DEFAULT_CATALOG))
    item = (catalog.get("items") or [None])[0]
    updated, problems = cw.add_item(catalog, item)
    check("same id same bytes idempotent", problems == [])
    clash = dict(item)
    clash["title"] = "Different title for same id 1234"
    _, problems = cw.add_item(catalog, clash)
    check("same id different bytes CONFLICT", any("CONFLICT" in p for p in problems), problems)


def main():
    test_self_and_catalog()
    test_close_rule()
    test_conflict_same_id()
    if FAILED:
        print("CURRENT WORK TEST: FAIL", len(FAILED), ":", ", ".join(FAILED))
        return 1
    print("CURRENT WORK TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
