#!/usr/bin/env python3
"""Apply the exact board_ingest bake-reset convergence repair.

This is a disposable branch helper. The executed workflow deletes it before the
production pull request is opened, leaving only source, tests, and receipts.
"""
from __future__ import annotations

from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "board_ingest.py"

OLD = '''            if retry == "pushed":
                print("bake retry pushed from refreshed origin", flush=True)
                refresh_projection_status(env)
                return "pushed"
            if recorded == "pushed":
                print("bake retry deferred after one bounded attempt; record is durable", flush=True)
                refresh_projection_status(env)
                return "pushed"
            print("bake retry failed after one bounded attempt", flush=True)
            refresh_projection_status(env)
            return "push-fail"
'''

NEW = '''            if retry == "pushed":
                print("bake retry pushed from refreshed origin", flush=True)
                refresh_projection_status(env)
                return "pushed"
            status = refresh_projection_status(env)
            if retry == "bake-reset" and status.get("state") == "CONVERGED_IN_GIT":
                # The second replay reset hard-resets to origin/main. If that
                # exact refreshed tree already carries the matching source and
                # projection receipt, another push would be a false requirement.
                print("bake retry converged on refreshed origin; no push needed", flush=True)
                return "pushed" if recorded == "pushed" else "unchanged"
            if recorded == "pushed":
                print("bake retry deferred after one bounded attempt; record is durable", flush=True)
                return "pushed"
            print("bake retry failed after one bounded attempt", flush=True)
            return "push-fail"
'''


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    if NEW in text and OLD not in text:
        print("board bake convergence repair already present")
        return 0
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f"expected one exact source block, found {count}")
    PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
    print("applied board bake convergence repair")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
