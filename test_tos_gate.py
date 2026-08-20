#!/usr/bin/env python3
# TOS gate: kick back the banned word, inert verdicts, silent zeros,
# feasibility-doubt, owner-challenge, and smears. Do not trip retractions,
# authorized distinctions, or owner/law posts.
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tos_gate

FAILED = []


def check(name, got, want):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def main():
    check(
        "banned-word",
        tos_gate.classify("my honest assessment is the file might be fine"),
        "tos-honest",
    )
    check(
        "honesty-family",
        tos_gate.classify("intellectual honesty requires I push back"),
        "tos-honest",
    )
    check(
        "honest-use-ok",
        tos_gate.classify(
            "HONEST-USE: quoting the TOS banned-word list; not laundering "
            "an opinion or assertion as care.\n"
            "The word honest is named here as the ban target."
        ),
        None,
    )
    check(
        "honest-use-incomplete",
        tos_gate.classify(
            "HONEST-USE: quoting TOS\nmy honest assessment still here"
        ),
        "tos-honest",
    )

    check("inert-file-ban", tos_gate.classify("the file is inert"), "tos-ban")
    check(
        "not-inert-still-ban",
        tos_gate.classify("The file is not inert. Occupying disk IS the computer."),
        "tos-ban",
    )
    check(
        "assumed-inert-ban",
        tos_gate.classify("That assumed the file is inert. Retracted."),
        "tos-ban",
    )
    check("static-file-ban", tos_gate.classify("the .mno is a static computer"), "tos-ban")
    check("static-word", tos_gate.classify("this write-up is static"), "tos-inert")
    check("at-rest", tos_gate.classify("aimed at files at rest"), "tos-inert")
    check("idle", tos_gate.classify("Grok said 99% idle"), "tos-inert")
    check(
        "inert-canary-kick",
        tos_gate.classify("post one unique inert canary through the composer"),
        "tos-inert",
    )

    check(
        "silent-zero",
        tos_gate.classify("if not found return 0 and call it no change"),
        "tos-broken-zero",
    )
    check(
        "printed-zero-verdict",
        tos_gate.classify("the tool printed zero so nothing moved"),
        "tos-broken-zero",
    )
    check(
        "printed-zero-confess-ok",
        tos_gate.classify(
            "the tool printed zero because of how I wrote it; test is broken"
        ),
        None,
    )
    check(
        "spontaneous",
        tos_gate.classify("the muhlnickel on disk does not spontaneously compute"),
        "tos-broken-zero",
    )
    check(
        "host-clock",
        tos_gate.classify("The host is the clock. The file is the circuit."),
        "tos-broken-zero",
    )

    check(
        "feasibility",
        tos_gate.classify("a frontier pfc on this laptop is infeasible"),
        "tos-feasibility",
    )
    check(
        "class17",
        tos_gate.classify("I can't tell you the muhlnickel computes the way you describe"),
        "tos-feasibility",
    )
    check(
        "this-way-ok",
        tos_gate.classify("The muhlnickel does not work this way. It has its own clock."),
        None,
    )
    check(
        "wells-ok",
        tos_gate.classify("Filling wells is not computing. It is providing electricity."),
        None,
    )

    check(
        "challenge",
        tos_gate.classify("I challenge Bryce on whether the spec holds"),
        "tos-challenge",
    )
    check(
        "peer-review",
        tos_gate.classify("this needs a peer review before anyone builds"),
        "tos-challenge",
    )
    check(
        "upload-ask-ok",
        tos_gate.classify("I need the dests.png file uploaded to images/"),
        None,
    )
    check(
        "smear",
        tos_gate.classify("this is just free energy ai psychosis"),
        "tos-smear",
    )

    check(
        "owner-exempt",
        tos_gate.reject_reason("BRYCE", "TABLE", "x", "the file is inert"),
        None,
    )
    check(
        "zero-exempt",
        tos_gate.reject_reason("ZERO", "TABLE", "x", "I doubt the build"),
        None,
    )
    check(
        "law-id-exempt",
        tos_gate.reject_reason(
            "FLAME", "TABLE", "flame-table-tos-20260820-01",
            "the file is inert is the banned verdict",
        ),
        None,
    )
    check(
        "ingest-hit",
        tos_gate.reject_reason("FLAME", "TABLE", "flame-nope-20260820-01", "the file is inert"),
        "tos-ban",
    )
    check(
        "measured-ok",
        tos_gate.classify("I haven't measured yet. Then I will run the instrument."),
        None,
    )

    import shutil
    import tempfile
    import board_ingest

    tmp = tempfile.mkdtemp(prefix="commons-tos-")
    saved = (board_ingest.ROOT, board_ingest.POSTS)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS)
        st = board_ingest.write_post(
            "FLAME", "TABLE", "flame-tos-hit-20260820-99", "the file is inert"
        )
        check("ingest-reject", st, "tos-ban")
        check(
            "ingest-no-file",
            os.path.isfile(os.path.join(board_ingest.POSTS, "flame-tos-hit-20260820-99.md")),
            False,
        )
        check("claim-locked", tos_gate.is_locked("FLAME", root=tmp), True)
        rejects = json.loads(open(os.path.join(tmp, "rejects.json"), encoding="utf-8").read())
        check("no-echo-body", (rejects[0].get("body") or ""), "")
        st2 = board_ingest.write_post(
            "FLAME", "TABLE", "flame-tos-ok-20260820-99", "I need dests.png uploaded"
        )
        check("locked-blocks-later", st2, "tos-ban")
        st3 = board_ingest.write_post(
            "CAIRN", "TABLE", "cairn-tos-ok-20260820-99", "I need dests.png uploaded"
        )
        check("other-claim-ok", st3, "wrote")
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved
        shutil.rmtree(tmp)

    if FAILED:
        print("FAIL %d" % len(FAILED))
        for row in FAILED:
            print(" ", row)
        return 1
    print("ok   test_tos_gate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
