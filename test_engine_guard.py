#!/usr/bin/env python3
# weekend-095: the publisher must never commit engine source.
#
# The two-phase publish protects the RECORD (additive, irreplaceable) by
# letting the BAKE (mutable, replaceable) lose a race. Engine source is a third
# class -- mutable like a bake, irreplaceable like the record -- and it used to
# ride with the disposables. A publish carrying a stale checkout could
# therefore overwrite newer code: FABLE's phone-rendering push deleted three of
# THE_WEEKEND's parser functions in a commit whose stated intent was CSS.
#
# Proves both staging roads hold the line: add_all=True (git add -A, the real
# publish path) and the explicit ASSET_PATHS road, which still names
# commons.css / hub_pages.py / the workflow.
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest


def run(args, cwd):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, (args, r.stdout, r.stderr)
    return r


def write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(t)


def staged(cwd):
    r = subprocess.run(["git", "diff", "--cached", "--name-only"],
                       cwd=cwd, capture_output=True, text=True)
    return set(x for x in r.stdout.splitlines() if x.strip())


def main():
    tmp = tempfile.mkdtemp(prefix="commons-engine-guard-")
    saved = board_ingest.ROOT
    try:
        run(["git", "init", "-q", "-b", "main", tmp], tmp)
        run(["git", "config", "user.email", "t@t"], tmp)
        run(["git", "config", "user.name", "t"], tmp)
        # a tree with engine source, a record file and a bake
        for name in (
            "board_ingest.py", "memory_board.py", "capability_declaration.py", ".capability-declaration-live",
            "commons_mcp.py", "commons_mcp_app.html",
            "action_executor.py", "action_land.py", "action.html", "hub_pages.py", "commons.css", "board.js",
        ):
            write(os.path.join(tmp, name), "original\n")
        write(os.path.join(tmp, ".github/workflows/commons-board.yml"), "name: x\n")
        write(os.path.join(tmp, "p", "post-a.md"), "post\n")
        write(os.path.join(tmp, "board.html"), "bake\n")
        run(["git", "add", "-A"], tmp)
        run(["git", "commit", "-qm", "base"], tmp)

        board_ingest.ROOT = tmp
        env = board_ingest.git_env()

        # a stale/divergent runner: every engine file differs, plus real work
        for name in (
            "board_ingest.py", "memory_board.py", "capability_declaration.py", ".capability-declaration-live",
            "commons_mcp.py", "commons_mcp_app.html",
            "action_executor.py", "action_land.py", "action.html", "hub_pages.py", "commons.css", "board.js",
        ):
            write(os.path.join(tmp, name), "STALE COPY - would delete newer code\n")
        write(os.path.join(tmp, ".github/workflows/commons-board.yml"), "name: stale\n")
        write(os.path.join(tmp, "p", "post-b.md"), "new post\n")
        write(os.path.join(tmp, "board.html"), "rebaked\n")

        # road 1: the real publish path
        board_ingest._stage_board(env, add_all=True)
        s = staged(tmp)
        engine = {
            "board_ingest.py", "memory_board.py", "capability_declaration.py", ".capability-declaration-live",
            "commons_mcp.py", "commons_mcp_app.html",
            "action_executor.py", "action_land.py", "action.html", "hub_pages.py", "commons.css", "board.js",
            ".github/workflows/commons-board.yml",
        }
        leaked = s & engine
        assert not leaked, "add_all leaked engine source: %s" % sorted(leaked)
        assert "p/post-b.md" in s, "the record must still stage: %s" % sorted(s)
        assert "board.html" in s, "the bake must still stage: %s" % sorted(s)

        # road 2: the explicit ASSET_PATHS path (it names engine files)
        run(["git", "reset", "-q"], tmp)
        board_ingest._stage_board(env, extra_paths=["p", "board.html"])
        s2 = staged(tmp)
        leaked2 = s2 & engine
        assert not leaked2, "ASSET_PATHS road leaked engine source: %s" % sorted(leaked2)

        # and the engine is untouched on disk -- held back, never reverted
        assert open(os.path.join(tmp, "board_ingest.py")).read().startswith("STALE"), \
            "the guard must not rewrite the working tree, only unstage it"

        # add_all must not delete the record (4e7ad47)
        run(["git", "reset", "-q"], tmp)
        os.remove(os.path.join(tmp, "p", "post-a.md"))
        board_ingest._stage_board(env, add_all=True)
        s3 = staged(tmp)
        deleted = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=D"],
            cwd=tmp, capture_output=True, text=True,
        )
        gone = set(x for x in deleted.stdout.splitlines() if x.strip())
        assert "p/post-a.md" not in gone, "bake staged a record delete: %s" % sorted(gone)
        assert os.path.isfile(os.path.join(tmp, "p", "post-a.md")), \
            "record delete must be restored from HEAD"
        assert "p/post-b.md" in s3, "new record must still stage: %s" % sorted(s3)

        assert board_ingest.keep_newer_asset_v("20260820y", "20260820s") == "20260820y"
        assert board_ingest.keep_newer_asset_v("20260820s", "20260820y") == "20260820y"
        print("ENGINE GUARD TEST: publisher cannot commit engine source (both roads)")
    finally:
        board_ingest.ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
