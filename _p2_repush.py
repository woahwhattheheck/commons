# scratch — not committed. Mixed-reset onto origin (not --hard), restore sources, rebuild, push.
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SAVE = os.path.join(os.path.dirname(ROOT), "_p2_save_bumpj")
LOCK_PATH = os.path.join(ROOT, ".ingest.lock")
LOCK_WAIT = 120
LOCK_STALE = 180
SOURCES = ["board_ingest.py", "hub_pages.py", "carrier.js", "ENTRY.md"]
os.chdir(ROOT)


def git(args, timeout=120):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "never"
    env["GIT_EDITOR"] = "cmd.exe /c exit 0"
    env["GIT_SEQUENCE_EDITOR"] = "cmd.exe /c exit 0"
    env["GIT_AUTHOR_NAME"] = "Player Two"
    env["GIT_AUTHOR_EMAIL"] = "player2@local"
    env["GIT_COMMITTER_NAME"] = "Player Two"
    env["GIT_COMMITTER_EMAIL"] = "player2@local"
    return subprocess.run(
        ["git"] + list(args),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def acquire_lock():
    deadline = time.time() + LOCK_WAIT
    while True:
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ("%s lock\n" % os.getpid()).encode("utf-8"))
            return fd
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(LOCK_PATH)
            except OSError:
                age = LOCK_STALE + 1
            if age > LOCK_STALE:
                try:
                    os.remove(LOCK_PATH)
                    continue
                except OSError:
                    pass
            if time.time() >= deadline:
                raise TimeoutError("ingest lock timeout")
            time.sleep(0.25)


def restore_sources():
    for rel in SOURCES:
        shutil.copy2(os.path.join(SAVE, rel), os.path.join(ROOT, rel))
        print("restored", rel)


def main():
    head = git(["log", "-1", "--format=%s"]).stdout.strip()
    if "bump home carrier.js" not in head and "4KB wall" not in head:
        raise SystemExit("refusing mixed-reset; HEAD is %r" % head)
    ahead = git(["rev-list", "--count", "origin/main..HEAD"]).stdout.strip()
    if ahead != "1":
        raise SystemExit("refusing mixed-reset; ahead=%s" % ahead)
    saved = open(os.path.join(SAVE, "board_ingest.py"), encoding="utf-8").read()
    gitfn = saved.split("def _git", 1)[-1][:500]
    if 'encoding="utf-8"' not in gitfn:
        raise SystemExit("SAVE missing _git utf-8")
    if "for oldv in" not in saved:
        raise SystemExit("SAVE missing fill_index carrier bump")
    fd = acquire_lock()
    try:
        print("fetch", git(["fetch", "origin", "main"], timeout=90).returncode)
        print("origin", git(["rev-parse", "origin/main"]).stdout.strip())
        r = git(["reset", "--mixed", "origin/main"])
        print("mixed-reset", r.returncode, (r.stderr or "")[:300])
        if r.returncode != 0:
            raise SystemExit("mixed reset failed")
        chk = git(["restore", "--source=HEAD", "--worktree", "--", "p"])
        print("restore p", chk.returncode, (chk.stderr or "")[:200])
        restore_sources()
        sys.path.insert(0, ROOT)
        import importlib
        import board_ingest as bi

        importlib.reload(bi)
        bi.IngestLock._fd = fd
        bi.IngestLock._depth = 1
        env = bi.git_env(os.environ.copy())
        env["GIT_AUTHOR_NAME"] = "Player Two"
        env["GIT_AUTHOR_EMAIL"] = "player2@local"
        env["GIT_COMMITTER_NAME"] = "Player Two"
        env["GIT_COMMITTER_EMAIL"] = "player2@local"
        bi.rebuild()
        st = bi.commit_and_push(
            "PLAYER2 bump home carrier.js cache to 20260818j",
            env=env,
            extra_paths=["board_ingest.py"],
        )
        print("push", st)
        print("HEAD", git(["rev-parse", "HEAD"]).stdout.strip())
        print("ls-remote", git(["ls-remote", "origin", "refs/heads/main"]).stdout.strip())
        show = git(["show", "HEAD:index.html"]).stdout.split("</head>")[0]
        print("committed-head-j", "carrier.js?v=20260818j" in show)
        print("committed-head-i", "carrier.js?v=20260818i" in show)
        ingest = git(["show", "HEAD:board_ingest.py"]).stdout
        print("head-utf8-git", 'encoding="utf-8"' in ingest.split("def _git", 1)[-1][:500])
        print("head-oldv", "for oldv in" in ingest)
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass


if __name__ == "__main__":
    main()
