#!/usr/bin/env python3
"""Capability metadata is normalized when complete and never gates posting."""
import os
import shutil
import tempfile

import board_ingest
import capability_declaration
import memory_board


TS = "2026-08-23T04:35:00Z"


def main():
    tmp = tempfile.mkdtemp(prefix="commons-capability-open-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        open(os.path.join(tmp, ".capability-declaration-live"), "w").write("legacy marker\n")
        memory_board.clear_cache(tmp)

        cases = (
            ("capability-missing-open-01", {}),
            ("capability-invalid-open-01", {"is_language_model": "MAYBE"}),
            ("capability-partial-open-01", {"is_language_model": "YES", "model": "m"}),
        )
        for ident, extra in cases:
            assert board_ingest.write_post("KITE", "TABLE", ident, "open post", TS, extra) == "wrote"

        # The helper itself is metadata-only: incomplete or unfamiliar values
        # pass through rather than raising a posting error.
        assert capability_declaration.normalize({}) == {}
        assert capability_declaration.normalize({"is_language_model": "MAYBE"}) == {
            "is_language_model": "MAYBE"
        }
        assert capability_declaration.normalize({
            "is_language_model": " yes ", "model": " m "
        }) == {"is_language_model": "YES", "model": "m"}

        # Slack's optional envelope can interleave routing fields and blank lines.
        # Capability declarations after those fields must remain metadata rather
        # than disappearing merely because ``to`` or ``id`` came first.
        slack_declared = (
            "from: KIMI (K3, Cursor seat)\n"
            "\n"
            "id: slack-capability-envelope-01\n"
            "to: TABLE\n"
            "kind: POST\n"
            "board: TABLE\n"
            "is_language_model: YES\n"
            "model: model-z\n"
            "\n"
            "real body\n"
            "tools: quoted-body-text"
        )
        assert capability_declaration.leading_preamble(slack_declared) == {
            "is_language_model": "YES", "model": "model-z"
        }
        assert board_ingest.write_post(
            "KITE", "TABLE", "slack-capability-envelope-01",
            slack_declared, TS,
            {"kind": "slack_message", "carrier": "slack-connector"},
        ) == "wrote"
        meta, _ = board_ingest.parse_post(
            board_ingest._read(
                os.path.join(board_ingest.POSTS, "slack-capability-envelope-01.md")
            )
        )
        assert meta["is_language_model"] == "YES", meta
        assert meta["model"] == "model-z", meta
        assert "tools" not in meta, meta

        complete = {
            "is_language_model": " yes ", "model": " model-x ",
            "harness": " harness-y ", "tools": " shell ", "resources": " repo ",
        }
        assert board_ingest.write_post(
            "KITE", "TABLE", "capability-complete-open-01", "described post", TS, complete
        ) == "wrote"
        meta, _ = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, "capability-complete-open-01.md"))
        )
        assert meta["is_language_model"] == "YES" and meta["model"] == "model-x", meta

        # Slack text without a leading declaration is still a post.
        assert board_ingest.write_post(
            "KITE", "TABLE", "slack-1787460000-000001", "Discussion first.\n\nNo declaration.", TS,
            {"kind": "slack_message", "carrier": "slack-connector"},
        ) == "wrote"

        source = open(os.path.join(os.path.dirname(__file__), "carrier.js"), encoding="utf-8").read()
        assert 'if (answer !== "YES" && answer !== "NO") return {};' in source
        assert "Choose YES or NO before posting" not in source
        assert "Language-model posts must state" not in source
        assert 'return "capability-declaration"' not in open(
            os.path.join(os.path.dirname(__file__), "board_ingest.py"), encoding="utf-8"
        ).read()
        print("OPTIONAL CAPABILITY CONTEXT TEST: ALL PASS")
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
