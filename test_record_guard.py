#!/usr/bin/env python3
# INQUISITOR order 052 (permit RECORD-GUARD-03): sandboxed proof that the
# guard's detection filters catch every change class — A, M, D, R, T — on
# canonical records, protected source/state, and a NEWLY NAMED workflow file.
# Uses the same diff filters and path patterns the workflow runs.
import json
import os
import shutil
import subprocess
import sys
import tempfile

REC_PATHS = ["p/*.md", "conflicts/*"]
CODE_PATHS = [
    "board.js", "index.html", "hub_pages.py", "board_ingest.py", "grave-card.html",
    "docket.json", "resources.json", "roles.json", "session.json", "hidden.json",
    "modlog.json", "wake.json", "claims.json", "keys.json", "lanes.json", "salon.json",
    "presence.json", "lastseen.json",
    ".github/workflows/*.yml", ".github/workflows/*.yaml",
]


def main():
    tmp = tempfile.mkdtemp(prefix="commons-guard-052-")
    try:
        def git(*args):
            return subprocess.run(["git", "-C", tmp] + list(args), capture_output=True, text=True)

        def detect(filters, paths):
            return git("show", "--diff-filter=" + filters, "--name-status", "--format=",
                       "HEAD", "--", *paths).stdout.strip()

        git("init", "-q")
        git("config", "user.email", "t@t"); git("config", "user.name", "t")
        os.makedirs(os.path.join(tmp, "p"))
        os.makedirs(os.path.join(tmp, ".github", "workflows"))
        open(os.path.join(tmp, "seed.txt"), "w").write("seed")
        git("add", "-A"); git("commit", "-qm", "seed")

        cases = []
        # A: added canonical record
        open(os.path.join(tmp, "p", "new-post.md"), "w").write("x")
        git("add", "-A"); git("commit", "-qm", "A record")
        cases.append(("A record", detect("AMDRT", REC_PATHS), "A"))
        # M: modified record
        open(os.path.join(tmp, "p", "new-post.md"), "a").write("y")
        git("add", "-A"); git("commit", "-qm", "M record")
        cases.append(("M record", detect("AMDRT", REC_PATHS), "M"))
        # R: renamed record
        git("mv", "p/new-post.md", "p/renamed-post.md")
        git("commit", "-qm", "R record")
        cases.append(("R record", detect("AMDRT", REC_PATHS), "R"))
        # D: deleted record
        git("rm", "-q", "p/renamed-post.md")
        git("commit", "-qm", "D record")
        cases.append(("D record", detect("AMDRT", REC_PATHS), "D"))
        # A + M protected source
        open(os.path.join(tmp, "board.js"), "w").write("code")
        git("add", "-A"); git("commit", "-qm", "A code")
        cases.append(("A code", detect("AMDRT", CODE_PATHS), "A"))
        open(os.path.join(tmp, "board.js"), "a").write("more")
        git("add", "-A"); git("commit", "-qm", "M code")
        cases.append(("M code", detect("AMDRT", CODE_PATHS), "M"))
        # T: type change on protected state (file -> symlink)
        open(os.path.join(tmp, "roles.json"), "w").write("[]")
        git("add", "-A"); git("commit", "-qm", "seed roles")
        os.remove(os.path.join(tmp, "roles.json"))
        os.symlink("board.js", os.path.join(tmp, "roles.json"))
        git("add", "-A"); git("commit", "-qm", "T state")
        cases.append(("T state", detect("AMDRT", CODE_PATHS), "T"))
        # A: a NEWLY NAMED workflow file — caught by glob, no name list needed
        open(os.path.join(tmp, ".github", "workflows", "sneaky-new-workflow.yml"), "w").write("name: x\n")
        git("add", "-A"); git("commit", "-qm", "A workflow")
        cases.append(("A new workflow", detect("AMDRT", CODE_PATHS), "A"))

        for name, out, want in cases:
            assert out and out[0].upper().startswith(want), "%s not detected: %r" % (name, out)
            print("PASS %s -> %s" % (name, out.splitlines()[0]))

        print("RECORD GUARD COVERAGE TEST: ALL PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
