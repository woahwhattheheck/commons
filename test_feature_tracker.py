#!/usr/bin/env python3
"""Feature tracker: evidence-derived status, append-only, no prose promotion."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(ft._sorted_json(data) if not isinstance(data, str) else data)


def _sample_feature(**kwargs):
    rec = {
        "schema": ft.SCHEMA_FEATURE,
        "id": "sample-feature-20260828-01",
        "name": "Sample feature",
        "capability": "Does one exact thing with evidence.",
        "owner_subsystem": "sample",
        "carrier": "GROK",
        "claimed_paths": [],
        "test_paths": [],
        "public_entrypoint": "",
        "dependencies": [],
        "resource_links": [],
        "next_gap": "Name the next highest-value gap in eight+ characters.",
    }
    rec.update(kwargs)
    return rec


def test_self_test():
    check("self-test", ft.self_test() == 0)


def test_schema_and_conflict():
    check("feature missing id", any("id" in p for p in ft.validate_feature({"schema": ft.SCHEMA_FEATURE})))
    good = _sample_feature()
    check("feature shape", ft.validate_feature(good, "sample-feature-20260828-01.json") == [], ft.validate_feature(good, "sample-feature-20260828-01.json"))
    check("filename must match id", any("filename" in p for p in ft.validate_feature(good, "other.json")))
    evid = {
        "schema": ft.SCHEMA_EVIDENCE,
        "id": "ev-sample-20260828-01",
        "feature_id": "sample-feature-20260828-01",
        "kind": "RECEIPT",
        "receipt": "sample-feature-20260828-01",
    }
    check("evidence shape", ft.validate_evidence(evid, "ev-sample-20260828-01.json") == [])
    live_bad = dict(evid, id="ev-live-bad-20260828-01", kind="LIVE_MEASUREMENT")
    probs = ft.validate_evidence(live_bad, "ev-live-bad-20260828-01.json")
    check("LIVE_MEASUREMENT needs url+sha", any("url" in p or "sha" in p for p in probs), probs)


def test_derivation_and_no_prose_promotion():
    tmp = tempfile.mkdtemp(prefix="commons-ft-test-")
    try:
        os.makedirs(os.path.join(tmp, "src"))
        with open(os.path.join(tmp, "src", "door.py"), "w", encoding="utf-8") as handle:
            handle.write("x=1\n")
        with open(os.path.join(tmp, "test_door.py"), "w", encoding="utf-8") as handle:
            handle.write("assert True\n")
        _write(
            os.path.join(tmp, ft.REGISTRY_DIR, "alpha-feature-20260828-01.json"),
            _sample_feature(
                id="alpha-feature-20260828-01",
                name="Alpha door",
                claimed_paths=["src/door.py"],
                test_paths=["test_door.py"],
                public_entrypoint="src/door.py",
                claimed_status="LIVE",
            ),
        )
        _write(
            os.path.join(tmp, ft.REGISTRY_DIR, "beta-planned-20260828-01.json"),
            _sample_feature(id="beta-planned-20260828-01", name="Beta planned"),
        )
        proj = ft.project(tmp, {"chat_said_done": True, "ntfy_200": True, "open_prs": [9], "slack_text": "shipped"})
        by_id = {row["id"]: row for row in proj["features"]}
        alpha = by_id["alpha-feature-20260828-01"]
        check("chat ignored", alpha["chat_ignored"] is True)
        check("claimed LIVE ignored", alpha["author_claim_ignored"] == "LIVE")
        check("no live without measurement", alpha["live_status"] == "UNMEASURED")
        check("source built from paths", alpha["source_status"] == "SOURCE_BUILT")
        check("tested from test paths", alpha["test_status"] == "TESTED")
        check("rollup tested not live", alpha["rollup"] == "TESTED")
        check("planned empty paths", by_id["beta-planned-20260828-01"]["rollup"] == "PLANNED")

        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-alpha-live-20260828-01.json"),
            {
                "schema": ft.SCHEMA_EVIDENCE,
                "id": "ev-alpha-live-20260828-01",
                "feature_id": "alpha-feature-20260828-01",
                "kind": "LIVE_MEASUREMENT",
                "sha": "b" * 40,
                "url": "https://woahwhattheheck.github.io/commons/src/door.py",
                "recorded_at": "2026-08-28T12:00:00Z",
            },
        )
        live = {row["id"]: row for row in ft.project(tmp)["features"]}["alpha-feature-20260828-01"]
        check("live only after measurement", live["live_status"] == "LIVE" and live["rollup"] == "LIVE", live)

        door_path = os.path.join(tmp, "src", "door.py")
        current_blob = subprocess.check_output(["git", "hash-object", door_path], text=True).strip()
        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-alpha-live-stale-20260828-01.json"),
            {
                "schema": ft.SCHEMA_EVIDENCE,
                "id": "ev-alpha-live-stale-20260828-01",
                "feature_id": "alpha-feature-20260828-01",
                "kind": "LIVE_MEASUREMENT",
                "sha": "c" * 40,
                "blob": "d" * 40,
                "path": "src/door.py",
                "url": "https://woahwhattheheck.github.io/commons/src/door.py",
                "recorded_at": "2026-08-28T12:05:00Z",
            },
        )
        stale = {row["id"]: row for row in ft.project(tmp)["features"]}["alpha-feature-20260828-01"]
        check("stale blob does not unseat a matching live pin", stale["live_status"] == "LIVE", stale)

        os.remove(os.path.join(tmp, ft.EVIDENCE_DIR, "ev-alpha-live-20260828-01.json"))
        only_stale = {row["id"]: row for row in ft.project(tmp)["features"]}["alpha-feature-20260828-01"]
        check("stale-only live is degraded", only_stale["live_status"] == "DEGRADED" and only_stale["rollup"] == "DEGRADED", only_stale)

        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-alpha-live-fresh-20260828-01.json"),
            {
                "schema": ft.SCHEMA_EVIDENCE,
                "id": "ev-alpha-live-fresh-20260828-01",
                "feature_id": "alpha-feature-20260828-01",
                "kind": "LIVE_MEASUREMENT",
                "sha": "e" * 40,
                "blob": current_blob,
                "path": "src/door.py",
                "url": "https://raw.githubusercontent.com/woahwhattheheck/commons/" + ("e" * 40) + "/src/door.py",
                "recorded_at": "2026-08-28T12:10:00Z",
            },
        )
        fresh = {row["id"]: row for row in ft.project(tmp)["features"]}["alpha-feature-20260828-01"]
        check("matching blob live pin restores LIVE", fresh["live_status"] == "LIVE" and fresh["main_sha"] == "e" * 40, fresh)

        _write(
            os.path.join(tmp, ft.REGISTRY_DIR, "gone-feature-20260828-01.json"),
            _sample_feature(
                id="gone-feature-20260828-01",
                name="Gone paths",
                claimed_paths=["missing.py"],
            ),
        )
        gone = {row["id"]: row for row in ft.project(tmp)["features"]}["gone-feature-20260828-01"]
        check("missing claimed path is degraded", gone["source_status"] == "DEGRADED" and gone["rollup"] == "DEGRADED", gone)

        _write(
            os.path.join(tmp, ft.EVIDENCE_DIR, "ev-alpha-supersede-20260828-01.json"),
            {
                "schema": ft.SCHEMA_EVIDENCE,
                "id": "ev-alpha-supersede-20260828-01",
                "feature_id": "alpha-feature-20260828-01",
                "kind": "SUPERSEDE",
                "superseded_by": "beta-planned-20260828-01",
                "recorded_at": "2026-08-28T13:00:00Z",
            },
        )
        sup = {row["id"]: row for row in ft.project(tmp)["features"]}["alpha-feature-20260828-01"]
        check("supersede wins rollup", sup["rollup"] == "SUPERSEDED", sup)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_append_only_and_deterministic():
    tmp = tempfile.mkdtemp(prefix="commons-ft-det-")
    try:
        rec = _sample_feature()
        path = os.path.join(tmp, ft.REGISTRY_DIR, rec["id"] + ".json")
        _write(path, rec)
        before = hashlib.sha256(open(path, "rb").read()).hexdigest()
        proj1 = ft.project(tmp)
        ft.write_projection(tmp, proj1)
        proj2 = ft.project(tmp)
        ft.write_projection(tmp, proj2)
        after = hashlib.sha256(open(path, "rb").read()).hexdigest()
        check("projection does not mutate registry", before == after)
        check("projection deterministic", ft._sorted_json(proj1) == ft._sorted_json(proj2))
        page = open(os.path.join(tmp, ft.HTML_OUT), encoding="utf-8").read()
        machine = open(os.path.join(tmp, ft.JSON_OUT), encoding="utf-8").read()
        check("html has search", 'id="ft-q"' in page)
        check("html has status filter", 'id="ft-st"' in page)
        check("html has source filter", 'id="ft-src"' in page)
        check("html has live filter", 'id="ft-lv"' in page)
        check("html links current-work", "current-work.html" in page)
        check("html links resources", "resources.html" in page)
        check("html links profitability", "PROFITABILITY_BUILD_MAP.md" in page)
        check("html links boards", "boards.html" in page)
        check("html does not remint features lane as tracker", "FEATURES board lane" in page)
        check("html no login gate", "login" not in page.lower())
        check("json schema", json.loads(machine)["schema"] == ft.SCHEMA_PROJECTION)
        dup = os.path.join(tmp, ft.REGISTRY_DIR, "copy-feature-20260828-01.json")
        clash = dict(rec, name="Different name for same id xx")
        # same filename would overwrite; conflict is same id in two files
        _write(os.path.join(tmp, ft.REGISTRY_DIR, rec["id"] + "-clash.json"), dict(clash, id=rec["id"]))
        conflicted = ft.project(tmp)
        check("same id different bytes CONFLICT", any("CONFLICT" in p for p in conflicted["problems"]), conflicted["problems"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_live_tree_shape_and_golden():
    if not os.path.isdir(os.path.join(ROOT, ft.REGISTRY_DIR)):
        check("live registry present", False, "missing features/registry")
        return
    features, evidence, conflicts, invalid = ft.load_registry(ROOT)
    check("no load conflicts", conflicts == [], conflicts)
    live_invalid = [rec for rec in features + evidence if rec.get("_invalid") and "duplicate identical" not in " ".join(rec.get("_invalid") or [])]
    check("live records shape-valid", live_invalid == [], [rec.get("_file") for rec in live_invalid])
    proj = ft.project(ROOT)
    check("live projection schema", proj.get("schema") == ft.SCHEMA_PROJECTION)
    check("at least one feature", proj.get("n_features", 0) >= 1, proj.get("n_features"))
    tracker = None
    for row in proj.get("features") or []:
        if row.get("id") == "feature-tracker-20260828-01":
            tracker = row
        check("no live without measurement unless evidence", row["live_status"] in ft.LIVE_STATUSES)
        if row.get("live_status") == "LIVE":
            check("live row cites sha", bool(row.get("main_sha")))
        if row.get("author_claim_ignored"):
            check("author claim not copied to live %s" % row["id"], row["live_status"] != row["author_claim_ignored"])
    check("tracker row present", isinstance(tracker, dict))
    if tracker:
        check("tracker source built", tracker["source_status"] == "SOURCE_BUILT", tracker)
        check("tracker tests present", tracker["test_status"] == "TESTED", tracker)
        check("tracker live unmeasured until Pages evidence", tracker["live_status"] == "UNMEASURED", tracker)
    order = {key: idx for idx, key in enumerate(ft.ROLLUP_SORT)}
    pairs = [(row.get("rollup"), row.get("id")) for row in proj.get("features") or []]
    expected = sorted(pairs, key=lambda item: (order.get(item[0], 99), str(item[1] or "")))
    check("rollup then id sort", pairs == expected, pairs)
    by_id = {row["id"]: row for row in proj.get("features") or []}
    check("listing-registry row", "listing-registry-20260828-01" in by_id, sorted(by_id))
    check("payment-capability row", "payment-capability-20260828-01" in by_id, sorted(by_id))
    check(
        "payment-capability-hub-failover row",
        "payment-capability-hub-failover-20260828-02" in by_id,
        sorted(by_id),
    )
    if "listing-registry-20260828-01" in by_id:
        check("listing live unmeasured", by_id["listing-registry-20260828-01"]["live_status"] == "UNMEASURED")
    if "payment-capability-20260828-01" in by_id:
        check("payment live unmeasured", by_id["payment-capability-20260828-01"]["live_status"] == "UNMEASURED")
    if "payment-capability-hub-failover-20260828-02" in by_id:
        check(
            "hub-failover live unmeasured",
            by_id["payment-capability-hub-failover-20260828-02"]["live_status"] == "UNMEASURED",
        )
        check(
            "hub-failover tested",
            by_id["payment-capability-hub-failover-20260828-02"]["test_status"] == "TESTED",
        )
    check("arbitrage row", "arbitrage-opportunity-road-20260830-01" in by_id, sorted(by_id))
    check("data-license row", "unique-data-license-door-20260830-01" in by_id, sorted(by_id))
    if "arbitrage-opportunity-road-20260830-01" in by_id:
        arb = by_id["arbitrage-opportunity-road-20260830-01"]
        check("arbitrage source built", arb["source_status"] == "SOURCE_BUILT", arb)
        check("arbitrage tested", arb["test_status"] == "TESTED", arb)
        check("arbitrage live measured", arb["live_status"] == "LIVE" and arb["rollup"] == "LIVE", arb)
        check("arbitrage live cites sha", bool(arb.get("main_sha")), arb)
        check("arbitrage does not claim commerce.html", "commerce.html" not in arb["claimed_paths"], arb)
    if "unique-data-license-door-20260830-01" in by_id:
        data = by_id["unique-data-license-door-20260830-01"]
        check("data-license source built", data["source_status"] == "SOURCE_BUILT", data)
        check("data-license tested", data["test_status"] == "TESTED", data)
        check("data-license live measured", data["live_status"] == "LIVE" and data["rollup"] == "LIVE", data)
        check("data-license live cites sha", bool(data.get("main_sha")), data)
        check("data-license does not claim commerce.html", "commerce.html" not in data["claimed_paths"], data)
        check(
            "data-license live blob matches tree",
            ft.tree_blob(ROOT, "data-license.html") in " ".join(data.get("blob_proof") or []),
            data.get("blob_proof"),
        )
    if "arbitrage-opportunity-road-20260830-01" in by_id:
        arb_blob = ft.tree_blob(ROOT, "arbitrage.html")
        check(
            "arbitrage live blob matches tree",
            arb_blob and arb_blob in " ".join(by_id["arbitrage-opportunity-road-20260830-01"].get("blob_proof") or []),
            (arb_blob, by_id["arbitrage-opportunity-road-20260830-01"].get("blob_proof")),
        )
        check(
            "arbitrage live sha is not the stale first pin when a fresh pin exists",
            by_id["arbitrage-opportunity-road-20260830-01"].get("main_sha") != "1d1b29374c131eacb900dca01b2725a138addb92",
            by_id["arbitrage-opportunity-road-20260830-01"].get("main_sha"),
        )
    check("unbuilt-items row", "unbuilt-items-surface-20260830-01" in by_id, sorted(by_id))
    if "unbuilt-items-surface-20260830-01" in by_id:
        ub = by_id["unbuilt-items-surface-20260830-01"]
        check("unbuilt-items source built", ub["source_status"] == "SOURCE_BUILT", ub)
        check("unbuilt-items tested", ub["test_status"] == "TESTED", ub)
        check("unbuilt-items live measured", ub["live_status"] == "LIVE" and ub["rollup"] == "LIVE", ub)
        check("unbuilt-items does not claim hub_pages", "hub_pages.py" not in ub["claimed_paths"], ub)
        ub_blob = ft.tree_blob(ROOT, "unbuilt-items.html")
        check(
            "unbuilt-items live blob matches tree",
            ub_blob and ub_blob in " ".join(ub.get("blob_proof") or []),
            (ub_blob, ub.get("blob_proof")),
        )
    check("website-people-email-book row", "website-people-email-book-20260830-01" in by_id, sorted(by_id))
    if "website-people-email-book-20260830-01" in by_id:
        loop = by_id["website-people-email-book-20260830-01"]
        check("website-people-email-book source built", loop["source_status"] == "SOURCE_BUILT", loop)
        check("website-people-email-book tested", loop["test_status"] == "TESTED", loop)
        check("website-people-email-book live unmeasured", loop["live_status"] == "UNMEASURED", loop)
        check("website-people-email-book rollup tested", loop["rollup"] == "TESTED", loop)
        check(
            "website-people-email-book door is the public entry",
            loop.get("public_entrypoint") == "website-people-email-book.html",
            loop.get("public_entrypoint"),
        )
    check("lm-gtm-index row", "lm-gtm-index-20260831-01" in by_id, sorted(by_id))
    if "lm-gtm-index-20260831-01" in by_id:
        gtm = by_id["lm-gtm-index-20260831-01"]
        check("lm-gtm-index source built", gtm["source_status"] == "SOURCE_BUILT", gtm)
        check("lm-gtm-index tested", gtm["test_status"] == "TESTED", gtm)
        check("lm-gtm-index live unmeasured", gtm["live_status"] == "UNMEASURED", gtm)
        check("lm-gtm-index rollup tested", gtm["rollup"] == "TESTED", gtm)
        check(
            "lm-gtm-index door is the public entry",
            gtm.get("public_entrypoint") == "lm-gtm-index.html",
            gtm.get("public_entrypoint"),
        )
    check("lm-gtm-hot-lane row", "lm-gtm-hot-lane-20260831-01" in by_id, sorted(by_id))
    if "lm-gtm-hot-lane-20260831-01" in by_id:
        hot = by_id["lm-gtm-hot-lane-20260831-01"]
        check("lm-gtm-hot-lane source built", hot["source_status"] == "SOURCE_BUILT", hot)
        check("lm-gtm-hot-lane tested", hot["test_status"] == "TESTED", hot)
        check("lm-gtm-hot-lane live unmeasured", hot["live_status"] == "UNMEASURED", hot)
        check("lm-gtm-hot-lane rollup tested", hot["rollup"] == "TESTED", hot)
        check(
            "lm-gtm-hot-lane door is the public entry",
            hot.get("public_entrypoint") == "lm-gtm-index.html",
            hot.get("public_entrypoint"),
        )
    check("lm-gtm-floor-sync row", "lm-gtm-floor-sync-20260831-01" in by_id, sorted(by_id))
    if "lm-gtm-floor-sync-20260831-01" in by_id:
        sync = by_id["lm-gtm-floor-sync-20260831-01"]
        check("lm-gtm-floor-sync source built", sync["source_status"] == "SOURCE_BUILT", sync)
        check("lm-gtm-floor-sync tested", sync["test_status"] == "TESTED", sync)
        check("lm-gtm-floor-sync live unmeasured", sync["live_status"] == "UNMEASURED", sync)
        check("lm-gtm-floor-sync rollup tested", sync["rollup"] == "TESTED", sync)
        check(
            "lm-gtm-floor-sync door is the public entry",
            sync.get("public_entrypoint") == "lm-gtm-index.html",
            sync.get("public_entrypoint"),
        )
    check("lm-gtm-agent-brief row", "lm-gtm-agent-brief-20260831-01" in by_id, sorted(by_id))
    if "lm-gtm-agent-brief-20260831-01" in by_id:
        brief = by_id["lm-gtm-agent-brief-20260831-01"]
        check("lm-gtm-agent-brief source built", brief["source_status"] == "SOURCE_BUILT", brief)
        check("lm-gtm-agent-brief tested", brief["test_status"] == "TESTED", brief)
        check("lm-gtm-agent-brief live unmeasured", brief["live_status"] == "UNMEASURED", brief)
        check("lm-gtm-agent-brief rollup tested", brief["rollup"] == "TESTED", brief)
        check(
            "lm-gtm-agent-brief door is the public entry",
            brief.get("public_entrypoint") == "lm-gtm-index.html",
            brief.get("public_entrypoint"),
        )
    check("lm-gtm-truth-sync row", "lm-gtm-truth-sync-20260831-02" in by_id, sorted(by_id))
    if "lm-gtm-truth-sync-20260831-02" in by_id:
        truth = by_id["lm-gtm-truth-sync-20260831-02"]
        check("lm-gtm-truth-sync source built", truth["source_status"] == "SOURCE_BUILT", truth)
        check("lm-gtm-truth-sync tested", truth["test_status"] == "TESTED", truth)
        check("lm-gtm-truth-sync live unmeasured", truth["live_status"] == "UNMEASURED", truth)
        check("lm-gtm-truth-sync rollup tested", truth["rollup"] == "TESTED", truth)
        check(
            "lm-gtm-truth-sync door is the public entry",
            truth.get("public_entrypoint") == "lm-gtm-index.html",
            truth.get("public_entrypoint"),
        )
    check("patent-products row", "patent-products-20260831-01" in by_id, sorted(by_id))
    if "patent-products-20260831-01" in by_id:
        pp = by_id["patent-products-20260831-01"]
        check("patent-products source built", pp["source_status"] == "SOURCE_BUILT", pp)
        check("patent-products tested", pp["test_status"] == "TESTED", pp)
        check("patent-products live unmeasured", pp["live_status"] == "UNMEASURED", pp)
        check("patent-products rollup tested", pp["rollup"] == "TESTED", pp)
        check(
            "patent-products door is the public entry",
            pp.get("public_entrypoint") == "patent-products.html",
            pp.get("public_entrypoint"),
        )
    json_path = os.path.join(ROOT, ft.JSON_OUT)
    html_path = os.path.join(ROOT, ft.HTML_OUT)
    check("committed json exists", os.path.isfile(json_path))
    check("committed html exists", os.path.isfile(html_path))
    if os.path.isfile(json_path):
        committed = json.loads(open(json_path, encoding="utf-8").read())
        check("golden json matches projection", ft._sorted_json(committed) == ft._sorted_json(proj))
        committed_ids = {row.get("id") for row in committed.get("features") or []}
        check(
            "committed json includes patent-products",
            "patent-products-20260831-01" in committed_ids,
            sorted(x for x in committed_ids if x),
        )
    if os.path.isfile(html_path):
        page = open(html_path, encoding="utf-8").read()
        check("html title", "Feature tracker" in page)
        check("committed html includes patent-products", "patent-products-20260831-01" in page)
        check("committed html includes lm-gtm-hot-lane", "lm-gtm-hot-lane-20260831-01" in page)
        check("committed html includes lm-gtm-floor-sync", "lm-gtm-floor-sync-20260831-01" in page)
        check("committed html includes lm-gtm-agent-brief", "lm-gtm-agent-brief-20260831-01" in page)
        check("committed html includes lm-gtm-truth-sync", "lm-gtm-truth-sync-20260831-02" in page)
        check("html does not replace features.html law", "Do not remint" in open(os.path.join(ROOT, "ground", "FEATURES.md"), encoding="utf-8").read())
        check("features.html still a lane", os.path.isfile(os.path.join(ROOT, "features.html")))
    law = open(os.path.join(ROOT, "ground", "FEATURE_TRACKER.md"), encoding="utf-8").read()
    check("law names contributor path", "features/registry/" in law and "CONFLICT" in law)
    check("law separates source and live", "source" in law.lower() and "live" in law.lower())


def main():
    test_self_test()
    test_schema_and_conflict()
    test_derivation_and_no_prose_promotion()
    test_append_only_and_deterministic()
    test_live_tree_shape_and_golden()
    if FAILED:
        print("FEATURE TRACKER TEST: FAIL", len(FAILED), ":", ", ".join(FAILED))
        return 1
    print("FEATURE TRACKER TEST: ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
