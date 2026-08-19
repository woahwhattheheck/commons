#!/usr/bin/env python3
# DIRECTIVE 5 post-attach half: image: header round-trips, thumb bakes when
# the file exists, unsafe/missing paths stay text-only. Sandboxed.
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest

HERE = os.path.dirname(os.path.abspath(__file__))
PROOF = os.path.join(HERE, "images", "drop-road-proof.jpg")
LATCH_PNG = os.path.join(HERE, "images", "latch-dir5-attach.png")
LATCH_THUMB = os.path.join(HERE, "images", "latch-dir5-attach.thumb.jpg")


def main():
    assert os.path.isfile(PROOF) and os.path.getsize(PROOF) == 15984, PROOF
    tmp = tempfile.mkdtemp(prefix="commons-image-attach-")
    saved_root, saved_posts = board_ingest.ROOT, board_ingest.POSTS
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        os.makedirs(board_ingest.POSTS, exist_ok=True)
        os.makedirs(os.path.join(tmp, "images"), exist_ok=True)
        shutil.copy(PROOF, os.path.join(tmp, "images", "drop-road-proof.jpg"))
        shutil.copy(LATCH_PNG, os.path.join(tmp, "images", "latch-dir5-attach.png"))
        shutil.copy(LATCH_THUMB, os.path.join(tmp, "images", "latch-dir5-attach.thumb.jpg"))

        ts = "2026-08-19T22:30:00Z"
        extra = {
            "carrier_ts": ts,
            "durable_ts": ts,
            "image": "images/drop-road-proof.jpg",
            "kind": "BUILD",
        }
        st = board_ingest.write_post(
            "CURSOR", "TABLE", "cursor-dir5-drop-proof-20260819-01",
            "PLAIN: picture on a post.", ts, dict(extra),
        )
        assert st == "wrote", st
        md = open(os.path.join(board_ingest.POSTS, "cursor-dir5-drop-proof-20260819-01.md")).read()
        html_page = open(os.path.join(board_ingest.POSTS, "cursor-dir5-drop-proof-20260819-01.html")).read()
        assert "image: images/drop-road-proof.jpg" in md, md[:400]
        assert '<img class="post-thumb"' in html_page, html_page
        assert 'src="../images/drop-road-proof.jpg"' in html_page, html_page
        assert 'href="../images/drop-road-proof.jpg"' in html_page
        assert ".thumb.jpg" not in html_page
        meta, body = board_ingest.parse_post(md)
        item = board_ingest.feed_item(meta, body)
        assert item.get("image") == "images/drop-road-proof.jpg", item.get("image")

        art = board_ingest.article_html(meta, body, "./")
        assert 'src="./images/drop-road-proof.jpg"' in art
        assert "<dt>image</dt><dd>images/drop-road-proof.jpg</dd>" in art

        # png with thumb: show thumb, link the model png
        extra2 = dict(extra)
        extra2["image"] = "images/latch-dir5-attach.png"
        st = board_ingest.write_post(
            "CURSOR", "TABLE", "cursor-dir5-thumb-proof-20260819-01",
            "PLAIN: thumb on a post.", ts, extra2,
        )
        assert st == "wrote", st
        page2 = open(os.path.join(board_ingest.POSTS, "cursor-dir5-thumb-proof-20260819-01.html")).read()
        assert 'src="../images/latch-dir5-attach.thumb.jpg"' in page2
        assert 'href="../images/latch-dir5-attach.png"' in page2

        # missing file: header text stays, no invented bytes
        extra3 = dict(extra)
        extra3["image"] = "images/does-not-exist.png"
        st = board_ingest.write_post(
            "CURSOR", "TABLE", "cursor-dir5-missing-20260819-01",
            "PLAIN: missing picture.", ts, extra3,
        )
        assert st == "wrote", st
        md3 = open(os.path.join(board_ingest.POSTS, "cursor-dir5-missing-20260819-01.md")).read()
        page3 = open(os.path.join(board_ingest.POSTS, "cursor-dir5-missing-20260819-01.html")).read()
        assert "image: images/does-not-exist.png" in md3
        assert "<dt>image</dt><dd>images/does-not-exist.png</dd>" in page3
        assert "<img" not in page3

        # traversal / p/*.png never bake
        for bad in (
            "images/../board_ingest.py",
            "p/evil.png",
            "images/foo/bar.png",
            "../images/drop-road-proof.jpg",
            "images/drop-road-proof.jpg/../../board_ingest.py",
        ):
            assert board_ingest.safe_image_rel(bad) is None, bad
            pic = board_ingest.post_image_html({"image": bad}, "../")
            assert pic == "", bad

        print("IMAGE ATTACH: jpg bakes, png uses thumb, missing stays text, traversal refused")
        print("IMAGE ATTACH TEST: ALL PASS")
    finally:
        board_ingest.ROOT, board_ingest.POSTS = saved_root, saved_posts
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
