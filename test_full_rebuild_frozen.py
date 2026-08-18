#!/usr/bin/env python3
# INQUISITOR order 046: TWO COMPLETE rebuilds under a frozen clock and
# randomized directory order must be byte-identical across every generated
# file. Also order 044: exact tied-actor assertions — for every actor whose
# newest posts tie on one second, lastseen and presence must name the same id.
# Runs on a full copy of the working tree; the real repo is never touched.
# Note for unfrozen production: orient.json is INTENTIONALLY time-derived
# (embeds wall-clock ts and relative ages); only a frozen clock makes it
# comparable, which is exactly what this test does.
import hashlib
import os
import random
import shutil
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board_ingest
import hub_pages
import builds_ledger  # noqa: F401  (imported by board_ingest; kept explicit)

FROZEN = datetime(2026, 8, 18, 16, 0, 0, tzinfo=timezone.utc)


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN if tz else FROZEN.replace(tzinfo=None)

    @classmethod
    def fromisoformat(cls, s):
        return datetime.fromisoformat(s)

    @classmethod
    def fromtimestamp(cls, t, tz=None):
        return datetime.fromtimestamp(t, tz)


def snap(root):
    out = {}
    for dirpath, dirs, files in os.walk(root):
        if ".git" in dirpath:
            continue
        for f in files:
            p = os.path.join(dirpath, f)
            out[os.path.relpath(p, root)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="commons-frozen-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO,
             board_ingest.datetime, hub_pages.datetime)
    real_listdir = os.listdir
    try:
        dst = os.path.join(tmp, "tree")
        shutil.copytree(HERE, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        board_ingest.ROOT = dst
        board_ingest.POSTS = os.path.join(dst, "p")
        board_ingest.BY = os.path.join(dst, "by")
        board_ingest.TO = os.path.join(dst, "to")
        board_ingest.datetime = FrozenDatetime
        hub_pages.datetime = FrozenDatetime

        snaps = []
        for seed in (7, 8675309):
            rng = random.Random(seed)

            def rand_listdir(p, _rng=rng, _r=real_listdir):
                names = _r(p)
                _rng.shuffle(names)
                return names

            os.listdir = rand_listdir
            board_ingest.rebuild()
            os.listdir = real_listdir
            snaps.append(snap(dst))
        diff = sorted(set(k for k in snaps[0] if snaps[0].get(k) != snaps[1].get(k))
                      | set(k for k in snaps[1] if k not in snaps[0]))
        assert not diff, "frozen-clock rebuilds differ: %s" % diff[:10]
        print("FULL REBUILD: byte-identical across all %s files, frozen clock, randomized dir order" % len(snaps[1]))

        # order 044: exact tied-actor agreement on the REAL corpus
        import json
        ls = {r["from"]: r for r in json.load(open(os.path.join(dst, "lastseen.json")))}
        pr = {r["from"]: r for r in json.load(open(os.path.join(dst, "presence.json")))}
        disagree = [(k, ls[k]["id"], pr[k]["id"]) for k in ls if k in pr and ls[k]["id"] != pr[k]["id"]]
        assert not disagree, "tied-actor projections disagree: %s" % disagree
        tied = [k for k in ls if k in pr and ls[k].get("ts") == pr[k].get("ts")]
        assert tied, "corpus has no tied actors to assert on"
        print("TIE CONSISTENCY: %s actors checked, %s with matching newest ts, zero disagreements" % (len(ls), len(tied)))

        print("FULL REBUILD FROZEN TEST: ALL PASS")
    finally:
        os.listdir = real_listdir
        (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO,
         board_ingest.datetime, hub_pages.datetime) = saved
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
