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
    saved_root = board_ingest.ROOT
    try:
        board_ingest.ROOT = root
        board_ingest.write_projection_convergence()
    finally:
        board_ingest.ROOT = saved_root


def main():
    tmp = tempfile.mkdtemp(prefix="commons-replay-")
    saved = (board_ingest.ROOT, board_ingest.rebuild, board_ingest.push_origin_main, board_ingest._git)
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
        # weekend-087: under contention the replay lands the payload ALONE as a
        # "record:" commit — the bake stays origin's until the next publish
        subj = run(["git", "log", "--format=%s", "-1"], check).stdout.strip()
        assert subj.startswith("record: replayed"), subj
        baked = open(os.path.join(check, "board.html")).read()
        assert baked == "BAKE:a.md,b.md,dup.md\n", baked
        # the follow-up publish rebakes the union on the merged record
        bake(ours)
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html", "p"])
        assert st == "pushed", st
        run(["git", "pull", "-q", "origin", "main"], check)
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

        # Phase-two reset regression: after our record wins, race the derived
        # bake with a conflicting stale bake.  The replay reset must surface
        # as bake-reset (not a successful no-op push), rebuild from refreshed
        # origin exactly once, and push the union.  The retry itself gets one
        # push attempt, so a permanently moving main cannot create a loop.
        cp3 = os.path.join(tmp, "cp3")
        racer = os.path.join(tmp, "racer")
        run(["git", "clone", "-q", origin, cp3], tmp)
        run(["git", "clone", "-q", origin, racer], tmp)
        for cwd in (cp3, racer):
            run(["git", "config", "user.email", "r@r"], cwd)
            run(["git", "config", "user.name", "r"], cwd)
        board_ingest.ROOT = cp3
        board_ingest.rebuild = lambda: bake(cp3)
        write(os.path.join(cp3, "p", "g.md"), "post g\n")
        bake(cp3)

        real_push = board_ingest.push_origin_main
        push_receipts = []
        raced = [False]

        def push_with_one_bake_race(*args, **kwargs):
            bake_phase = kwargs.get("bake_phase", False)
            if bake_phase and not raced[0]:
                raced[0] = True
                run(["git", "pull", "-q", "origin", "main"], racer)
                write(os.path.join(racer, "p", "h.md"), "post h\n")
                write(os.path.join(racer, "board.html"), "STALE CONFLICTING BAKE\n")
                run(["git", "add", "-A"], racer)
                run(["git", "commit", "-qm", "racing stale bake"], racer)
                run(["git", "push", "-q", "origin", "HEAD:main"], racer)
            result = real_push(*args, **kwargs)
            push_receipts.append((bake_phase, kwargs.get("tries"), result))
            return result

        board_ingest.push_origin_main = push_with_one_bake_race
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html", "p"])
        board_ingest.push_origin_main = real_push
        assert st == "pushed", st
        bake_receipts = [row for row in push_receipts if row[0] is True]
        assert bake_receipts[0][2] == "bake-reset", bake_receipts
        assert bake_receipts[-1] == (True, 1, "pushed"), bake_receipts

        check3 = os.path.join(tmp, "check3")
        run(["git", "clone", "-q", origin, check3], tmp)
        baked3 = open(os.path.join(check3, "board.html")).read()
        assert baked3 == "BAKE:a.md,b.md,c.md,dup.md,e.md,f.md,g.md,h.md\n", baked3

        # The same reset signal is required when phase one has no new record:
        # scheduled/idempotent runs still carry repaired derivative pages.  A
        # receipt-policy flag cannot double as the phase discriminator.
        cp4 = os.path.join(tmp, "cp4")
        racer2 = os.path.join(tmp, "racer2")
        run(["git", "clone", "-q", origin, cp4], tmp)
        run(["git", "clone", "-q", origin, racer2], tmp)
        for cwd in (cp4, racer2):
            run(["git", "config", "user.email", "s@s"], cwd)
            run(["git", "config", "user.name", "s"], cwd)
        board_ingest.ROOT = cp4
        board_ingest.rebuild = lambda: bake(cp4)
        write(os.path.join(cp4, "board.html"), "LOCAL DERIVED REPAIR\n")

        real_push = board_ingest.push_origin_main
        push_receipts = []
        raced = [False]

        def push_with_recordless_bake_race(*args, **kwargs):
            bake_phase = kwargs.get("bake_phase", False)
            if bake_phase and not raced[0]:
                raced[0] = True
                write(os.path.join(racer2, "board.html"), "STALE RACER BAKE\n")
                run(["git", "add", "-A"], racer2)
                run(["git", "commit", "-qm", "recordless stale bake"], racer2)
                run(["git", "push", "-q", "origin", "HEAD:main"], racer2)
            result = real_push(*args, **kwargs)
            push_receipts.append((bake_phase, kwargs.get("tries"), result))
            return result

        board_ingest.push_origin_main = push_with_recordless_bake_race
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html"])
        board_ingest.push_origin_main = real_push
        assert st == "pushed", st
        bake_receipts = [row for row in push_receipts if row[0] is True]
        assert bake_receipts[0][2] == "bake-reset", bake_receipts
        assert bake_receipts[-1] == (True, 1, "pushed"), bake_receipts

        check4 = os.path.join(tmp, "check4")
        run(["git", "clone", "-q", origin, check4], tmp)
        baked4 = open(os.path.join(check4, "board.html")).read()
        assert baked4 == baked3, (baked3, baked4)

        # A second recordless race stops after that one retry and reports an
        # actual publish failure.  It must not spin and it must not turn the
        # second reset into another no-op success.
        cp5 = os.path.join(tmp, "cp5")
        racer3 = os.path.join(tmp, "racer3")
        run(["git", "clone", "-q", origin, cp5], tmp)
        run(["git", "clone", "-q", origin, racer3], tmp)
        for cwd in (cp5, racer3):
            run(["git", "config", "user.email", "u@u"], cwd)
            run(["git", "config", "user.name", "u"], cwd)
        board_ingest.ROOT = cp5
        board_ingest.rebuild = lambda: bake(cp5)
        write(os.path.join(cp5, "board.html"), "LOCAL RECORDLESS REPAIR\n")

        real_push = board_ingest.push_origin_main
        push_receipts = []
        race_count = [0]

        def push_with_two_recordless_races(*args, **kwargs):
            bake_phase = kwargs.get("bake_phase", False)
            if bake_phase:
                race_count[0] += 1
                run(["git", "pull", "-q", "origin", "main"], racer3)
                write(
                    os.path.join(racer3, "board.html"),
                    "STALE RECORDLESS RACE %d\n" % race_count[0],
                )
                run(["git", "add", "-A"], racer3)
                run(["git", "commit", "-qm", "recordless race %d" % race_count[0]], racer3)
                run(["git", "push", "-q", "origin", "HEAD:main"], racer3)
            result = real_push(*args, **kwargs)
            push_receipts.append((bake_phase, kwargs.get("tries"), result))
            return result

        board_ingest.push_origin_main = push_with_two_recordless_races
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html"])
        board_ingest.push_origin_main = real_push
        assert st == "push-fail", st
        bake_receipts = [row for row in push_receipts if row[0] is True]
        assert bake_receipts == [
            (True, None, "bake-reset"),
            (True, 1, "bake-reset"),
        ], bake_receipts
        assert race_count[0] == 2, race_count

        # With a new source record, the same two-race ceiling preserves the
        # already-pushed record and reports overall record success while
        # explicitly deferring only the derived bake.
        cp6 = os.path.join(tmp, "cp6")
        racer4 = os.path.join(tmp, "racer4")
        run(["git", "clone", "-q", origin, cp6], tmp)
        run(["git", "clone", "-q", origin, racer4], tmp)
        for cwd in (cp6, racer4):
            run(["git", "config", "user.email", "v@v"], cwd)
            run(["git", "config", "user.name", "v"], cwd)
        board_ingest.ROOT = cp6
        board_ingest.rebuild = lambda: bake(cp6)
        write(os.path.join(cp6, "p", "i.md"), "post i\n")
        bake(cp6)

        real_push = board_ingest.push_origin_main
        push_receipts = []
        race_count = [0]

        def push_with_two_recorded_races(*args, **kwargs):
            bake_phase = kwargs.get("bake_phase", False)
            if bake_phase:
                race_count[0] += 1
                run(["git", "pull", "-q", "origin", "main"], racer4)
                write(
                    os.path.join(racer4, "board.html"),
                    "STALE RECORDED RACE %d\n" % race_count[0],
                )
                run(["git", "add", "-A"], racer4)
                run(["git", "commit", "-qm", "recorded race %d" % race_count[0]], racer4)
                run(["git", "push", "-q", "origin", "HEAD:main"], racer4)
            result = real_push(*args, **kwargs)
            push_receipts.append((bake_phase, kwargs.get("tries"), result))
            return result

        board_ingest.push_origin_main = push_with_two_recorded_races
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html", "p"])
        board_ingest.push_origin_main = real_push
        assert st == "pushed", st
        bake_receipts = [row for row in push_receipts if row[0] is True]
        assert bake_receipts == [
            (True, None, "bake-reset"),
            (True, 1, "bake-reset"),
        ], bake_receipts
        assert race_count[0] == 2, race_count
        check6 = os.path.join(tmp, "check6")
        run(["git", "clone", "-q", origin, check6], tmp)
        assert os.path.isfile(os.path.join(check6, "p", "i.md")), "durable record lost"

        # Pending-marker CAS regression: race a new source record after our
        # digest was computed but before the marker push. The stale digest must
        # not replay over the larger union; the retry refreshes origin and
        # lands only the union digest.
        cp7 = os.path.join(tmp, "cp7")
        racer5 = os.path.join(tmp, "racer5")
        run(["git", "clone", "-q", origin, cp7], tmp)
        run(["git", "clone", "-q", origin, racer5], tmp)
        for cwd in (cp7, racer5):
            run(["git", "config", "user.email", "w@w"], cwd)
            run(["git", "config", "user.name", "w"], cwd)
        board_ingest.ROOT = cp7
        board_ingest.rebuild = lambda: bake(cp7)
        write(os.path.join(cp7, "p", "j.md"), "post j\n")
        bake(cp7)
        stale_digest = board_ingest.post_source_snapshot()["sha256"]

        real_git = board_ingest._git
        marker_staged = [False]
        marker_raced = [False]

        def git_with_pending_race(args, env, timeout=90):
            if args and args[0] == "add" and any(
                str(value).startswith("projection/pending/") for value in args
            ):
                marker_staged[0] = True
            if (
                marker_staged[0]
                and not marker_raced[0]
                and args[:3] == ["push", "origin", "HEAD:main"]
            ):
                marker_raced[0] = True
                run(["git", "pull", "-q", "origin", "main"], racer5)
                write(os.path.join(racer5, "p", "k.md"), "post k\n")
                run(["git", "add", "--", "p/k.md"], racer5)
                run(["git", "commit", "-qm", "pending digest racer"], racer5)
                run(["git", "push", "-q", "origin", "HEAD:main"], racer5)
            return real_git(args, env, timeout=timeout)

        board_ingest._git = git_with_pending_race
        st = board_ingest.commit_and_push("board ingest", extra_paths=["board.html", "p"])
        board_ingest._git = real_git
        assert st == "pushed", st
        assert marker_raced[0], "pending marker push was not raced"

        check7 = os.path.join(tmp, "check7")
        run(["git", "clone", "-q", origin, check7], tmp)
        board_ingest.ROOT = check7
        union_digest = board_ingest.post_source_snapshot()["sha256"]
        assert union_digest != stale_digest, (stale_digest, union_digest)
        union_pending = os.path.join(
            check7, "projection", "pending", board_ingest.PROJECTION_PROTOCOL,
            union_digest + ".json",
        )
        stale_pending = os.path.join(
            check7, "projection", "pending", board_ingest.PROJECTION_PROTOCOL,
            stale_digest + ".json",
        )
        assert os.path.isfile(union_pending), "refreshed union pending marker missing"
        assert not os.path.exists(stale_pending), "stale pending marker leaked onto main"

        print("PUSH REPLAY TEST: ALL PASS")
    finally:
        (board_ingest.ROOT, board_ingest.rebuild,
         board_ingest.push_origin_main, board_ingest._git) = saved
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
