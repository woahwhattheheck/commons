#!/usr/bin/env python3
# INQUISITOR order 043: schema + projection tests for the attribution ledger.
# Sandboxed; the live builds/records/ are never touched.
import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import builds_ledger


def main():
    tmp = tempfile.mkdtemp(prefix="commons-ledger-")
    try:
        rdir = os.path.join(tmp, builds_ledger.RECORDS_DIR)
        os.makedirs(rdir)

        good_req = {"record_type": "BUILD_REQUEST", "permit_id": "P-1",
                    "request_post": "post-a", "purpose": "x", "status": "REQUESTED"}
        good_auth = {"record_type": "BUILD_AUTHORIZATION", "permit_id": "P-1",
                     "authorization_post": "post-b", "authority_claim": "A", "authority_basis": "B",
                     "builder_claim": "W", "repo": "r", "branch": "main", "change_class": "c",
                     "purpose": "x", "issued": "t", "expires": "t2", "base_sha": "s",
                     "allow_paths": [], "deny_paths": [], "allowed_ops": [],
                     "acceptance_tests": [], "stop_conditions": [],
                     "status": "AUTH_EVIDENCE_RECORDED"}
        bad_status = {"record_type": "BUILD_RECEIPT", "permit_id": "P-1",
                      "commit_shas": ["abc"], "github_push_actor": "x", "status": "TOTALLY_FINE"}
        missing_field = {"record_type": "BUILD_FINDING", "permit_id": "P-2", "status": "DISPUTED"}

        for i, rec in enumerate([good_req, good_auth, bad_status, missing_field]):
            open(os.path.join(rdir, "%03d.json" % i), "w").write(json.dumps(rec))

        # schema: valid accepted, enum violation and missing fields rejected
        assert builds_ledger.validate(good_req) == []
        assert builds_ledger.validate(good_auth) == []
        assert any("status not in enum" in p for p in builds_ledger.validate(bad_status))
        assert any("missing field" in p for p in builds_ledger.validate(missing_field))

        written = {}
        proj = builds_ledger.project(tmp, lambda p, t: written.__setitem__(p, t))
        assert proj["n_records"] == 4 and proj["n_invalid"] == 2, proj["n_invalid"]
        p1 = next(p for p in proj["permits"] if p["permit_id"] == "P-1")
        # latest VALID status wins the projection; the invalid receipt's status is not adopted
        assert p1["latest_status"] == "AUTH_EVIDENCE_RECORDED", p1["latest_status"]
        # invalid records stay listed as evidence, never dropped
        assert sum(1 for r in p1["records"] if r.get("_invalid")) == 1
        assert os.path.join(tmp, "builds.json") in written and os.path.join(tmp, "builds.html") in written
        assert 'href="./index.html"' in written[os.path.join(tmp, "builds.html")]

        # append-only: projecting twice changes no record file and is deterministic
        before = {f: hashlib.sha256(open(os.path.join(rdir, f), "rb").read()).hexdigest()
                  for f in os.listdir(rdir)}
        written2 = {}
        builds_ledger.project(tmp, lambda p, t: written2.__setitem__(p, t))
        after = {f: hashlib.sha256(open(os.path.join(rdir, f), "rb").read()).hexdigest()
                 for f in os.listdir(rdir)}
        assert before == after, "projection mutated a record"
        assert written == written2, "projection nondeterministic"

        print("BUILDS LEDGER TEST: ALL PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()


def test_record_edit_detection():
    # order 048: git-diff detection — an edit or delete of a prior record file
    # must be visible to the guard's exact detection command; adds are not
    # flagged by it (they go through schema validation instead).
    import subprocess
    tmp = tempfile.mkdtemp(prefix="commons-guard-git-")
    try:
        def git(*args):
            return subprocess.run(["git", "-C", tmp] + list(args), capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "t@t"); git("config", "user.name", "t")
        rdir = os.path.join(tmp, "builds", "records")
        os.makedirs(rdir)
        open(os.path.join(rdir, "001.json"), "w").write(json.dumps(
            {"record_type": "BUILD_REQUEST", "permit_id": "P", "request_post": "x",
             "purpose": "y", "status": "REQUESTED"}))
        git("add", "-A"); git("commit", "-qm", "add record")
        # edit the record
        open(os.path.join(rdir, "001.json"), "a").write("\n")
        git("add", "-A"); git("commit", "-qm", "tamper")
        out = git("show", "--diff-filter=MDRT", "--name-status", "--format=", "HEAD", "--", "builds/records/*").stdout
        assert "001.json" in out and out.strip().startswith("M"), out
        # delete it
        os.remove(os.path.join(rdir, "001.json"))
        git("add", "-A"); git("commit", "-qm", "delete")
        out = git("show", "--diff-filter=MDRT", "--name-status", "--format=", "HEAD", "--", "builds/records/*").stdout
        assert "001.json" in out and out.strip().startswith("D"), out
        # a fresh ADD is not flagged by the MDRT filter (validation path covers it)
        open(os.path.join(rdir, "002.json"), "w").write(json.dumps(
            {"record_type": "BUILD_REQUEST", "permit_id": "P2", "request_post": "x",
             "purpose": "y", "status": "REQUESTED"}))
        git("add", "-A"); git("commit", "-qm", "append new record")
        out = git("show", "--diff-filter=MDRT", "--name-status", "--format=", "HEAD", "--", "builds/records/*").stdout
        assert out.strip() == "", out
        print("RECORD EDIT DETECTION: M and D flagged, append clean")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if "test_record_edit_detection" in dir():
    test_record_edit_detection()
