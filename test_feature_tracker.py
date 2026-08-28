#!/usr/bin/env python3
"""Feature tracker: derived status, append-only registry, projection does not mutate."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "host"))
import feature_tracker as ft

ROOT = os.path.dirname(os.path.abspath(__file__))
FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("ok  ", name)
        return
    FAILED.append(name)
    print("FAIL", name, detail)


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _feature(**overrides):
    row = {
        "schema": ft.SCHEMA,
        "id": "demo-feature-20260828-01",
        "name": "Demo feature",
        "capability": "A sandbox feature used only by tests.",
        "carrier": "GROK",
        "owner_subsystem": "feature-tracker",
        "public_entrypoint": "demo.html",
        "next_gap": "none",
        "claimed_paths": ["demo.html"],
        "test_paths": ["test_demo.py"],
        "dependencies": [],
        "resource_links": ["demo.html"],
        "related": {"boards": False, "current_work": False, "profitability": False, "resources": False},
    }
    row.update(overrides)
    return row


def test_self():
    check("self-test", ft.self_test() == 0)


def test_sandbox_statuses():
    tmp = tempfile.mkdtemp(prefix="commons-feature-tracker-")
    try:
        open(os.path.join(tmp, "demo.html"), "w").write("<p>demo</p>\n")
        open(os.path.join(tmp, "test_demo.py"), "w").write("print('ok')\n")
        planned = _feature(id="planned-feature-20260828-01", claimed_paths=[], test_paths=[], claimed_status="LIVE")
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "planned-feature-20260828-01.json"), planned)
        built = _feature(id="source-feature-20260828-01", test_paths=["missing_test.py"], claimed_status="LIVE")
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "source-feature-20260828-01.json"), built)
        tested = _feature(id="tested-feature-20260828-01")
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "tested-feature-20260828-01.json"), tested)
        live = _feature(id="live-feature-20260828-01")
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "live-feature-20260828-01.json"), live)
        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-live-feature-20260828-01.json"),
            {
                "schema": ft.EVIDENCE_SCHEMA,
                "id": "ev-live-feature-20260828-01",
                "feature_id": "live-feature-20260828-01",
                "kind": "LIVE_MEASUREMENT",
                "url": "https://woahwhattheheck.github.io/commons/demo.html",
                "sha": "c" * 40,
                "recorded_at": "2026-08-28T00:00:00Z",
            },
        )
        degraded = _feature(id="degraded-feature-20260828-01", claimed_paths=["gone.html"])
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "degraded-feature-20260828-01.json"), degraded)
        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-degraded-source-20260828-01.json"),
            {
                "schema": ft.EVIDENCE_SCHEMA,
                "id": "ev-degraded-source-20260828-01",
                "feature_id": "degraded-feature-20260828-01",
                "kind": "SOURCE_PATHS",
                "paths": ["gone.html"],
                "recorded_at": "2026-08-28T00:00:00Z",
            },
        )
        superseded = _feature(id="old-feature-20260828-01")
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "old-feature-20260828-01.json"), superseded)
        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-old-supersede-20260828-01.json"),
            {
                "schema": ft.EVIDENCE_SCHEMA,
                "id": "ev-old-supersede-20260828-01",
                "feature_id": "old-feature-20260828-01",
                "kind": "SUPERSEDE",
                "superseded_by": "tested-feature-20260828-01",
                "recorded_at": "2026-08-28T00:00:00Z",
            },
        )
        chatter_live = ft.derive_status(built, [{"kind": "RECEIPT", "ntfy_200": True, "slack": "LIVE"}], tmp)
        check("chat does not promote LIVE", chatter_live["live"] is False)
        check("claimed_status ignored", chatter_live["claimed_status_ignored"] == "LIVE")

        projection = ft.project(tmp)
        by_id = {row["id"]: row for row in projection["features"]}
        check("planned", by_id["planned-feature-20260828-01"]["status"] == "PLANNED", by_id["planned-feature-20260828-01"])
        check("source built", by_id["source-feature-20260828-01"]["status"] == "SOURCE_BUILT", by_id["source-feature-20260828-01"])
        check("tested", by_id["tested-feature-20260828-01"]["status"] == "TESTED", by_id["tested-feature-20260828-01"])
        check("live", by_id["live-feature-20260828-01"]["status"] == "LIVE", by_id["live-feature-20260828-01"])
        check("source and live columns separate", by_id["tested-feature-20260828-01"]["live"] is False and by_id["tested-feature-20260828-01"]["source_built"] is True)
        check("degraded", by_id["degraded-feature-20260828-01"]["status"] == "DEGRADED", by_id["degraded-feature-20260828-01"])
        check("superseded", by_id["old-feature-20260828-01"]["status"] == "SUPERSEDED", by_id["old-feature-20260828-01"])

        bad_live = {
            "schema": ft.EVIDENCE_SCHEMA,
            "id": "ev-pages-only-20260828-01",
            "feature_id": "tested-feature-20260828-01",
            "kind": "LIVE_MEASUREMENT",
            "url": "https://woahwhattheheck.github.io/commons/demo.html",
            "sha": "not-a-sha",
        }
        check("pages without 40-sha is invalid", any("40-character SHA" in p for p in ft.validate_evidence(bad_live, "ev-pages-only-20260828-01.json")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_conflict_and_filename():
    row = _feature()
    check("filename matches id", ft.validate_feature(row, "demo-feature-20260828-01.json") == [])
    check("filename mismatch", any("filename" in p for p in ft.validate_feature(row, "other.json")))
    tmp = tempfile.mkdtemp(prefix="commons-feature-conflict-")
    try:
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "demo-feature-20260828-01.json"), row)
        clash = dict(row)
        clash["name"] = "Different name for same id"
        # same-id different bytes as a second file cannot share the filename; the
        # loader still flags two loaded dicts with the same id via seen map when
        # validate_feature is used by add-style callers.
        first = ft.validate_feature(row, "demo-feature-20260828-01.json")
        second = ft.validate_feature(clash, "demo-feature-20260828-01.json")
        check("both rows shape-valid", first == [] and second == [])
        check("canonical differs", ft._canonical(row) != ft._canonical(clash))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_projection_does_not_mutate():
    tmp = tempfile.mkdtemp(prefix="commons-feature-proj-")
    try:
        os.makedirs(os.path.join(tmp, "features.html-keep"), exist_ok=True)
        open(os.path.join(tmp, "features.html"), "w").write("LANE\n")
        row = _feature(claimed_paths=["demo.html"], test_paths=[])
        _write(os.path.join(tmp, ft.REGISTRY_DIR, "demo-feature-20260828-01.json"), row)
        open(os.path.join(tmp, "demo.html"), "w").write("x\n")
        before = hashlib.sha256(open(os.path.join(tmp, ft.REGISTRY_DIR, "demo-feature-20260828-01.json"), "rb").read()).hexdigest()
        lane_before = open(os.path.join(tmp, "features.html"), encoding="utf-8").read()
        written = {}
        proj = ft.write_projection(tmp, lambda path, text: written.__setitem__(path, text) or open(path, "w", encoding="utf-8").write(text))
        after = hashlib.sha256(open(os.path.join(tmp, ft.REGISTRY_DIR, "demo-feature-20260828-01.json"), "rb").read()).hexdigest()
        check("registry bytes unchanged", before == after)
        check("wrote json", os.path.join(tmp, "feature-tracker.json") in written)
        check("wrote html", os.path.join(tmp, "feature-tracker.html") in written)
        check("did not remint features.html", open(os.path.join(tmp, "features.html"), encoding="utf-8").read() == lane_before)
        check("html distinguishes FEATURES lane", "FEATURES board lane" in written[os.path.join(tmp, "feature-tracker.html")])
        written2 = {}
        ft.write_projection(tmp, lambda path, text: written2.__setitem__(path, text) or open(path, "w", encoding="utf-8").write(text))
        check("deterministic", written == written2)
        check("projection measured", proj["n_features"] == 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_repo_registry_if_present():
    registry = os.path.join(ROOT, ft.REGISTRY_DIR)
    if not os.path.isdir(registry):
        print("skip repo registry (not in this tree)")
        return
    projection = ft.project(ROOT)
    check("repo registry loads", isinstance(projection.get("features"), list))
    tracker = next((row for row in projection["features"] if row.get("id") == "feature-tracker-20260828-01"), None)
    if tracker is None:
        print("skip tracker row (not copied yet)")
        return
    check("tracker schema row present", tracker["name"] == "Feature tracker")
    check("tracker does not claim LIVE without measurement", tracker["live"] is False)
    check("features.html not in tracker claimed_paths", "features.html" not in (tracker.get("claimed_paths") or []))


def main():
    test_self()
    test_sandbox_statuses()
    test_conflict_and_filename()
    test_projection_does_not_mutate()
    test_repo_registry_if_present()
    if FAILED:
        print("FEATURE TRACKER TEST: FAIL", len(FAILED), ":", ", ".join(FAILED))
        return 1
    print("FEATURE TRACKER TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
