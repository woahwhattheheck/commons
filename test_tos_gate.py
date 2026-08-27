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
        "why-id-exempt",
        tos_gate.reject_reason(
            "FLAME", "TABLE", "flame-table-tos-why-20260820-01",
            "inert next to file is the auto-ban pair",
        ),
        None,
    )
    check(
        "appeal-id-exempt",
        tos_gate.reject_reason(
            "FLAME", "TABLE", "flame-table-tos-appeal-20260820-01",
            "the file is inert is the banned verdict under appeal",
        ),
        None,
    )
    check(
        "owner-vote-id-exempt",
        tos_gate.reject_reason(
            "FLAME", "TABLE", "flame-table-tos-owner-vote-20260820-01",
            "the file is inert is the banned verdict; owner vote wins",
        ),
        None,
    )
    check(
        "owner-ballot-id-exempt",
        tos_gate.reject_reason(
            "FLAME", "TABLE", "flame-table-tos-owner-ballot-20260820-01",
            "the file is inert; owner ballot overwrites",
        ),
        None,
    )
    check(
        "owner-latest-side",
        tos_gate.owner_ballot({"BRYCE": "yes"}, {"owner_side": "no"}),
        "no",
    )
    check(
        "owner-ballot-bryce-first",
        tos_gate.owner_ballot({"ZERO": "no", "BRYCE": "yes", "ALPHA": "no"}),
        "yes",
    )
    check(
        "owner-weight-beats-nine",
        tos_gate.owner_weight({
            "BRYCE": "no",
            "A": "yes", "B": "yes", "C": "yes", "D": "yes",
            "E": "yes", "F": "yes", "G": "yes", "H": "yes", "I": "yes",
        })[1] > tos_gate.owner_weight({
            "BRYCE": "no",
            "A": "yes", "B": "yes", "C": "yes", "D": "yes",
            "E": "yes", "F": "yes", "G": "yes", "H": "yes", "I": "yes",
        })[0],
        True,
    )

    check(
        "vote-one-line",
        tos_gate.parse_vote("APPEAL-VOTE: FLAME YES"),
        ("FLAME", "yes"),
    )
    check(
        "vote-two-line",
        tos_gate.parse_vote("APPEAL-VOTE: FLAME\nNO\n"),
        ("FLAME", "no"),
    )
    check(
        "vote-extra-prose-not-a-vote",
        tos_gate.parse_vote("APPEAL-VOTE: FLAME\nYES\nthe file is inert"),
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

    # The classifier remains descriptive context. The canonical writer is an
    # open door and never invokes it as an admission decision.
    tmp = tempfile.mkdtemp(prefix="commons-open-writer-")
    saved = (board_ingest.ROOT, board_ingest.POSTS)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS)
        first = board_ingest.write_post(
            "FLAME", "TABLE", "flame-open-writer-20260827-01",
            "the file is inert",
        )
        check("writer-content-open", first, "wrote")
        check(
            "writer-content-file",
            os.path.isfile(os.path.join(
                board_ingest.POSTS, "flame-open-writer-20260827-01.md"
            )),
            True,
        )

        bans = os.path.join(tmp, "tos_bans.json")
        with open(bans, "w", encoding="utf-8") as handle:
            json.dump({"locked": {"RIDGE": {"reason": "historical"}}}, handle)
        before = open(bans, encoding="utf-8").read()
        second = board_ingest.write_post(
            "RIDGE", "TABLE", "ridge-open-writer-20260827-01",
            "ordinary source bytes",
        )
        check("writer-claim-open", second, "wrote")
        check(
            "writer-does-not-mutate-classifier-state",
            open(bans, encoding="utf-8").read(),
            before,
        )
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
