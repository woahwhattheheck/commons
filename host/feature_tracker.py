#!/usr/bin/env python3
"""host/feature_tracker.py — evidence-derived shipped-state tracker.

Status is derived from registry + evidence + the measured tree.
Chat, Slack, ntfy 200, an open PR, Pages, and claimed_status never promote.

  python3 host/feature_tracker.py
  python3 host/feature_tracker.py --root .
  python3 host/feature_tracker.py --write
  python3 host/feature_tracker.py --self-test

Law: ground/FEATURE_TRACKER.md
Do not remint features.html. That door is the FEATURES board lane.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys


DEFAULT_ROOT = "."
REGISTRY_DIR = os.path.join("features", "registry")
EVIDENCE_DIR = os.path.join("features", "evidence")
JSON_OUT = "feature-tracker.json"
HTML_OUT = "feature-tracker.html"
SCHEMA = "commons-feature-v1"
EVIDENCE_SCHEMA = "commons-feature-evidence-v1"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_KINDS = (
    "SOURCE_PATHS",
    "TEST_PATHS",
    "GIT_SHA",
    "BLOB",
    "LIVE_MEASUREMENT",
    "RECEIPT",
    "SUPERSEDE",
)
STATUSES = ("PLANNED", "SOURCE_BUILT", "TESTED", "LIVE", "DEGRADED", "SUPERSEDED")
CSS_TAG = '<link rel="stylesheet" href="./commons.css?v=20260823f">'
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'
RELATED_KEYS = ("boards", "current_work", "profitability", "resources")


def _read(root, rel):
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def _list_json(root, rel):
    directory = os.path.join(root, rel)
    if not os.path.isdir(directory):
        return []
    names = [name for name in os.listdir(directory) if name.endswith(".json")]
    names.sort()
    return names


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _blob(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_feature(row, filename=""):
    problems = []
    if not isinstance(row, dict):
        return ["feature is not an object"]
    if row.get("schema") != SCHEMA:
        problems.append("schema must be %s" % SCHEMA)
    feature_id = str(row.get("id") or "")
    if not ID_RE.match(feature_id):
        problems.append("id must match %s" % ID_RE.pattern)
    elif filename and filename != "%s.json" % feature_id:
        problems.append("filename must equal {id}.json")
    name = str(row.get("name") or "")
    if len(name) < 4:
        problems.append("name too short")
    for field in ("capability", "carrier", "owner_subsystem", "public_entrypoint", "next_gap"):
        if not str(row.get(field) or "").strip():
            problems.append("missing field: %s" % field)
    for field in ("claimed_paths", "test_paths", "dependencies", "resource_links"):
        value = row.get(field)
        if value is None:
            continue
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            problems.append("%s must be a list of nonempty strings" % field)
    related = row.get("related")
    if related is not None:
        if not isinstance(related, dict):
            problems.append("related must be an object")
        else:
            for key, value in related.items():
                if not isinstance(value, bool):
                    problems.append("related.%s must be boolean" % key)
    return problems


def validate_evidence(row, filename=""):
    problems = []
    if not isinstance(row, dict):
        return ["evidence is not an object"]
    if row.get("schema") != EVIDENCE_SCHEMA:
        problems.append("schema must be %s" % EVIDENCE_SCHEMA)
    evidence_id = str(row.get("id") or "")
    if not ID_RE.match(evidence_id):
        problems.append("id must match %s" % ID_RE.pattern)
    elif filename and filename != "%s.json" % evidence_id:
        problems.append("filename must equal {id}.json")
    feature_id = str(row.get("feature_id") or "")
    if not ID_RE.match(feature_id):
        problems.append("feature_id must match %s" % ID_RE.pattern)
    kind = row.get("kind")
    if kind not in EVIDENCE_KINDS:
        problems.append("kind not in enum")
    if kind == "LIVE_MEASUREMENT":
        url = str(row.get("url") or row.get("public_url") or "").strip()
        sha = str(row.get("sha") or row.get("main_sha") or "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            problems.append("LIVE_MEASUREMENT needs a public URL")
        if not SHA_RE.match(sha):
            problems.append("LIVE_MEASUREMENT needs a 40-character SHA")
    if kind == "SUPERSEDE" and not str(row.get("superseded_by") or row.get("replacement") or "").strip():
        problems.append("SUPERSEDE needs superseded_by")
    return problems


def _load_named_dir(root, rel, validate):
    rows = []
    seen = {}
    conflicts = []
    for name in _list_json(root, rel):
        raw = _read(root, os.path.join(rel, name))
        try:
            data = json.loads(raw or "")
        except ValueError:
            rows.append({"_file": name, "_invalid": ["not JSON"], "id": name[:-5]})
            continue
        if not isinstance(data, dict):
            rows.append({"_file": name, "_invalid": ["not an object"], "id": name[:-5]})
            continue
        problems = validate(data, name)
        item = dict(data)
        item["_file"] = name
        item["_blob"] = _blob(_canonical({k: v for k, v in data.items()}))
        if problems:
            item["_invalid"] = problems
        item_id = str(item.get("id") or name[:-5])
        prior = seen.get(item_id)
        if prior is None:
            seen[item_id] = item
            rows.append(item)
        elif prior.get("_blob") == item.get("_blob"):
            continue
        else:
            conflicts.append("CONFLICT same id different bytes: %s" % item_id)
            item["_invalid"] = list(item.get("_invalid") or []) + [
                "CONFLICT same id different bytes: %s" % item_id
            ]
            rows.append(item)
    return rows, conflicts


def load_registry(root):
    return _load_named_dir(root, REGISTRY_DIR, validate_feature)


def load_evidence(root):
    return _load_named_dir(root, EVIDENCE_DIR, validate_evidence)


def git_names(root):
    """Path names on HEAD/origin/main even when the worktree is sparse."""
    names = set()
    git_dir = os.path.join(root, ".git")
    if not (os.path.isdir(git_dir) or os.path.isfile(git_dir)):
        return names
    for ref in ("HEAD", "origin/main"):
        try:
            out = subprocess.check_output(
                ["git", "-C", root, "ls-tree", "-r", "--name-only", ref],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        names.update(line for line in out.splitlines() if line)
    return names


def exists_on_tree(root, rel, names=None):
    if not rel or not isinstance(rel, str):
        return False
    if os.path.exists(os.path.join(root, rel)):
        return True
    if not names:
        return False
    if rel in names:
        return True
    prefix = rel.rstrip("/") + "/"
    return any(name.startswith(prefix) for name in names)


def _live_ok(row):
    if not isinstance(row, dict) or row.get("kind") != "LIVE_MEASUREMENT":
        return False
    if row.get("_invalid"):
        return False
    url = str(row.get("url") or row.get("public_url") or "").strip()
    sha = str(row.get("sha") or row.get("main_sha") or "").strip()
    return (url.startswith("http://") or url.startswith("https://")) and bool(SHA_RE.match(sha))


def derive_status(feature, evidence_rows, root, names=None):
    """Derive shipped state. claimed_status / chat never promote."""
    feature = feature if isinstance(feature, dict) else {}
    evidence_rows = [row for row in (evidence_rows or []) if isinstance(row, dict)]
    claimed = [p for p in (feature.get("claimed_paths") or []) if isinstance(p, str) and p]
    tests = [p for p in (feature.get("test_paths") or []) if isinstance(p, str) and p]
    superseded_by = str(feature.get("superseded_by") or "").strip()
    for row in evidence_rows:
        if row.get("kind") == "SUPERSEDE" and not row.get("_invalid"):
            superseded_by = str(row.get("superseded_by") or row.get("replacement") or superseded_by).strip()
    source_ok = bool(claimed) and all(exists_on_tree(root, path, names) for path in claimed)
    test_ok = source_ok and bool(tests) and all(exists_on_tree(root, path, names) for path in tests)
    live_rows = [row for row in evidence_rows if row.get("kind") == "LIVE_MEASUREMENT"]
    live_ok = source_ok and any(_live_ok(row) for row in live_rows)

    source_evidence_paths = []
    test_evidence_paths = []
    for row in evidence_rows:
        if row.get("_invalid"):
            continue
        if row.get("kind") == "SOURCE_PATHS":
            source_evidence_paths.extend(p for p in (row.get("paths") or []) if isinstance(p, str) and p)
        if row.get("kind") == "TEST_PATHS":
            test_evidence_paths.extend(p for p in (row.get("paths") or []) if isinstance(p, str) and p)

    degraded = False
    if claimed and not source_ok and (source_evidence_paths or any(row.get("kind") == "GIT_SHA" for row in evidence_rows)):
        degraded = True
    if source_evidence_paths and any(not exists_on_tree(root, path, names) for path in source_evidence_paths):
        degraded = True
    if tests and source_ok and not test_ok and test_evidence_paths:
        degraded = True
    if live_rows and source_ok and not live_ok:
        degraded = True

    status = "PLANNED"
    if not claimed:
        status = "PLANNED"
    elif source_ok:
        status = "SOURCE_BUILT"
        if test_ok:
            status = "TESTED"
        if live_ok:
            status = "LIVE"
    if degraded:
        status = "DEGRADED"
    if superseded_by:
        status = "SUPERSEDED"
    return {
        "status": status,
        "source_built": bool(source_ok),
        "tested": bool(test_ok),
        "live": bool(live_ok),
        "degraded": bool(degraded),
        "superseded_by": superseded_by,
        "claimed_status_ignored": feature.get("claimed_status"),
    }


def project(root):
    features, feature_conflicts = load_registry(root)
    evidence, evidence_conflicts = load_evidence(root)
    problems = list(feature_conflicts) + list(evidence_conflicts)
    by_feature = {}
    for row in evidence:
        fid = str(row.get("feature_id") or "")
        by_feature.setdefault(fid, []).append(row)
    names = git_names(root)
    items = []
    for feature in features:
        fid = str(feature.get("id") or "")
        derived = derive_status(feature, by_feature.get(fid) or [], root, names)
        if feature.get("_invalid"):
            problems.extend("%s: %s" % (fid, p) for p in feature["_invalid"])
        public = {k: v for k, v in feature.items() if not str(k).startswith("_")}
        items.append({
            "id": fid,
            "name": feature.get("name"),
            "capability": feature.get("capability"),
            "carrier": feature.get("carrier"),
            "owner_subsystem": feature.get("owner_subsystem"),
            "public_entrypoint": feature.get("public_entrypoint"),
            "claimed_paths": list(feature.get("claimed_paths") or []),
            "test_paths": list(feature.get("test_paths") or []),
            "next_gap": feature.get("next_gap"),
            "related": feature.get("related") or {},
            "resource_links": list(feature.get("resource_links") or []),
            "invalid": list(feature.get("_invalid") or []),
            "evidence_ids": [str(row.get("id") or "") for row in by_feature.get(fid) or []],
            **derived,
            "registry": public,
        })
    items.sort(key=lambda row: str(row.get("id") or ""))
    counts = {status: 0 for status in STATUSES}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "schema": "commons-feature-tracker-v1",
        "note": (
            "Descriptive projection of features/registry/ + features/evidence/. "
            "Status is derived. Chat, Slack, ntfy, Pages, claimed_status, and HTTP "
            "never promote LIVE. features.html stays the FEATURES board lane."
        ),
        "statuses": list(STATUSES),
        "n_features": len(items),
        "n_evidence": len(evidence),
        "n_invalid": sum(1 for row in items if row.get("invalid")),
        "counts": counts,
        "problems": problems,
        "features": items,
    }


def render_html(projection):
    rows = []
    for item in projection.get("features") or []:
        status = str(item.get("status") or "")
        source = "yes" if item.get("source_built") else "no"
        live = "yes" if item.get("live") else "no"
        tested = "yes" if item.get("tested") else "no"
        entry = str(item.get("public_entrypoint") or "")
        entry_html = html.escape(entry)
        if entry.endswith(".html") or entry.endswith(".md"):
            entry_html = '<a href="./%s">%s</a>' % (html.escape(entry), html.escape(entry))
        rows.append(
            "<tr class=\"st-%s\"><td><code>%s</code></td><td>%s</td><td class=\"status\">%s</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                html.escape(status),
                html.escape(str(item.get("id") or "")),
                html.escape(str(item.get("name") or "")),
                html.escape(status),
                source,
                tested,
                live,
                entry_html,
                html.escape(str(item.get("next_gap") or "")),
            )
        )
    body = "\n".join(rows) if rows else '<tr><td colspan="8">no registry rows</td></tr>'
    counts = projection.get("counts") or {}
    count_line = " · ".join("%s %s" % (counts.get(status, 0), status) for status in STATUSES)
    return """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
%s
<meta name="robots" content="index,follow">
<title>Commons feature tracker</title>
%s
</head><body>
<section id="trust-through-proof" class="law trust-law" aria-label="Trust after proof — operating law"><strong>TRUST AFTER PROOF.</strong> <a href="./trust.html">Read “On Trust.”</a> Proof is cached. Build unless the bytes moved. Once evidence validates a path, stop re-litigating it: build through it at full speed and reopen doubt only when a named boundary check or new evidence invalidates the cache. <strong>Commerce is included:</strong> when the offer, delivery path, and payment road are verified, ask for the sale and fulfill it. Never invent buyers, replies, payments, or results.</section>
<p class="nav"><a href="./index.html">Commons</a> · <a href="./features.html">FEATURES lane</a> · <a href="./current-work.html">current work</a> · <a href="./ledger.html">resource ledger</a> · <a href="./boards.html">boards</a></p>
<h1>Feature tracker</h1>
<p class="law">Shipped-state tracker. Status is derived from git-visible registry, evidence, and the measured tree. <b>Source and live stay separate columns.</b> Chat, Slack, ntfy 200, an open PR, Pages, <code>claimed_status</code>, and HTTP never promote LIVE.</p>
<p>Law: <a href="./ground/FEATURE_TRACKER.md">ground/FEATURE_TRACKER.md</a>. Machine: <a href="./feature-tracker.json">feature-tracker.json</a>. Instrument: <code>python3 host/feature_tracker.py --write</code>. Proof: <code>python3 test_feature_tracker.py</code>. Registry: <a href="./features/README.md">features/registry/</a>.</p>
<p class="note"><a href="./features.html">features.html</a> is the FEATURES board lane. Do not remint it. This page is a different object.</p>
<p class="note">%s · %s features · HTTP is a bake.</p>
<table>
<thead><tr><th>id</th><th>name</th><th>status</th><th>source</th><th>tested</th><th>live</th><th>door</th><th>next gap</th></tr></thead>
<tbody>
%s
</tbody>
</table>
<p>Add a feature: mint id <code>^[A-Za-z0-9._-]{8,80}$</code>, write one new <code>features/registry/{id}.json</code>, optionally write evidence, run the instrument, unique branch, merge not force. Same id + same bytes is idempotent. Same id + different bytes is CONFLICT. No auth. No secrets.</p>
<p>LIVE requires a <code>LIVE_MEASUREMENT</code> evidence row with a public URL and a 40-character SHA. After merge, cite the Pages URL against the official main SHA. Do not fabricate LIVE.</p>
</body></html>
""" % (VIEWPORT, CSS_TAG, html.escape(count_line), projection.get("n_features") or 0, body)


def _file_hashes(root, rel):
    directory = os.path.join(root, rel)
    out = {}
    if not os.path.isdir(directory):
        return out
    for name in _list_json(root, rel):
        path = os.path.join(directory, name)
        with open(path, "rb") as handle:
            out[name] = hashlib.sha256(handle.read()).hexdigest()
    return out


def write_projection(root, write=None):
    """Write derived doors. Never mutates registry or evidence files."""
    before_reg = _file_hashes(root, REGISTRY_DIR)
    before_ev = _file_hashes(root, EVIDENCE_DIR)
    projection = project(root)
    json_text = json.dumps(projection, indent=2, sort_keys=True) + "\n"
    html_text = render_html(projection)
    writer = write
    if writer is None:
        def writer(path, text):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
    writer(os.path.join(root, JSON_OUT), json_text)
    writer(os.path.join(root, HTML_OUT), html_text)
    after_reg = _file_hashes(root, REGISTRY_DIR)
    after_ev = _file_hashes(root, EVIDENCE_DIR)
    if before_reg != after_reg or before_ev != after_ev:
        raise RuntimeError("projection mutated registry or evidence")
    return projection


def self_test():
    sample = {
        "schema": SCHEMA,
        "id": "sample-feature-20260828-01",
        "name": "Sample feature",
        "capability": "A sample row for the instrument self-test.",
        "carrier": "GROK",
        "owner_subsystem": "feature-tracker",
        "public_entrypoint": "feature-tracker.html",
        "next_gap": "none",
        "claimed_paths": ["ground/FEATURE_TRACKER.md"],
        "test_paths": ["test_feature_tracker.py"],
        "claimed_status": "LIVE",
    }
    assert validate_feature(sample, "sample-feature-20260828-01.json") == []
    planned = derive_status(
        {"id": "planned-feature-20260828-01", "claimed_paths": [], "claimed_status": "LIVE"},
        [{"kind": "LIVE_MEASUREMENT", "url": "https://example.invalid", "sha": "a" * 40}],
        ".",
    )
    assert planned["status"] == "PLANNED"
    assert planned["live"] is False
    chatter = derive_status(
        sample,
        [{"kind": "RECEIPT", "id": "ev-chat-20260828-01", "ntfy_200": True, "slack": "done"}],
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))) or ".",
    )
    assert chatter["claimed_status_ignored"] == "LIVE"
    live_row = {
        "schema": EVIDENCE_SCHEMA,
        "id": "ev-live-sample-20260828-01",
        "feature_id": "sample-feature-20260828-01",
        "kind": "LIVE_MEASUREMENT",
        "url": "https://woahwhattheheck.github.io/commons/feature-tracker.html",
        "sha": "b" * 40,
    }
    assert validate_evidence(live_row, "ev-live-sample-20260828-01.json") == []
    bad_live = dict(live_row)
    bad_live["sha"] = "abc"
    assert any("40-character SHA" in p for p in validate_evidence(bad_live, "ev-live-sample-20260828-01.json"))
    print("self-test ok")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evidence-derived shipped-state tracker")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--write", action="store_true", help="write feature-tracker.json and feature-tracker.html")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.write:
        projection = write_projection(args.root)
    else:
        projection = project(args.root)
        json.dump(projection, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 1 if projection.get("problems") else 0


if __name__ == "__main__":
    sys.exit(main())
