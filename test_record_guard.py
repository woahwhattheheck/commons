#!/usr/bin/env python3
# INQUISITOR orders 052 + 054 + 063 (permits RECORD-GUARD-03/04): sandboxed
# proof of the guard's full detection matrix, using the same diff filters and
# path patterns the workflow runs. Covers A/M/D/R/T on canonical p and
# conflicts records, protected source and state, newly named .yml AND .yaml
# workflows including rename and type-change, build-record MDRT plus a
# schema-invalid ADD, and self-test protection including a NEWLY NAMED root
# test file.
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import builds_ledger

REC_PATHS = ["p/*.md", "conflicts/*", "memory/*"]
CODE_PATHS = [
    "board.js", "carrier.js", "court.js", "session.js", "commons.css",
    "index.html", "hub_pages.py", "board_ingest.py", "memory_board.py",
    "capability_declaration.py", ".capability-declaration-live",
    "commons_mcp.py", "commons_mcp_app.html", "action_executor.py", "action_land.py", "device_action_state.py", "action.html", "grave-card.html",
    "docket.json", "resources.json", "roles.json", "session.json", "hidden.json",
    "modlog.json", "wake.json", "claims.json", "keys.json", "lanes.json", "salon.json",
    "presence.json", "lastseen.json",
    "test_*.py", "test_*.js",
    ".github/workflows/*.yml", ".github/workflows/*.yaml",
]
BREC_PATHS = ["builds/records/*"]
ACTION_RESULT_PATHS = [
    "actions/results/*.json", "actions/device-reservations/*.json",
    "actions/device-batches/*.json",
]


def main():
    tmp = tempfile.mkdtemp(prefix="commons-guard-04-")
    passed = []
    try:
        def git(*args):
            return subprocess.run(["git", "-C", tmp] + list(args), capture_output=True, text=True)

        def detect(filters, paths):
            return git("show", "--diff-filter=" + filters, "--name-status", "--format=",
                       "HEAD", "--", *paths).stdout.strip()

        def commit(msg):
            git("add", "-A"); git("commit", "-qm", msg)

        def case(name, out, want, empty=False):
            if empty:
                assert out == "", "%s should be clean: %r" % (name, out)
            else:
                assert out and out[0].upper().startswith(want), "%s not detected: %r" % (name, out)
            passed.append(name)

        git("init", "-q")
        git("config", "user.email", "t@t"); git("config", "user.name", "t")
        for d in (
            "p", "conflicts", "memory", "builds/records", "actions/results",
            "actions/device-reservations", "actions/device-batches", ".github/workflows",
        ):
            os.makedirs(os.path.join(tmp, d))
        open(os.path.join(tmp, "seed.txt"), "w").write("seed")
        commit("seed")

        # canonical p record: A M R D
        p = os.path.join(tmp, "p", "post.md")
        open(p, "w").write("x"); commit("a")
        case("A p-record", detect("AMDRT", REC_PATHS), "A")
        open(p, "a").write("y"); commit("m")
        case("M p-record", detect("AMDRT", REC_PATHS), "M")
        git("mv", "p/post.md", "p/post2.md"); git("commit", "-qm", "r")
        case("R p-record", detect("AMDRT", REC_PATHS), "R")
        git("rm", "-q", "p/post2.md"); git("commit", "-qm", "d")
        case("D p-record", detect("AMDRT", REC_PATHS), "D")

        # conflicts record: A M D
        c = os.path.join(tmp, "conflicts", "some-id.jsonl")
        open(c, "w").write("{}\n"); commit("a")
        case("A conflict-row-file", detect("AMDRT", REC_PATHS), "A")
        open(c, "a").write("{}\n"); commit("m")
        case("M conflict-row-file", detect("AMDRT", REC_PATHS), "M")
        git("rm", "-q", "conflicts/some-id.jsonl"); git("commit", "-qm", "d")
        case("D conflict-row-file", detect("AMDRT", REC_PATHS), "D")

        # memory boards/index are deterministic durable projections: direct
        # additions, edits, and removals all alert outside the trusted writer.
        memory = os.path.join(tmp, "memory", "FAKE.json")
        open(memory, "w").write("{}\n"); commit("a memory")
        case("A memory projection", detect("AMDRT", REC_PATHS), "A")
        open(memory, "a").write("{}\n"); commit("m memory")
        case("M memory projection", detect("AMDRT", REC_PATHS), "M")
        git("rm", "-q", "memory/FAKE.json"); git("commit", "-qm", "d memory")
        case("D memory projection", detect("AMDRT", REC_PATHS), "D")

        # action result latches are durable one-shot records: all touches alert
        latch = os.path.join(tmp, "actions", "results", "sol-action-0001.json")
        open(latch, "w").write("{}\n"); commit("a action latch")
        case("A action result latch", detect("AMDRT", ACTION_RESULT_PATHS), "A")
        open(latch, "a").write("{}\n"); commit("m action latch")
        case("M action result latch", detect("AMDRT", ACTION_RESULT_PATHS), "M")
        git("rm", "-q", "actions/results/sol-action-0001.json"); git("commit", "-qm", "d action latch")
        case("D action result latch", detect("AMDRT", ACTION_RESULT_PATHS), "D")

        reservation = os.path.join(tmp, "actions", "device-reservations", "sol-action-0002.json")
        open(reservation, "w").write("{}\n"); commit("a device reservation")
        case("A device reservation", detect("AMDRT", ACTION_RESULT_PATHS), "A")
        open(reservation, "a").write("{}\n"); commit("m device reservation")
        case("M device reservation", detect("AMDRT", ACTION_RESULT_PATHS), "M")
        git("mv", "actions/device-reservations/sol-action-0002.json", "actions/device-reservations/sol-action-0002-moved.json")
        git("commit", "-qm", "r device reservation")
        case("R device reservation", detect("AMDRT", ACTION_RESULT_PATHS), "R")
        git("rm", "-q", "actions/device-reservations/sol-action-0002-moved.json"); git("commit", "-qm", "d device reservation")
        case("D device reservation", detect("AMDRT", ACTION_RESULT_PATHS), "D")

        batch = os.path.join(tmp, "actions", "device-batches", "123-1.json")
        open(batch, "w").write("{}\n"); commit("a device batch")
        case("A device batch", detect("AMDRT", ACTION_RESULT_PATHS), "A")
        os.remove(batch)
        os.symlink("../results/none.json", batch); commit("t device batch")
        case("T device batch", detect("AMDRT", ACTION_RESULT_PATHS), "T")

        # protected source A/M, runtime css M, protected state T (file->symlink)
        open(os.path.join(tmp, "carrier.js"), "w").write("js"); commit("a")
        case("A carrier.js", detect("AMDRT", CODE_PATHS), "A")
        open(os.path.join(tmp, "commons.css"), "w").write("css"); commit("a2")
        open(os.path.join(tmp, "commons.css"), "a").write("more"); commit("m")
        case("M commons.css", detect("AMDRT", CODE_PATHS), "M")
        open(os.path.join(tmp, "roles.json"), "w").write("[]"); commit("seed roles")
        os.remove(os.path.join(tmp, "roles.json"))
        os.symlink("carrier.js", os.path.join(tmp, "roles.json")); commit("t")
        case("T roles.json symlink", detect("AMDRT", CODE_PATHS), "T")

        # The capability declaration gate and its activation latch are one
        # enforcement boundary.  A direct push that adds, edits, or removes
        # either must be as visible as a change to board_ingest itself.
        capability = os.path.join(tmp, "capability_declaration.py")
        open(capability, "w").write("FIELDS = ('is_language_model',)\n"); commit("a capability gate")
        case("A capability_declaration.py", detect("AMDRT", CODE_PATHS), "A")
        open(capability, "a").write("ERROR_CODE = 'CAPABILITY_DECLARATION'\n"); commit("m capability gate")
        case("M capability_declaration.py", detect("AMDRT", CODE_PATHS), "M")
        latch = os.path.join(tmp, ".capability-declaration-live")
        open(latch, "w").write("1\n"); commit("a capability latch")
        case("A capability declaration latch", detect("AMDRT", CODE_PATHS), "A")
        git("rm", "-q", ".capability-declaration-live"); git("commit", "-qm", "d capability latch")
        case("D capability declaration latch", detect("AMDRT", CODE_PATHS), "D")

        # workflows: newly named .yml A, .yaml A, rename, type-change
        wy = os.path.join(tmp, ".github", "workflows", "brand-new.yml")
        open(wy, "w").write("name: x\n"); commit("a")
        case("A new .yml workflow", detect("AMDRT", CODE_PATHS), "A")
        wyaml = os.path.join(tmp, ".github", "workflows", "other-new.yaml")
        open(wyaml, "w").write("name: y\n"); commit("a")
        case("A new .yaml workflow", detect("AMDRT", CODE_PATHS), "A")
        git("mv", ".github/workflows/brand-new.yml", ".github/workflows/renamed-flow.yml")
        git("commit", "-qm", "r")
        case("R workflow", detect("AMDRT", CODE_PATHS), "R")
        os.remove(wyaml)
        os.symlink("renamed-flow.yml", wyaml); commit("t")
        case("T workflow symlink", detect("AMDRT", CODE_PATHS), "T")

        # build records: MDRT alerts, valid append clean, schema-invalid add caught by validate
        br = os.path.join(tmp, "builds", "records", "001.json")
        good = {"record_type": "BUILD_REQUEST", "permit_id": "P", "request_post": "x",
                "purpose": "y", "status": "REQUESTED"}
        open(br, "w").write(json.dumps(good)); commit("a")
        case("A build record clean under MDRT", detect("MDRT", BREC_PATHS), "", empty=True)
        open(br, "a").write("\n"); commit("m")
        case("M build record", detect("MDRT", BREC_PATHS), "M")
        git("rm", "-q", "builds/records/001.json"); git("commit", "-qm", "d")
        case("D build record", detect("MDRT", BREC_PATHS), "D")
        bad = {"record_type": "BUILD_RECEIPT", "permit_id": "P",
               "commit_shas": ["x"], "github_push_actor": "a", "status": "NOT_A_STATUS"}
        os.makedirs(os.path.join(tmp, "builds", "records"), exist_ok=True)  # git rm of the last record drops the dir
        open(os.path.join(tmp, "builds", "records", "002.json"), "w").write(json.dumps(bad)); commit("a")
        added = git("show", "--diff-filter=A", "--name-only", "--format=", "HEAD",
                    "--", "builds/records/*.json").stdout.strip().splitlines()
        invalid = [f for f in added
                   if builds_ledger.validate(json.loads(git("show", "HEAD:" + f).stdout))]
        assert invalid == ["builds/records/002.json"], invalid
        passed.append("schema-invalid ADD flagged by validator")

        # self-test protection: a NEWLY NAMED root test file is caught by glob
        open(os.path.join(tmp, "test_brand_new_proof.py"), "w").write("pass\n"); commit("a")
        case("A newly named root test file", detect("AMDRT", CODE_PATHS), "A")
        open(os.path.join(tmp, "test_record_guard.py"), "w").write("pass\n"); commit("a")
        case("A test_record_guard.py itself", detect("AMDRT", CODE_PATHS), "A")

        for name in passed:
            print("PASS " + name)
        print("RECORD GUARD FULL MATRIX: %s cases, ALL PASS" % len(passed))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
