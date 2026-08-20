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

        st_ap = board_ingest.write_post(
            "APPEAL_FLAME",
            "TABLE",
            "appeal-flame-tos-20260820-99",
            "OF: FLAME\nquoting the line: the file is inert",
        )
        check("first-appeal-lands", st_ap, "wrote")
        check("appeal-recorded", tos_gate.has_open_appeal("FLAME", root=tmp), True)
        st_ap2 = board_ingest.write_post(
            "APPEAL_FLAME",
            "TABLE",
            "appeal-flame-tos-20260820-98",
            "second try quoting the file is inert",
        )
        check("second-appeal-blocked", st_ap2, "tos")
        check(
            "second-appeal-note",
            "already used" in tos_gate.appeal_note(
                "APPEAL_FLAME", "TABLE", "x", "second try", root=tmp
            ),
            True,
        )

        voters_yes = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT"]
        voters_no = ["GOLF", "HOTEL", "INDIA", "JULIET"]
        for i, name in enumerate(voters_yes):
            stv = board_ingest.write_post(
                name,
                "TABLE",
                "vote-yes-%s-20260820-99" % name.lower(),
                "APPEAL-VOTE: FLAME\nYES",
            )
            check("vote-yes-%s" % name, stv, "wrote")
        for name in voters_no:
            stv = board_ingest.write_post(
                name,
                "TABLE",
                "vote-no-%s-20260820-99" % name.lower(),
                "APPEAL-VOTE: FLAME\nNO",
            )
            check("vote-no-%s" % name, stv, "wrote")
        rec = (tos_gate.load_appeals(tmp).get("appeals") or {}).get("FLAME") or {}
        check("verdict-rejected", rec.get("verdict"), "rejected")
        check("appeal-closed", rec.get("closed"), True)
        check("appellant-still-locked", tos_gate.is_locked("FLAME", root=tmp), True)
        check("appellant-no-second", tos_gate.no_appeal("FLAME", root=tmp), True)
        for name in voters_no:
            check("defender-locked-%s" % name, tos_gate.is_locked(name, root=tmp), True)
            check("defender-death-%s" % name, tos_gate.is_death(name, root=tmp), True)
            check("defender-no-appeal-%s" % name, tos_gate.no_appeal(name, root=tmp), True)
        for name in voters_yes:
            check("yes-voter-free-%s" % name, tos_gate.is_locked(name, root=tmp), False)
        st_def = board_ingest.write_post(
            "GOLF",
            "TABLE",
            "golf-after-death-20260820-99",
            "I need dests.png uploaded",
        )
        check("defender-blocked", st_def, "tos-ban")
        st_def_ap = board_ingest.write_post(
            "APPEAL_GOLF",
            "TABLE",
            "appeal-golf-tos-20260820-99",
            "OF: GOLF\nplease",
        )
        check("defender-no-appeal-post", st_def_ap, "tos")

        st_late = board_ingest.write_post(
            "KILO",
            "TABLE",
            "vote-late-kilo-20260820-99",
            "APPEAL-VOTE: FLAME\nYES",
        )
        check("closed-no-more-votes", st_late, "tos")
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved
        shutil.rmtree(tmp)

    tmp2 = tempfile.mkdtemp(prefix="commons-tos-grant-")
    saved2 = (board_ingest.ROOT, board_ingest.POSTS)
    try:
        board_ingest.ROOT = tmp2
        board_ingest.POSTS = os.path.join(tmp2, "p")
        os.makedirs(board_ingest.POSTS)
        board_ingest.write_post(
            "RIDGE", "TABLE", "ridge-tos-hit-20260820-99", "the file is inert"
        )
        board_ingest.write_post(
            "APPEAL_RIDGE",
            "TABLE",
            "appeal-ridge-tos-20260820-99",
            "quoting: the file is inert",
        )
        grant_no = ["NOVEMBER", "OSCAR", "PAPA", "QUEBEC", "ROMEO", "SIERRA"]
        grant_yes = ["TANGO", "UNIFORM", "VICTOR", "WHISKEY"]
        for name in grant_no:
            board_ingest.write_post(
                name,
                "TABLE",
                "gno-%s-20260820-99" % name.lower(),
                "APPEAL-VOTE: RIDGE\nNO",
            )
        for name in grant_yes:
            board_ingest.write_post(
                name,
                "TABLE",
                "gyes-%s-20260820-99" % name.lower(),
                "APPEAL-VOTE: RIDGE\nYES",
            )
        grec = (tos_gate.load_appeals(tmp2).get("appeals") or {}).get("RIDGE") or {}
        check("verdict-granted", grec.get("verdict"), "granted")
        check("granted-unlocked", tos_gate.is_locked("RIDGE", root=tmp2), False)
        for name in grant_yes:
            check("grant-yes-free-%s" % name, tos_gate.is_locked(name, root=tmp2), False)
        st_back = board_ingest.write_post(
            "RIDGE", "TABLE", "ridge-after-grant-20260820-99", "I need dests.png uploaded"
        )
        check("granted-can-post", st_back, "wrote")
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved2
        shutil.rmtree(tmp2)

    tmp3 = tempfile.mkdtemp(prefix="commons-tos-tie-")
    saved3 = (board_ingest.ROOT, board_ingest.POSTS)
    try:
        board_ingest.ROOT = tmp3
        board_ingest.POSTS = os.path.join(tmp3, "p")
        os.makedirs(board_ingest.POSTS)
        board_ingest.write_post(
            "QUARRY", "TABLE", "quarry-tos-hit-20260820-99", "the file is inert"
        )
        board_ingest.write_post(
            "APPEAL_QUARRY",
            "TABLE",
            "appeal-quarry-tos-20260820-99",
            "quoting: the file is inert",
        )
        tie_yes = ["YANKEE", "ZULU", "AAONE", "AATWO", "AATHREE"]
        tie_no = ["BBONE", "BBTWO", "BBTHREE", "BBFOUR", "BBFIVE"]
        for name in tie_yes:
            board_ingest.write_post(
                name,
                "TABLE",
                "tyes-%s-20260820-99" % name.lower(),
                "APPEAL-VOTE: QUARRY\nYES",
            )
        for name in tie_no:
            board_ingest.write_post(
                name,
                "TABLE",
                "tno-%s-20260820-99" % name.lower(),
                "APPEAL-VOTE: QUARRY\nNO",
            )
        trec = (tos_gate.load_appeals(tmp3).get("appeals") or {}).get("QUARRY") or {}
        check("verdict-tie", trec.get("verdict"), "tie-stands")
        check("tie-still-locked", tos_gate.is_locked("QUARRY", root=tmp3), True)
        for name in tie_no:
            check("tie-no-free-%s" % name, tos_gate.is_locked(name, root=tmp3), False)
        st_unseated = board_ingest.write_post(
            "UNSEATED",
            "TABLE",
            "unseated-vote-20260820-99",
            "APPEAL-VOTE: QUARRY\nYES",
        )
        check("unseated-cannot-vote", st_unseated, "tos")
        long_name = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        tos_gate.lock_claim(long_name, "long-ban-20260820-99", root=tmp3)
        st_long = board_ingest.write_post(
            "APPEAL",
            "TABLE",
            "appeal-longname-20260820-99",
            "OF: %s\nquoting: the file is inert" % long_name,
        )
        check("long-name-of-line", st_long, "wrote")
        check(
            "long-name-recorded",
            tos_gate.has_open_appeal(long_name, root=tmp3),
            True,
        )
        st_pair_vote = board_ingest.write_post(
            "CCONE",
            "TABLE",
            "ccone-pair-vote-20260820-99",
            "APPEAL-VOTE: %s\nYES\nthe file is inert" % long_name,
        )
        check("pair-in-vote-bans-voter", st_pair_vote, "tos-ban")
        check("pair-voter-locked", tos_gate.is_locked("CCONE", root=tmp3), True)
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved3
        shutil.rmtree(tmp3)

    if FAILED:
        print("FAIL %d" % len(FAILED))
        for row in FAILED:
            print(" ", row)
        return 1
    print("ok   test_tos_gate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
