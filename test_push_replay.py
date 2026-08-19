#!/usr/bin/env python3
# The push-race conflict path, end to end against a real (local) origin.
# History: merging two full-corpus bakes via rebase died a new way each day —
# unmerged files _stage_board never added (run 32297808918), then git 2.55
# refusing --continue once rebuild() staged fresh bakes mid-rebase (run
# 32299103849). _resolve_rebase now replays source files on a refreshed origin
# instead of rebasing. Proves: a racing runner's payload and ours both land,
# the bake is re-derived from the union, and a duplicate id keeps ORIGIN's
# body. Sandboxed: never touches the live record or the network.
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def run(args, cwd, **kw):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)
    assert r.returncode == 0, (args, r.stdout, r.stderr)
    return r


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def bake(root):
    # stand-in for rebuild(): the bake is a pure projection of p/*.md
    names = sorted(n for n in os.listdir(os.path.join(root, "p")) if n.endswith(".md"))
    write(os.path.join(root, "board.html"), "BAKE:" + ",".join(names) + "\n")


def main():
    tmp = tempfile.mkdtemp(prefix="commons-replay-")
    saved = (board_ingest.ROOT, board_ingest.rebuild)
    try:
        origin = os.path.join(tmp, "origin.git")
        ours = os.path.join(tmp, "ours")
        other = os.path.join(tmp, "other")
        run(["git", "init", "-q", "--bare", "-b", "main", origin], tmp)

        run(["git", "clone", "-q", origin, ours], tmp)
        for cwd in (ours,):
            run(["git", "config", "user.email", "t@t"], cwd)
            run(["git", "config", "user.name", "t"], cwd)
        write(os.path.join(ours, "p", "a.md"), "post a\n")
        bake(ours)
        run(["git", "add", "-A"], ours)
        run(["git", "commit", "-qm", "base"], ours)
        run(["git", "push", "-q", "origin", "HEAD:main"], ours)

        # the racing runner lands p/b.md plus its own bake, and p/dup.md first
        run(["git", "clone", "-q", origin, other], tmp)
        run(["git", "config", "user.email", "o@o"], other)
        run(["git", "config", "user.name", "o"], other)
        write(os.path.join(other, "p", "b.md"), "post b\n")
        write(os.path.join(other, "p", "dup.md"), "ORIGINAL body\n")
        bake(other)
        run(["git", "add", "-A"], other)
        run(["git", "commit", "-qm", "other runner"], other)
        run(["git", "push", "-q", "origin", "HEAD:main"], other)

        # our runner, unaware, commits p/c.md + a conflicting bake + the same
        # dup id with a DIFFERENT body
        write(os.path.join(ours, "p", "c.md"), "post c\n")
        write(os.path.join(ours, "p", "dup.md"), "different body\n")
        bake(ours)
        run(["git", "add", "-A"], ours)
        run(["git", "commit", "-qm", "our runner"], ours)

        board_ingest.ROOT = ours
        board_ingest.rebuild = lambda: bake(ours)
        # the sandbox carries only a slice of the real tree; ASSET_PATHS that
        # do not exist are skipped by _stage_board (that skip is itself under
        # test: an unmatched pathspec used to abort the whole add, exit 128)
        env = board_ingest.git_env()
        st = board_ingest.push_origin_main(env=env, extra_paths=["board.html", "p"])
        assert st == "pushed", st

        check = os.path.join(tmp, "check")
        run(["git", "clone", "-q", origin, check], tmp)
        for n in ("a.md", "b.md", "c.md", "dup.md"):
            assert os.path.isfile(os.path.join(check, "p", n)), n + " missing on origin"
        dup = open(os.path.join(check, "p", "dup.md")).read()
        assert dup == "ORIGINAL body\n", "duplicate id must keep origin's body, got %r" % dup
        baked = open(os.path.join(check, "board.html")).read()
        assert baked == "BAKE:a.md,b.md,c.md,dup.md\n", baked

        # Two-phase commit_and_push (weekend-085): the record commit goes
        # first and alone; the bake rides second. Race a fourth runner in
        # before our push and assert our record still lands, with a
        # "record:" commit in origin's history.
        cp2 = os.path.join(tmp, "cp2")
        run(["git", "clone", "-q", origin, cp2], tmp)
        run(["git", "config", "user.email", "t@t"], cp2)
        run(["git", "config", "user.name", "t"], cp2)
        board_ingest.ROOT = cp2
        board_ingest.rebuild = lambda: bake(cp2)
        write(os.path.join(cp2, "p", "e.md"), "post e\n")
        bake(cp2)
        # the racing runner lands p/f.md + its own bake after our checkout
        write(os.path.join(other, "p", "f.md"), "post f\n")
        run(["git", "pull", "-q", "origin", "main"], other)
        bake(other)
        run(["git", "add", "-A"], other)
        run(["git", "commit", "-qm", "other runner again"], other)
        run(["git", "push", "-q", "origin", "HEAD:main"], other)
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html", "p"])
        assert st == "pushed", st
        check2 = os.path.join(tmp, "check2")
        run(["git", "clone", "-q", origin, check2], tmp)
        for n in ("e.md", "f.md"):
            assert os.path.isfile(os.path.join(check2, "p", n)), n + " missing on origin"
        subjects = run(["git", "log", "--format=%s", "-5"], check2).stdout
        assert "record: board ingest" in subjects, subjects
        baked2 = open(os.path.join(check2, "board.html")).read()
        assert baked2 == "BAKE:a.md,b.md,c.md,dup.md,e.md,f.md\n", baked2

        print("PUSH REPLAY TEST: ALL PASS")
    finally:
        board_ingest.ROOT, board_ingest.rebuild = saved
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
