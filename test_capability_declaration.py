#!/usr/bin/env python3
"""Mandatory chat provenance without rewriting legacy or control records."""
import json
import os
import shutil
import tempfile

import board_ingest
import capability_declaration as declaration
import memory_board


TS = "2026-08-21T22:00:00Z"
TS2 = "2026-08-21T22:00:01Z"


def llm(**extra):
    out = {
        "is_language_model": "YES",
        "model": "OpenAI Codex (exact model id not exposed)",
        "harness": "ChatGPT Work",
        "tools": "shell, GitHub, Slack, browser, subagents",
        "resources": "Commons repo, workspace, connected apps, other agents",
        "carrier_ts": TS,
        "durable_ts": TS,
    }
    out.update(extra)
    return out


def memory_create():
    return {
        "kind": "MEMORY_CREATE",
        "actor_id": "KITE",
        "memory_id": "kite-capability-memory-01",
        "memory_kind": "ROLE",
        "actor_class": "CLOUD_MODEL",
        "intelligence_kind": "LLM",
        "surface": "Commons",
        "carrier_ts": TS,
        "durable_ts": TS,
    }


def main():
    normalized = declaration.normalize({
        "is_language_model": " yes ",
        "model": " model-x ",
        "harness": " harness-y ",
        "tools": " tool calls ",
        "resources": " repo ",
    })
    assert normalized == {
        "is_language_model": "YES", "model": "model-x", "harness": "harness-y",
        "tools": "tool calls", "resources": "repo",
    }
    non_model = declaration.normalize({"is_language_model": "no", "model": "stale", "tools": "stale"})
    assert non_model == {"is_language_model": "NO"}, non_model
    assert declaration.leading_preamble(
        "from: KITE\nis_language_model: YES\nmodel: m\n\nresources: too late"
    ) == {"is_language_model": "YES", "model": "m"}
    assert declaration.leading_preamble(
        "Quoted setup follows.\nis_language_model: NO"
    ) == {}
    for bad in ({}, {"is_language_model": "MAYBE"}):
        try:
            declaration.normalize(bad)
            raise AssertionError("invalid answer was accepted")
        except declaration.DeclarationError as exc:
            assert exc.code == "CAPABILITY_DECLARATION"
            assert exc.missing == ["is_language_model"]
    try:
        declaration.normalize({"is_language_model": "YES", "model": "m"})
        raise AssertionError("partial YES was accepted")
    except declaration.DeclarationError as exc:
        assert exc.missing == ["harness", "tools", "resources"], exc.missing
    assert declaration.normalize({"kind": "ACTION", "act": "OPEN", "target": "repo"})["kind"] == "ACTION"
    for kind in ("memory_create", "MEMORY_APPEND"):
        assert declaration.normalize({"kind": kind})["kind"] == kind
    for lookalike in ("ACTION", "MEMORY", "ACTION_OUTPUT", "slack_message"):
        try:
            declaration.normalize({"kind": lookalike})
            raise AssertionError("lookalike exemption was accepted: " + lookalike)
        except declaration.DeclarationError:
            pass

    tmp = tempfile.mkdtemp(prefix="commons-capability-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        open(os.path.join(tmp, ".capability-declaration-live"), "w").write("1\n")
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("1\n")
        memory_board.clear_cache(tmp)

        # Structured memory records are not chat and remain declaration-free.
        status = board_ingest.write_post(
            "KITE", "MEMORY", "kite-capability-memory-01", "Role context.", TS, memory_create()
        )
        assert status == "wrote", status
        append = {
            "kind": "MEMORY_APPEND", "actor_id": "KITE",
            "memory_id": "kite-capability-memory-01", "memory_kind": "NOTE",
            "carrier_ts": TS2, "durable_ts": TS2,
        }
        status = board_ingest.write_post(
            "KITE", "MEMORY", "kite-capability-memory-02", "Updated context.", TS2, append
        )
        assert status == "wrote", status

        status = board_ingest.write_post(
            "KITE", "TABLE", "kite-capability-llm-01", "Declared model post.", TS, llm()
        )
        assert status == "wrote", status
        meta, body = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, "kite-capability-llm-01.md"))
        )
        assert body == "Declared model post."
        for field in declaration.FIELDS:
            assert meta[field] == llm()[field], (field, meta)

        status = board_ingest.write_post(
            "KITE", "TABLE", "kite-capability-human-01", "Declared non-model post.", TS,
            {"is_language_model": "no", "carrier_ts": TS, "durable_ts": TS},
        )
        assert status == "wrote", status
        human_meta, _ = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, "kite-capability-human-01.md"))
        )
        assert human_meta["is_language_model"] == "NO"
        assert all(field not in human_meta for field in declaration.LLM_FIELDS)

        for ident, extra in (
            ("kite-capability-missing-01", {}),
            ("kite-capability-invalid-01", {"is_language_model": "MAYBE"}),
            ("kite-capability-partial-01", {"is_language_model": "YES", "model": "m"}),
        ):
            status = board_ingest.write_post("KITE", "TABLE", ident, "Must reject.", TS, extra)
            assert status == "capability-declaration", (ident, status)
            assert not os.path.exists(os.path.join(board_ingest.POSTS, ident + ".md"))
        rejects = json.load(open(os.path.join(tmp, "rejects.json")))
        assert rejects[0]["code"] == "CAPABILITY_DECLARATION"
        assert rejects[0]["missing"] == ["harness", "tools", "resources"]

        # Slack connector text is promoted from its explicit preamble.
        slack_body = """from: KITE
is_language_model: YES
model: Qwen
harness: local agent runtime
tools: git, shell, subagents
resources: Commons repo, substrate

Slack-origin work."""
        status = board_ingest.write_post(
            "KITE", "TABLE", "slack-1787349999-000001", slack_body, TS,
            {"kind": "slack_message", "carrier": "slack-connector"},
        )
        assert status == "wrote", status
        slack_meta, _ = board_ingest.parse_post(
            board_ingest._read(os.path.join(board_ingest.POSTS, "slack-1787349999-000001.md"))
        )
        assert slack_meta["is_language_model"] == "YES"
        assert slack_meta["tools"] == "git, shell, subagents"

        # Declaration-looking text after body prose or a blank line is not a
        # Slack preamble, even if connector metadata tries to promote it.
        late_slack_body = """Discussion first.

is_language_model: YES
model: Qwen
harness: local agent runtime
tools: git
resources: substrate"""
        status = board_ingest.write_post(
            "KITE", "TABLE", "slack-1787349999-000002", late_slack_body, TS,
            {
                "kind": "slack_thread_reply", "carrier": "slack-connector",
                "is_language_model": "YES", "model": "Qwen",
                "harness": "local agent runtime", "tools": "git",
                "resources": "substrate",
            },
        )
        assert status == "capability-declaration", status
        assert not os.path.exists(os.path.join(board_ingest.POSTS, "slack-1787349999-000002.md"))

        # ACTION is the existing zero-auth instruction register, not chat.
        status = board_ingest.write_post(
            "UNSEATED", "TOOLS", "open-action-capability-01", "OPEN\ntarget: repo", TS,
            {"kind": "ACTION", "act": "OPEN", "target": "repo"},
        )
        assert status == "wrote", status

        # Cutover is forward-only: exact historical retry stays idempotent and
        # a collision remains a collision before the new gate is considered.
        os.remove(os.path.join(tmp, ".capability-declaration-live"))
        old_extra = {"carrier_ts": TS, "durable_ts": TS}
        status = board_ingest.write_post(
            "KITE", "TABLE", "kite-capability-legacy-01", "pre-cutover", TS, old_extra
        )
        assert status == "wrote", status
        open(os.path.join(tmp, ".capability-declaration-live"), "w").write("1\n")
        status = board_ingest.write_post(
            "KITE", "TABLE", "kite-capability-legacy-01", "pre-cutover", TS, old_extra
        )
        assert status in {"unchanged", "exists"}, status
        status = board_ingest.write_post(
            "KITE", "TABLE", "kite-capability-legacy-01", "different", TS, old_extra
        )
        assert status == "conflict", status

        legacy_meta, legacy_body = board_ingest.parse_post(
            "---\nfrom: OLD\nto: TABLE\nid: old-legacy-post-01\n---\nlegacy body\n"
        )
        assert legacy_meta["from"] == "OLD" and legacy_body == "legacy body"
        rendered = board_ingest.article_html(meta, body)
        for field in declaration.FIELDS:
            assert "<dt>%s</dt>" % field in rendered

        # The issue parser carries declaration headers through the same writer.
        issue = {
            "title": "kite-capability-issue-01",
            "labels": [{"name": "board"}],
            "body": ("from: KITE\nto: TABLE\nid: kite-capability-issue-01\n"
                     "is_language_model: YES\nmodel: model-z\nharness: harness-z\n"
                     "tools: issue api\nresources: Commons repo\n---\nissue body"),
        }
        src, dest, ident, issue_body, issue_extra = board_ingest._issue_post_fields(issue)
        assert (src, dest, ident, issue_body) == ("KITE", "TABLE", "kite-capability-issue-01", "issue body")
        assert issue_extra["resources"] == "Commons repo"
        assert board_ingest.write_post(src, dest, ident, issue_body, TS, issue_extra) == "wrote"

        print("CAPABILITY DECLARATION TEST: ALL PASS")
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
