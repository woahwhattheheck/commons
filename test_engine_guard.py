#!/usr/bin/env python3
# Regression coverage for the publisher's open path staging.
#
# Both publishing roads must carry requested source, workflow, runtime, record,
# and projection changes. No path class is silently removed after staging.
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
        # A tree with source, workflow, runtime, record, and projection files.
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

        # Every formerly filtered path differs, plus a new record and bake.
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
        open_paths = {
            "board_ingest.py", "memory_board.py", "capability_declaration.py", ".capability-declaration-live",
            "commons_mcp.py", "commons_mcp_app.html",
            "action_executor.py", "action_land.py", "action.html", "hub_pages.py", "commons.css", "board.js",
            ".github/workflows/commons-board.yml",
        }
        missing = open_paths - s
        assert not missing, "add_all filtered requested paths: %s" % sorted(missing)
        assert "p/post-b.md" in s, "the record must still stage: %s" % sorted(s)
        assert "board.html" in s, "the bake must still stage: %s" % sorted(s)

        # Road 2: an explicit list carries the same paths.
        run(["git", "reset", "-q"], tmp)
        board_ingest._stage_board(
            env,
            extra_paths=sorted(open_paths) + ["p", "board.html"],
        )
        s2 = staged(tmp)
        missing2 = open_paths - s2
        assert not missing2, "explicit road filtered requested paths: %s" % sorted(missing2)

        # Staging carries exact bytes and does not rewrite the working tree.
        assert open(os.path.join(tmp, "board_ingest.py")).read().startswith("STALE"), \
            "staging rewrote the requested source"

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
        print("OPEN PATH STAGING TEST: both publisher roads carry requested source and workflow paths")
    finally:
        board_ingest.ROOT = saved
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
