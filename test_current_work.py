#!/usr/bin/env python3
"""Current-work ledger: close only from 40-char main SHA + claimed paths."""
from __future__ import annotations

import json
import os
import sys
import tempfile

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

    closed_with_unrelated_pr = cw.reconcile_item(
        item,
        {
            "open_prs": [999999],
            "main_sha": sha,
            "main_paths": {p: True for p in claimed},
        },
    )
    check(
        "unrelated open PR does not block main evidence",
        closed_with_unrelated_pr["status"] == "CLOSED"
        and closed_with_unrelated_pr["main_sha"] == sha,
        closed_with_unrelated_pr,
    )

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


def test_malformed_catalog_is_reported_not_crashed():
    with tempfile.TemporaryDirectory() as root:
        ground = os.path.join(root, "ground")
        os.makedirs(ground)
        catalog = {
            "schema": cw.SCHEMA,
            "add_work": {"preferred": cw.SHIP_LOOP},
            "historical_directives": [],
            "items": [
                "not-an-object",
                {
                    "id": "malformed-item-20260830-01",
                    "title": "Malformed claimed paths",
                    "kind": "BUILDABLE",
                    "claimed_paths": 7,
                },
            ],
        }
        with open(os.path.join(ground, "CURRENT_WORK.json"), "w", encoding="utf-8") as handle:
            json.dump(catalog, handle)
        measured = cw.measure_tree(root)
        check("malformed catalog returns problems", bool(measured.get("problems")), measured)
        check(
            "malformed catalog does not fabricate closure",
            all(row.get("status") != "CLOSED" for row in measured.get("items") or []),
            measured,
        )
        check("malformed catalog has no crash keys", "error" not in measured or measured.get("error") != "crash", measured)


def test_non_list_items_and_claimed_paths_do_not_abort():
    with tempfile.TemporaryDirectory() as root:
        ground = os.path.join(root, "ground")
        os.makedirs(ground)
        for payload in (
            {"schema": cw.SCHEMA, "add_work": {"preferred": cw.SHIP_LOOP}, "items": {"id": "dict-not-list"}},
            {"schema": cw.SCHEMA, "add_work": {"preferred": cw.SHIP_LOOP}, "items": "string-items"},
        ):
            with open(os.path.join(ground, "CURRENT_WORK.json"), "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            measured = cw.measure_tree(root)
            check("non-list items report problems", bool(measured.get("problems")), measured)
            check("non-list items stay a dict report", isinstance(measured, dict), measured)


def main():
    test_self_and_catalog()
    test_close_rule()
    test_conflict_same_id()
    test_malformed_catalog_is_reported_not_crashed()
    test_non_list_items_and_claimed_paths_do_not_abort()
    if FAILED:
        print("CURRENT WORK TEST: FAIL", len(FAILED), ":", ", ".join(FAILED))
        return 1
    print("CURRENT WORK TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
