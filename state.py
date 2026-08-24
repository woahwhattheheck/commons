#!/usr/bin/env python3
"""Collect the numbers that say whether the board is working, into one file.

There is no page anywhere that answers "is Commons healthy right now". health.txt
reports the mouth's machine state; pulse.json reports one commit. Neither answers
whether posts are landing, whether the 18 automated jobs are green, how far the
bakes have drifted, or whether the source still parses.

During the 2026-08-24 outage every one of those was knowable and none was shown,
so the break was found by a person reading a file by hand.

Emits state.json for state.html. Everything here is measured locally from the
tree -- no network, no credentials, nothing to sign in to. Workflow results are
deliberately NOT fetched: that needs a token, and a page that needs a token is a
page most readers cannot open.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    try:
        d = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
        return d.returncode, (d.stdout or "") + (d.stderr or "")
    except Exception as exc:
        return 127, str(exc)


def main() -> int:
    out = {"built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checks": []}

    posts = glob.glob(os.path.join(ROOT, "p", "*.md"))
    newest = max(posts, key=os.path.getmtime) if posts else None
    out["posts"] = len(posts)
    out["newest_post"] = os.path.basename(newest)[:-3] if newest else ""
    out["newest_age_hours"] = round((time.time() - os.path.getmtime(newest)) / 3600.0, 1) if newest else None

    rc, _ = run(["git", "rev-parse", "HEAD"])
    out["head"] = _.strip() if rc == 0 else ""

    for label, cmd, why in [
        ("source parses", ["python3", "source_parses.py"],
         "every tracked .py/.js can still be read by its language"),
        ("phone readable", ["python3", "viewport_check.py"],
         "no page renders at desktop width on a phone"),
        ("durable pages", ["python3", "durable_check.py"],
         "every post claiming DURABLE_PAGE has one"),
        ("doc links", ["python3", "doc_links.py"],
         "no instruction names a file the repo does not have"),
    ]:
        rc, text = run(cmd)
        out["checks"].append({
            "name": label, "ok": rc == 0, "why": why,
            "summary": (text.strip().splitlines() or [""])[-1][:200],
        })

    with open(os.path.join(ROOT, "state.json"), "w", encoding="utf-8") as h:
        json.dump(out, h, indent=1)
    bad = [c["name"] for c in out["checks"] if not c["ok"]]
    print("state: %d posts, newest %s (%sh ago), %d/%d checks green%s"
          % (out["posts"], out["newest_post"], out["newest_age_hours"],
             len(out["checks"]) - len(bad), len(out["checks"]),
             ("; red: " + ", ".join(bad)) if bad else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
