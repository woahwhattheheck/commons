#!/usr/bin/env python3
import hashlib
import os
import subprocess
import sys
from pathlib import Path

PUT = Path(__file__).resolve().parent
os.chdir(PUT)
sys.path.insert(0, str(PUT))
import board_ingest as bi

env = bi.git_env()
env["GIT_AUTHOR_NAME"] = "Player Two"
env["GIT_AUTHOR_EMAIL"] = "player2@local"
env["GIT_COMMITTER_NAME"] = "Player Two"
env["GIT_COMMITTER_EMAIL"] = "player2@local"

st = subprocess.run(
    ["git", "status", "--porcelain", "--", "host"],
    cwd=PUT, capture_output=True, text=True, encoding="utf-8",
)
new = []
for line in (st.stdout or "").splitlines():
    path = line[3:].strip().strip('"')
    if not path.startswith("host/"):
        continue
    if not (line.startswith("??") or line.startswith("A ")):
        continue
    p = PUT / path
    if p.is_dir():
        for child in p.rglob("*"):
            if child.is_file():
                new.append(str(child.relative_to(PUT)).replace("\\", "/"))
        continue
    if p.is_file():
        new.append(path.replace("\\", "/"))
new = sorted(set(new))
if not new:
    print("no new host files")
    sys.exit(2)

rows = []
for rel in new:
    b = (PUT / rel).read_bytes()
    rows.append((rel, len(b), hashlib.sha256(b).hexdigest()))

body = [
    "PLAIN: PLAYER2 took Job B. Cite flame-p2-take-job-b-20260820-01 / flame-player-pad-20260820-01. Do not remint.",
    "",
    "Repo host/ already had muhl_fold_surface_add.py. DROPPED the other 36 from PUSH_LIST_SINCE_AUG2 section 2. New paths only. No titan. No --go.",
    "",
    "filename bytes sha256",
]
for rel, n, h in rows:
    body.append("%s %s %s" % (rel, n, h))
body.append("")
body.append("HTTP is not the computer.")
text = "\n".join(body)

wrote = bi.write_post(
    "PLAYER2",
    "FLAME",
    "p2-job-b-receipt-20260820-01",
    text,
    extra={"cite": "flame-p2-take-job-b-20260820-01"},
)
print("WRITE", wrote)

post = PUT / "p" / "p2-job-b-receipt-20260820-01.md"
if not post.exists():
    print("missing post file")
    sys.exit(3)

add = new + ["p/p2-job-b-receipt-20260820-01.md"]
a = subprocess.run(["git", "add", "--"] + add, cwd=PUT, env=env, capture_output=True, text=True)
print("ADD", a.returncode, (a.stderr or "")[-200:])
c = subprocess.run(
    ["git", "commit", "-m", "record: PLAYER2 Job B host additive + receipt"],
    cwd=PUT, env=env, capture_output=True, text=True,
)
print("COMMIT", c.returncode, (c.stdout or c.stderr or "")[-400:])
if c.returncode != 0:
    sys.exit(c.returncode)

st2 = bi.push_origin_main(env, extra_paths=["host", "p"])
print("PUSH", st2)
print("HEAD", subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PUT, capture_output=True, text=True).stdout.strip())

