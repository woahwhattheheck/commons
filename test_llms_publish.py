#!/usr/bin/env python3
"""The HEAD feed rebakes after a moving-main rejection; retries stay bounded."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llms_txt


def run(args, cwd):
    rc = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    assert rc.returncode == 0, (args, rc.stdout, rc.stderr)
    return rc


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def bake(root):
    names = sorted(n for n in os.listdir(os.path.join(root, "p")) if n.endswith(".md"))
    write(os.path.join(root, "fresh.md"), "FRESH:" + ",".join(names) + "\n")
    head = run(["git", "rev-parse", "HEAD"], root).stdout.strip()
    write(os.path.join(root, "pulse.json"), json.dumps({"head": head}) + "\n")
    return 0


def configured_clone(origin, path, tmp):
    run(["git", "clone", "-q", origin, path], tmp)
    run(["git", "config", "user.email", "t@t"], path)
    run(["git", "config", "user.name", "t"], path)


def main():
    tmp = tempfile.mkdtemp(prefix="llms-publish-")
    saved = (llms_txt.ROOT, llms_txt._git)
    base_git = saved[1]
    try:
        origin = os.path.join(tmp, "origin.git")
        seed = os.path.join(tmp, "seed")
        run(["git", "init", "-q", "--bare", "-b", "main", origin], tmp)
        configured_clone(origin, seed, tmp)
        write(os.path.join(seed, "p", "a.md"), "a\n")
        write(os.path.join(seed, "fresh.md"), "STALE\n")
        write(os.path.join(seed, "pulse.json"), '{"head":"stale"}\n')
        run(["git", "add", "-A"], seed)
        run(["git", "commit", "-qm", "base"], seed)
        run(["git", "push", "-q", "origin", "HEAD:main"], seed)

        # One race: attempt one is rejected after another writer adds b.  The
        # second attempt must reset, see b, regenerate a+b, and push that exact
        # projection rather than rebasing the old a-only bytes.
        ours = os.path.join(tmp, "ours")
        racer = os.path.join(tmp, "racer")
        configured_clone(origin, ours, tmp)
        configured_clone(origin, racer, tmp)
        llms_txt.ROOT = ours
        pushes = [0]

        def one_race(args):
            if list(args) == ["push", "origin", "HEAD:main"]:
                pushes[0] += 1
                if pushes[0] == 1:
                    write(os.path.join(racer, "p", "b.md"), "b\n")
                    run(["git", "add", "-A"], racer)
                    run(["git", "commit", "-qm", "racer adds b"], racer)
                    run(["git", "push", "-q", "origin", "HEAD:main"], racer)
            return base_git(args)

        llms_txt._git = one_race
        mails = []
        status = llms_txt.publish_current_main(
            tries=3,
            build=lambda: bake(ours),
            outputs=("fresh.md", "pulse.json"),
            pause=lambda _n: None,
            mail=lambda: mails.append(pushes[0]) or "mailed",
            require_actions=False,
        )
        assert status == "pushed", status
        assert pushes[0] == 2, pushes
        assert mails == [2], mails
        check = os.path.join(tmp, "check")
        configured_clone(origin, check, tmp)
        assert open(os.path.join(check, "fresh.md"), encoding="utf-8").read() == \
            "FRESH:a.md,b.md\n"
        landed_parent = run(["git", "rev-parse", "HEAD^"], check).stdout.strip()
        pulse = json.loads(open(os.path.join(check, "pulse.json"), encoding="utf-8").read())
        assert pulse["head"] == landed_parent, (pulse, landed_parent)

        # Quiet current-main projection does not manufacture a commit/push.
        quiet = os.path.join(tmp, "quiet")
        configured_clone(origin, quiet, tmp)
        llms_txt.ROOT = quiet
        llms_txt._git = base_git
        mails = []
        status = llms_txt.publish_current_main(
            tries=3,
            build=lambda: bake(quiet),
            outputs=("fresh.md",),
            pause=lambda _n: None,
            mail=lambda: mails.append("quiet") or "mailed",
            require_actions=False,
        )
        assert status == "quiet", status
        assert mails == ["quiet"], mails

        # Quiet is not success until its base survives a CAS push check.  Move
        # origin after an initially quiet build; the old HEAD must be rejected,
        # then the retry sees c and lands a+b+c.
        quiet_race = os.path.join(tmp, "quiet-race")
        quiet_racer = os.path.join(tmp, "quiet-racer")
        configured_clone(origin, quiet_race, tmp)
        configured_clone(origin, quiet_racer, tmp)
        llms_txt.ROOT = quiet_race
        pushes = [0]
        builds = [0]
        mails = []

        def count_bake():
            builds[0] += 1
            return bake(quiet_race)

        def race_the_quiet_check(args):
            if list(args) == ["push", "origin", "HEAD:main"]:
                pushes[0] += 1
                if pushes[0] == 1:
                    write(os.path.join(quiet_racer, "p", "c.md"), "c\n")
                    run(["git", "add", "-A"], quiet_racer)
                    run(["git", "commit", "-qm", "quiet racer adds c"], quiet_racer)
                    run(["git", "push", "-q", "origin", "HEAD:main"], quiet_racer)
            return base_git(args)

        llms_txt._git = race_the_quiet_check
        status = llms_txt.publish_current_main(
            tries=3,
            build=count_bake,
            outputs=("fresh.md",),
            pause=lambda _n: None,
            mail=lambda: mails.append(pushes[0]) or "mailed",
            require_actions=False,
        )
        assert status == "pushed", status
        assert builds[0] == 2 and pushes[0] == 2, (builds, pushes)
        assert mails == [2], mails
        check_quiet = os.path.join(tmp, "check-quiet")
        configured_clone(origin, check_quiet, tmp)
        assert open(os.path.join(check_quiet, "fresh.md"), encoding="utf-8").read() == \
            "FRESH:a.md,b.md,c.md\n"

        # A main that moves on every push stops exactly at the configured
        # ceiling and returns push-fail.  There is no idle/retry loop.
        doomed = os.path.join(tmp, "doomed")
        racer2 = os.path.join(tmp, "racer2")
        configured_clone(origin, doomed, tmp)
        configured_clone(origin, racer2, tmp)
        llms_txt.ROOT = doomed
        pushes = [0]

        def every_push_races(args):
            if list(args) == ["push", "origin", "HEAD:main"]:
                pushes[0] += 1
                run(["git", "pull", "-q", "origin", "main"], racer2)
                name = "race-%d.md" % pushes[0]
                write(os.path.join(racer2, "p", name), name + "\n")
                run(["git", "add", "-A"], racer2)
                run(["git", "commit", "-qm", "race %d" % pushes[0]], racer2)
                run(["git", "push", "-q", "origin", "HEAD:main"], racer2)
            return base_git(args)

        llms_txt._git = every_push_races
        status = llms_txt.publish_current_main(
            tries=2,
            build=lambda: bake(doomed),
            outputs=("fresh.md",),
            pause=lambda _n: None,
            mail=lambda: (_ for _ in ()).throw(AssertionError("unlanded bake mailed")),
            require_actions=False,
        )
        assert status == "push-fail", status
        assert pushes[0] == 2, pushes

        # The publisher's hard reset is CI-only and must refuse a dirty tree
        # before fetch/reset can erase a human's tracked or untracked work.
        dirty = os.path.join(tmp, "dirty")
        configured_clone(origin, dirty, tmp)
        write(os.path.join(dirty, "fresh.md"), "LOCAL CHANGE\n")
        write(os.path.join(dirty, "UNTRACKED.txt"), "KEEP ME\n")
        llms_txt.ROOT = dirty
        llms_txt._git = base_git
        status = llms_txt.publish_current_main(
            build=lambda: (_ for _ in ()).throw(AssertionError("dirty tree built")),
            mail=lambda: (_ for _ in ()).throw(AssertionError("dirty tree mailed")),
            require_actions=False,
        )
        assert status == "dirty-worktree", status
        assert open(os.path.join(dirty, "fresh.md"), encoding="utf-8").read() == "LOCAL CHANGE\n"
        assert open(os.path.join(dirty, "UNTRACKED.txt"), encoding="utf-8").read() == "KEEP ME\n"
        print("LLMS PUBLISH REPLAY TEST: ALL PASS")
    finally:
        llms_txt.ROOT, llms_txt._git = saved
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
