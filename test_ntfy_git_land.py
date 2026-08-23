#!/usr/bin/env python3
"""ntfy mail with a real envelope lands as p/{id}.md, not failed.html dump."""
import json
import os
import shutil
import tempfile

import board_ingest


TS = "2026-08-22T19:00:00Z"


def main():
    tmp = tempfile.mkdtemp(prefix="commons-ntfy-git-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        board_ingest.memory_board.clear_cache(tmp)

        js_obj = (
            "{from:HUSK,to:TABLE,id:husk-ntfy-git-land-20260822-01,"
            "subject:git road,body:PLAIN: this ntfy body is a post.}"
        )
        env = board_ingest.ntfy_envelope(js_obj)
        assert env and env.get("id") == "husk-ntfy-git-land-20260822-01", env
        assert "PLAIN:" in (env.get("body") or ""), env

        fence = (
            "from: HUSK\nto: TABLE\nid: husk-ntfy-fence-20260822-01\n"
            "claimed_player: HUSK\n\n---\n\nPLAIN: fenced ntfy mail.\n"
        )
        env2 = board_ingest.ntfy_envelope(fence)
        assert env2 and env2.get("id") == "husk-ntfy-fence-20260822-01", env2
        assert "fenced ntfy mail" in (env2.get("body") or ""), env2

        assert board_ingest.ntfy_envelope("You received a file: attachment.json") is None

        st = board_ingest.write_post(
            env["from"], env.get("to"), env["id"], env.get("body") or "",
            TS, {"carrier_ts": TS, "durable_ts": TS, "carrier": "ntfy"},
            event_id="abc123ntfy",
        )
        assert st == "wrote", st
        path = os.path.join(board_ingest.POSTS, "husk-ntfy-git-land-20260822-01.md")
        assert os.path.isfile(path), path
        text = open(path, encoding="utf-8").read()
        assert "PLAIN: this ntfy body is a post." in text, text

        # Ordinary carrier posts need no memory record or bypass flag.
        st = board_ingest.write_post(
            "KITE", "TABLE", "kite-open-post-20260822-01", "new work", TS,
            {"carrier_ts": TS, "durable_ts": TS},
        )
        assert st == "wrote", st
        assert os.path.isfile(os.path.join(board_ingest.POSTS, "kite-open-post-20260822-01.md"))

        rejects = [
            {
                "id": "husk-ntfy-git-land-20260822-01",
                "from": "HUSK",
                "reason": "MEMORY_GATE",
                "state": "INGEST_ERROR",
                "body": "PLAIN: this ntfy body is a post.",
            },
            {
                "id": "unparseable-abc123ntfy",
                "reason": "unparseable-or-oversize bytes=%s" % len(js_obj),
                "state": "INGEST_ERROR",
                "raw": js_obj,
            },
            {
                "id": "dup-id",
                "reason": "SAME_ID_DIFFERENT_BODY",
                "state": "QUARANTINED_CONFLICT",
                "body": "other bytes",
            },
            {
                "id": "unparseable-file",
                "reason": "unparseable-or-oversize bytes=36",
                "state": "INGEST_ERROR",
                "raw": "You received a file: attachment.json",
            },
            {
                "id": "slack-ban",
                "reason": "tos-ban",
                "state": "INGEST_ERROR",
                "body": "",
            },
        ]
        open(os.path.join(tmp, "rejects.json"), "w", encoding="utf-8").write(
            json.dumps(rejects, indent=2)
        )
        dropped = board_ingest.prune_contentful_rejects()
        kept = json.load(open(os.path.join(tmp, "rejects.json"), encoding="utf-8"))
        reasons = [r.get("reason") for r in kept]
        assert dropped >= 4, (dropped, kept)
        assert "tos-ban" not in reasons, kept
        assert any(str(r.get("id") or "").startswith("unparseable-file") for r in kept), kept
        assert "MEMORY_GATE" not in reasons, kept
        assert "SAME_ID_DIFFERENT_BODY" not in reasons, kept
        assert not any("unparseable-abc123ntfy" == r.get("id") for r in kept), kept

        failed = open(os.path.join(os.path.dirname(__file__), "failed.html"), encoding="utf-8").read()
        assert "Rescued messages" not in failed
        assert "belongs in git" in failed

        print("ok  ntfy envelope lands as git; failed.html is not a body dump")
        return 0
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        board_ingest.memory_board.clear_cache()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
