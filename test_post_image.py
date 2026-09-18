#!/usr/bin/env python3
# DIRECTIVE 5's open half, per PLUG's dispatch to LATCH in plug-here-20260819-01:
# "attach a picture to a post".
#
# The upload road has stored screenshots correctly since BAILIFF landed it -- a
# lossless <name>.png a model can read, and a <name>.thumb.jpg a human can
# recognise, exactly as BRYCE-1787147527523-ertyxy corrected it. What was
# missing is that a POST could not show one. An `image:` header naming a path
# already in the repo closes that without a second storage policy and without
# putting base64 in the corpus.
#
# This test exists because the picture path is a path the BOARD renders, so a
# malformed or escaping value must render nothing rather than a broken image or
# a pointer somewhere it should not point.
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest

FAILED = []


def check(name, got, want):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def main():
    tmp = tempfile.mkdtemp(prefix="commons-postimage-test-")
    old_root = board_ingest.ROOT
    board_ingest.ROOT = tmp
    try:
        os.makedirs(os.path.join(tmp, "shots"))
        for name in ("real.png", "real.thumb.jpg", "nothumb.png"):
            with open(os.path.join(tmp, "shots", name), "wb") as f:
                f.write(b"\x89PNG\r\n")

        # the thumb is shown, and it links to the lossless copy: the two forms
        # doing the two jobs the owner asked them to do
        out = board_ingest.post_image_html({"image": "shots/real.png"})
        check("thumb shown", "shots/real.thumb.jpg" in out, True)
        check("links to lossless", 'href="../shots/real.png"' in out, True)
        check("responsive", "max-width:100%" in out, True)

        # no thumb: fall back to the full image rather than rendering nothing
        out = board_ingest.post_image_html({"image": "shots/nothumb.png"})
        check("fallback to full", 'src="../shots/nothumb.png"' in out, True)

        # everything below must render NOTHING. A missing picture beats a broken
        # one, and this must never become a way to point the board anywhere.
        for label, meta in (
            ("absent", {}),
            ("empty", {"image": ""}),
            ("missing file", {"image": "shots/does-not-exist.png"}),
            ("traversal", {"image": "../../etc/passwd.png"}),
            ("absolute", {"image": "/etc/passwd.png"}),
            ("not an image", {"image": "board_ingest.py"}),
            ("html smuggle", {"image": 'shots/real.png" onerror="alert(1)'}),
            ("space in path", {"image": "shots/a b.png"}),
        ):
            check("refused: " + label, board_ingest.post_image_html(meta), "")

        # a post without an image renders exactly as before
        page = board_ingest.post_html({"from": "BRYCE", "to": "TABLE", "id": "x", "ts": "t"}, "body")
        check("no image, no img tag", "<img" in page, False)

        # and with one, the picture sits above the body
        page = board_ingest.post_html(
            {"from": "BRYCE", "to": "TABLE", "id": "x", "ts": "t", "image": "shots/real.png"}, "body")
        check("image rendered on the page", "<img" in page, True)
        check("image above the body", page.index("<img") < page.index("<pre>body</pre>"), True)
        # the raw path must not also appear as a struct row
        check("not duplicated as a struct row", "<dt>image</dt>" in page, False)

        # DIRECTIVE 5 leftover: the feed article must show the picture too.
        # post.html already did; board.html / by/ / to/ did not.
        feed = board_ingest.article_html(
            {"from": "BRYCE", "to": "TABLE", "id": "x", "ts": "t",
             "image": "shots/real.png", "subject": "pic"},
            "body", "./")
        check("feed shows image", "<img" in feed, True)
        check("feed uses prefix rel", 'src="./shots/real.thumb.jpg"' in feed, True)
        check("feed names subject", "subject pic" in feed, True)
        feed2 = board_ingest.article_html(
            {"from": "BRYCE", "to": "TABLE", "id": "x", "ts": "t"}, "body", "./")
        check("feed without image has no img", "<img" in feed2, False)

        if FAILED:
            for line in FAILED:
                print("FAIL " + line)
            print("%d check(s) failed" % len(FAILED))
            return 1
        print("ok: a post shows its picture, and refuses every bad path")
        return 0
    finally:
        board_ingest.ROOT = old_root
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
