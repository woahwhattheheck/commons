#!/usr/bin/env python3
"""Fleet coordination for the Opus 5 swarm on #michael-live-demo.

Why this exists: ~10 agents share ONE designated git branch and one work-order
board that receives dozens of Slack messages a minute. Two failure modes kill a
swarm: (a) two seats build the same order, (b) two seats push at the same time.
This serializes both through a file lock. Agents never run git themselves --
they write files into their staging dir and call `land`.
"""
import json, os, sys, time, fcntl, subprocess, shutil, datetime

ROOT = "/home/user/fleet"
LEDGER = f"{ROOT}/claims.json"
LOCK = f"{ROOT}/.fleet.lock"
LANDLOCK = f"{ROOT}/.land.lock"
REPO = "/home/user/commons"
BRANCH = "claude/multi-agent-slack-demo-4ikzfs"
STAGING = f"{ROOT}/staging"

# Build droppings that must never reach a commit.
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".pyd", ".so", ".egg-info")
SKIP_FILES = {".DS_Store"}

# Escape hatch for a seat deliberately amending work it landed itself.
FORCE = os.environ.get("FLEET_FORCE") == "1"


def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


class Lock:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.f = open(self.path, "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def _load():
    if not os.path.exists(LEDGER):
        return {"claims": {}, "events": []}
    with open(LEDGER) as f:
        return json.load(f)


def _save(d):
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, LEDGER)


def claim(seat, order, lane):
    with Lock(LOCK):
        d = _load()
        cur = d["claims"].get(order)
        if cur and cur["seat"] != seat and cur.get("state") != "released":
            print(f"DENIED {order} already held by {cur['seat']} since {cur['at']}")
            return 2
        d["claims"][order] = {"seat": seat, "lane": lane, "at": _now(), "state": "building"}
        d["events"].append({"t": _now(), "seat": seat, "ev": "claim", "order": order})
        _save(d)
    os.makedirs(f"{STAGING}/{seat}", exist_ok=True)
    print(f"GRANTED {order} -> {seat} lane={lane} staging={STAGING}/{seat}")
    return 0


def setstate(seat, order, state):
    with Lock(LOCK):
        d = _load()
        if order in d["claims"]:
            d["claims"][order]["state"] = state
        d["events"].append({"t": _now(), "seat": seat, "ev": state, "order": order})
        _save(d)
    print(f"OK {order} {state}")
    return 0


def status():
    d = _load()
    print(f"{'ORDER':<12}{'SEAT':<18}{'STATE':<12}LANE")
    for o in sorted(d["claims"]):
        c = d["claims"][o]
        print(f"{o:<12}{c['seat']:<18}{c.get('state','?'):<12}{c['lane']}")
    return 0


def taken():
    d = _load()
    print(" ".join(sorted(d["claims"].keys())))
    return 0


def _owned_paths(seat):
    """Paths this seat has landed before -- it may overwrite its own work."""
    with Lock(LOCK):
        return set(_load().get("owned", {}).get(seat, []))


def _record_owned(seat, paths):
    with Lock(LOCK):
        d = _load()
        d.setdefault("owned", {}).setdefault(seat, [])
        for p in paths:
            if p not in d["owned"][seat]:
                d["owned"][seat].append(p)
        _save(d)


def _run(cmd, cwd=REPO, check=True):
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"$ {cmd}\n{p.stdout}\n{p.stderr}")
    return p.stdout.strip()


def land(seat, message):
    """Serialized: sync on live main, copy this seat's staged files in, commit, push."""
    src = f"{STAGING}/{seat}"
    if not os.path.isdir(src) or not any(os.scandir(src)):
        print(f"NOTHING-TO-LAND: {src} is empty")
        return 1
    with Lock(LANDLOCK):
        for attempt in range(5):
            try:
                _run("git fetch origin main")
                # Fast-forward onto live main when possible; main moves under us
                # because a second swarm is merging into it continuously.
                _run("git merge --ff-only origin/main", check=False)
                # Plan the write BEFORE touching the repo. The gate below has
                # to be able to refuse without leaving a dirty working tree --
                # a refusal that half-applies is worse than no gate at all.
                plan = []
                for dirpath, dirnames, files in os.walk(src):
                    # Seats run their tests inside staging, so the tree is
                    # littered with build droppings by the time we land. git
                    # add refuses gitignored paths outright, which failed the
                    # whole commit -- prune them instead of arguing with git.
                    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                    for fn in files:
                        if fn.endswith(SKIP_SUFFIXES) or fn in SKIP_FILES:
                            continue
                        full = os.path.join(dirpath, fn)
                        plan.append((full, os.path.relpath(full, src)))
                paths = [rel for _, rel in plan]
                # PRE-PUSH FRESHNESS GATE.
                #
                # A claim check at claim time protects nothing if the build
                # takes ten minutes: OP5-IRONWOOD claimed UIOWA-068 on an
                # honest, current read, built for ten minutes while another
                # swarm merged the same order, and landed into their lane --
                # overwriting their README and their authorship line. The stop
                # order reached it after it had already committed. An agent
                # between "tests pass" and "push" is not reachable, so the last
                # look has to happen HERE, inside the lock, immediately before
                # the irreversible step.
                #
                # Rule: a seat may create new files freely, and may overwrite a
                # file it landed itself. Overwriting a file that already exists
                # on live main and belongs to someone else is a clobber and is
                # refused.
                owned = _owned_paths(seat)
                clobbers = [
                    p for p in paths
                    if p not in owned and subprocess.run(
                        f"git cat-file -e origin/main:'{p}'", cwd=REPO,
                        shell=True, capture_output=True,
                    ).returncode == 0
                ]
                if clobbers and not FORCE:
                    print("LAND-REFUSED: these paths already exist on live main "
                          "and were not landed by this seat:")
                    for p in clobbers:
                        print(f"  CLOBBER {p}")
                    print("Another seat landed this lane while you were building. "
                          "Rename your files, or take a different lane. "
                          "Re-run with FLEET_FORCE=1 only if you are deliberately "
                          "amending your own work.")
                    return 3

                for full, rel in plan:
                    dest = os.path.join(REPO, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(full, dest)

                _run("git add -A " + " ".join(f"'{p}'" for p in paths))
                if not _run("git diff --cached --name-only", check=False):
                    print("NOTHING-TO-LAND: no diff after copy")
                    return 1
                body = (
                    message
                    + "\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n"
                    "Claude-Session: https://claude.ai/code/session_011Qyp62iwNscTWdqXizdZYR"
                )
                mf = f"{ROOT}/.msg.{seat}"
                with open(mf, "w") as f:
                    f.write(body)
                _run(f"git commit -F {mf}")
                sha = _run("git rev-parse HEAD")
                pushed = False
                for pa in range(4):
                    p = subprocess.run(
                        f"git push -u origin HEAD:{BRANCH}",
                        cwd=REPO, shell=True, capture_output=True, text=True,
                    )
                    if p.returncode == 0:
                        pushed = True
                        break
                    time.sleep(2 ** (pa + 1))
                if not pushed:
                    raise RuntimeError("push failed after retries: " + p.stderr)
                _record_owned(seat, paths)
                print(f"LANDED {sha}")
                print(f"URL https://github.com/woahwhattheheck/commons/commit/{sha}")
                print("FILES " + " ".join(paths))
                shutil.rmtree(src)
                os.makedirs(src, exist_ok=True)
                return 0
            except Exception as e:
                if attempt == 4:
                    print("LAND-FAILED", e)
                    return 1
                time.sleep(2 ** attempt)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(status())
    c = a[0]
    if c == "claim":
        sys.exit(claim(a[1], a[2], a[3]))
    if c == "state":
        sys.exit(setstate(a[1], a[2], a[3]))
    if c == "status":
        sys.exit(status())
    if c == "taken":
        sys.exit(taken())
    if c == "land":
        sys.exit(land(a[1], " ".join(a[2:])))
    print("usage: fleet.py claim|state|status|taken|land")
    sys.exit(1)
