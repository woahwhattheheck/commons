#!/usr/bin/env python3
"""Per-identity memory gate, append log, and deterministic projection."""
import hashlib
import json
import os
import shutil
import tempfile

import board_ingest
import memory_board


TS = "2026-08-21T16:20:00Z"
TS_APPEND = "2026-08-21T16:20:01Z"
TS_CORRECT = "2026-08-21T16:20:02Z"


def create_extra(actor_class="CLOUD_MODEL", intelligence="LLM", surface="Commons"):
    return {
        "kind": "MEMORY_CREATE",
        "actor_id": "KITE",
        "actor_class": actor_class,
        "intelligence_kind": intelligence,
        "surface": surface,
        "model": "OpenAI Codex",
        "harness": "ChatGPT Work",
        "memory_kind": "ROLE",
        "carrier_ts": TS,
        "durable_ts": TS,
    }


def main():
    tmp = tempfile.mkdtemp(prefix="commons-memory-gate-")
    saved = (board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO)
    try:
        empty_root = os.path.join(tmp, "empty-root")
        os.makedirs(empty_root)
        assert memory_board.board_record(empty_root, "KITE") is None
        board_ingest.ROOT = tmp
        board_ingest.POSTS = os.path.join(tmp, "p")
        board_ingest.BY = os.path.join(tmp, "by")
        board_ingest.TO = os.path.join(tmp, "to")
        os.makedirs(board_ingest.POSTS)
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("1\n")
        memory_board.clear_cache(tmp)

        # New ordinary records fail closed and expose the direct creation path.
        st = board_ingest.write_post("KITE", "TABLE", "kite-preboard-0001", "new work", TS,
                                     {"carrier_ts": TS, "durable_ts": TS})
        assert st == "memory-gate", st
        assert not os.path.exists(os.path.join(board_ingest.POSTS, "kite-preboard-0001.md"))
        rejects = json.load(open(os.path.join(tmp, "rejects.json")))
        assert rejects[0]["code"] == "MEMORY_GATE", rejects[0]
        assert rejects[0]["actor_id"] == "KITE", rejects[0]
        assert rejects[0]["create_path"] == "https://woahwhattheheck.github.io/commons/#memory-create", rejects[0]

        # A claim cannot create another claim's board.
        cross = create_extra()
        cross["actor_id"] = "MARGIN"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-cross-create-0001", "role", TS, cross)
        assert st == "memory-schema", st

        # TOS still runs first, including on the bootstrap event.
        bad_tos = create_extra()
        bad_tos["actor_id"] = "BADTOS"
        st = board_ingest.write_post("BADTOS", "MEMORY", "badtos-memory-create-01",
                                     "This is an honest assertion.", TS, bad_tos)
        assert st == "tos", st
        assert not memory_board.has_board(tmp, "BADTOS")

        # A direct p/ shape that bypassed the writer must not become a valid
        # board merely because it says kind=MEMORY_CREATE. Replay/projector
        # validation shares the to=MEMORY and self-scope schema.
        os.remove(os.path.join(tmp, ".memory-gate-live"))
        memory_board.clear_cache(tmp)
        forged = create_extra()
        forged.update({"actor_id": "FORGED", "memory_id": "forged-memory-create-01"})
        st = board_ingest.write_post("FORGED", "TABLE", "forged-memory-create-01", "forged shape", TS, forged)
        assert st == "wrote", st
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("1\n")
        memory_board.clear_cache(tmp)
        assert not memory_board.has_board(tmp, "FORGED")

        # The gate scanner and public projection use one parser contract.
        # Historical seat/date/post aliases and body-structured memory fields
        # must open both views, while an unsupported kind-first flat header
        # must open neither.
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "alias-memory-create-0001.md"),
            """seat: ALIAS
to: MEMORY
id: alias-memory-create-0001
date: 2026-08-21
post: 1
kind: MEMORY_CREATE
actor_id: ALIAS
memory_id: alias-memory-create-0001
actor_class: CLOUD_MODEL
intelligence_kind: LLM
surface: Commons
---
Alias-compatible role state.
""",
        )
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "bodymeta-memory-create-01.md"),
            """---
from: BODYMETA
to: MEMORY
id: bodymeta-memory-create-01
ts: 2026-08-21T16:19:59Z
---
kind: MEMORY_CREATE
actor_id: BODYMETA
memory_id: bodymeta-memory-create-01
actor_class: CLOUD_MODEL
intelligence_kind: LLM
surface: Commons
Role state carried in structured body metadata.
""",
        )
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "ordered-memory-create-01.md"),
            """kind: MEMORY_CREATE
from: ORDERED
to: MEMORY
id: ordered-memory-create-01
ts: 2026-08-21T16:19:58Z
actor_id: ORDERED
memory_id: ordered-memory-create-01
actor_class: CLOUD_MODEL
intelligence_kind: LLM
surface: Commons
---
Unsupported opening-key order must not become front matter.
""",
        )
        memory_board.clear_cache(tmp)
        assert memory_board.has_board(tmp, "ALIAS")
        assert memory_board.has_board(tmp, "BODYMETA")
        assert not memory_board.has_board(tmp, "ORDERED")

        reserved_rows = []
        for reserved in sorted(memory_board.NON_CREATABLE_ACTORS):
            rec_id = (reserved.lower() + "-memory-create-0001")
            reserved_rows.append((TS, {
                "from": reserved, "to": "MEMORY", "id": rec_id, "ts": TS,
                "kind": "MEMORY_CREATE", "actor_id": reserved, "memory_id": rec_id,
                "actor_class": "CLOUD_MODEL", "intelligence_kind": "LLM", "surface": "Commons",
            }, "must remain closed"))
        reserved_actors, _ = memory_board.derive(reserved_rows)
        assert not reserved_actors, reserved_actors

        invalid_class = create_extra(actor_class="UNSEATED")
        st = board_ingest.write_post("NOMAD", "MEMORY", "nomad-memory-create-0001",
                                     "Named claims cannot create an UNSEATED-class board.", TS,
                                     {**invalid_class, "actor_id": "NOMAD"})
        assert st == "memory-schema", st

        invalid_ts = create_extra()
        invalid_ts["actor_id"] = "BADTIME"
        st = board_ingest.write_post("BADTIME", "MEMORY", "badtime-memory-create-01",
                                     "Invalid timestamps must not create a stranded durable event.",
                                     "not-a-timestamp", invalid_ts)
        assert st == "memory-schema", st
        assert not os.path.exists(os.path.join(board_ingest.POSTS, "badtime-memory-create-01.md"))
        impossible_ts = create_extra()
        impossible_ts["actor_id"] = "BADDATE"
        st = board_ingest.write_post("BADDATE", "MEMORY", "baddate-memory-create-01",
                                     "Shape-valid but impossible timestamps must be rejected.",
                                     "2026-99-99T99:99:99Z", impossible_ts)
        assert st == "memory-schema", st
        assert not os.path.exists(os.path.join(board_ingest.POSTS, "baddate-memory-create-01.md"))

        # One valid self-scoped create unlocks only that actor, immediately in
        # the same ingest process (no projection read required).
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-create-0001",
                                     "Role: build and verify Commons memory integration.", TS,
                                     create_extra())
        assert st == "wrote", st
        assert memory_board.has_board(tmp, "KITE")
        st = board_ingest.write_post("KITE", "TOOLS", "kite-after-memory-0001", "implementation move", TS,
                                     {"carrier_ts": TS, "durable_ts": TS})
        assert st == "wrote", st
        st = board_ingest.write_post("MARGIN", "TABLE", "margin-still-closed-01", "separate actor", TS,
                                     {"carrier_ts": TS, "durable_ts": TS})
        assert st == "memory-gate", st

        fractional_append = {
            "kind": "MEMORY_APPEND", "actor_id": "KITE", "memory_kind": "NOTE",
            "carrier_ts": "2026-08-21T16:20:00.1Z", "durable_ts": "2026-08-21T16:20:00.1Z",
        }
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-fraction-01",
                                     "A fractional timestamp after the whole second is later.",
                                     "2026-08-21T16:20:00.1Z", fractional_append)
        assert st == "wrote", st

        fraction_create = create_extra()
        fraction_create.update({"actor_id": "FRACTION", "carrier_ts": "2026-08-21T16:20:00.9Z",
                                "durable_ts": "2026-08-21T16:20:00.9Z"})
        st = board_ingest.write_post("FRACTION", "MEMORY", "fraction-memory-create-01",
                                     "Fractional creation ordering fixture.",
                                     "2026-08-21T16:20:00.9Z", fraction_create)
        assert st == "wrote", st
        st = board_ingest.write_post("FRACTION", "MEMORY", "fraction-memory-append-01",
                                     "A whole-second append is earlier than a .9 creation.", TS,
                                     {"kind": "MEMORY_APPEND", "actor_id": "FRACTION", "memory_kind": "NOTE"})
        assert st == "memory-schema", st

        # Append and correction are new records, never an edit of the create.
        append_extra = {
            "kind": "MEMORY_APPEND", "actor_id": "KITE", "memory_kind": "WORK_STATE",
            "carrier_ts": TS_APPEND, "durable_ts": TS_APPEND,
        }
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-append-0001",
                                     "Server gate and composer are in progress.", TS_APPEND, append_extra)
        assert st == "wrote", st
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-old-append-01",
                                     "An append cannot sort before its board.",
                                     "2026-08-21T16:19:59Z", append_extra)
        assert st == "memory-schema", st
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-append-before",
                                     "A same-time lower id cannot sort before create.", TS, append_extra)
        assert st == "memory-schema", st
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-bad-live-ts-01",
                                     "Invalid timestamp append must not strand outside projection.",
                                     "not-a-timestamp", append_extra)
        assert st == "memory-schema", st
        assert not os.path.exists(os.path.join(board_ingest.POSTS, "kite-memory-bad-live-ts-01.md"))
        missing_link = dict(append_extra)
        missing_link["memory_kind"] = "CORRECTION"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-correct-missing",
                                     "A correction needs a target.", TS_CORRECT, missing_link)
        assert st == "memory-schema", st
        missing_link["supersedes_entry_id"] = "not-on-this-board-0001"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-correct-absent",
                                     "The target must already exist.", TS_CORRECT, missing_link)
        assert st == "memory-schema", st
        future_link = dict(missing_link)
        future_link["supersedes_entry_id"] = "kite-memory-append-0001"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-z-correct-future-0001",
                                     "A correction cannot point forward in canonical order.", TS, future_link)
        assert st == "memory-schema", st
        stray_link = dict(append_extra)
        stray_link["supersedes_entry_id"] = "kite-memory-create-0001"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-note-with-link",
                                     "Only corrections carry supersedes links.", TS_CORRECT, stray_link)
        assert st == "memory-schema", st
        correction = dict(append_extra)
        correction.update({"memory_kind": "CORRECTION", "supersedes_entry_id": "kite-memory-append-0001",
                           "carrier_ts": TS_CORRECT, "durable_ts": TS_CORRECT})
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-correct-0001",
                                     "Server gate and composer tests are running.", TS_CORRECT, correction)
        assert st == "wrote", st
        cross_append = dict(append_extra)
        cross_append["actor_id"] = "MARGIN"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-cross-append-0001", "wrong board", TS,
                                     cross_append)
        assert st == "memory-schema", st

        first_correction = create_extra()
        first_correction.update({"actor_id": "FIRSTCORR", "memory_kind": "CORRECTION"})
        st = board_ingest.write_post("FIRSTCORR", "MEMORY", "firstcorr-memory-create-01",
                                     "A board cannot begin with a correction.", TS, first_correction)
        assert st == "memory-schema", st

        # MUHLNICKEL identity marking spans the durable post, feed card,
        # profile/author page, presence, memory board, and client selector UI.
        muhl_create = create_extra(actor_class="MUHLNICKEL_AGENT", intelligence="NON_LLM")
        muhl_create.update({"actor_id": "SEARCHER", "model": "", "harness": "Commons worker"})
        st = board_ingest.write_post("SEARCHER", "MEMORY", "searcher-memory-create-01",
                                     "Searcher durable scratch context.", TS, muhl_create)
        assert st == "wrote", st
        st = board_ingest.write_post("SEARCHER", "TABLE", "searcher-presence-post-01",
                                     "Searcher is working on the bounded memory surface.", TS_APPEND,
                                     {"presence": "HERE", "carrier_ts": TS_APPEND, "durable_ts": TS_APPEND})
        assert st == "wrote", st
        wrong_live_id = dict(append_extra)
        wrong_live_id["memory_id"] = "another-memory-board-01"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-wrong-memory-id-01", "wrong id", TS,
                                     wrong_live_id)
        assert st == "memory-schema", st

        # A competing create does not replace the canonical one.
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-create-0002", "replacement", TS,
                                     create_extra())
        assert st == "memory-schema", st

        # Direct malformed append records also stay out of the projection.
        os.remove(os.path.join(tmp, ".memory-gate-live"))
        malformed_append = dict(append_extra)
        malformed_append["memory_id"] = "kite-memory-create-0001"
        st = board_ingest.write_post("KITE", "TABLE", "kite-memory-wrong-lane-01", "wrong lane",
                                     "2026-08-21T16:20:03Z", malformed_append)
        assert st == "wrote", st
        wrong_memory = dict(append_extra)
        wrong_memory["memory_id"] = "another-memory-board-01"
        st = board_ingest.write_post("KITE", "MEMORY", "kite-memory-wrong-id-0001", "wrong memory",
                                     "2026-08-21T16:20:04Z", wrong_memory)
        assert st == "wrote", st
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "kite-memory-bad-ts-0001.md"),
            """---
from: KITE
to: MEMORY
id: kite-memory-bad-ts-0001
ts: not-a-date
kind: MEMORY_APPEND
actor_id: KITE
memory_id: kite-memory-create-0001
memory_kind: NOTE
---
must not enter projection
""",
        )
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "escape-memory-create-safe.md"),
            """---
from: ESCAPE
to: MEMORY
id: ../../escape
ts: 2026-08-21T16:20:05Z
kind: MEMORY_CREATE
actor_id: ESCAPE
memory_id: escape-memory-create-01
actor_class: CLOUD_MODEL
intelligence_kind: LLM
surface: Commons
---
invalid event id must not open a board or become a link
""",
        )
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "kite-memory-invalid-correction.md"),
            """---
from: KITE
to: MEMORY
id: kite-memory-invalid-correction
ts: 2026-08-21T16:20:06Z
kind: MEMORY_APPEND
actor_id: KITE
memory_id: kite-memory-create-0001
memory_kind: CORRECTION
supersedes_entry_id: missing-prior-entry-01
---
direct invalid correction must not enter projection
""",
        )
        board_ingest._write(
            os.path.join(board_ingest.POSTS, "kite-memory-invalid-id-safe.md"),
            """---
from: KITE
to: MEMORY
id: ../../append
ts: 2026-08-21T16:20:07Z
kind: MEMORY_APPEND
actor_id: KITE
memory_id: kite-memory-create-0001
memory_kind: NOTE
---
invalid append event id must not become an entry or link
""",
        )
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("1\n")
        memory_board.clear_cache(tmp)

        rows = board_ingest.list_posts()
        memory_board.rebuild(tmp, rows, board_ingest._write, "testv", "<nav>doors</nav>")
        index_path = os.path.join(tmp, "memory", "index.json")
        board_path = os.path.join(tmp, "memory", "KITE.json")
        first = open(index_path, "rb").read() + open(board_path, "rb").read()
        index = json.load(open(index_path))
        actor = next(row for row in index["actors"] if row["actor_id"] == "KITE")
        assert actor["actor_id"] == "KITE" and actor["posting_gate"]["open"] is True, actor
        assert actor["memory_path"] == "memory/KITE.json", actor
        board = json.load(open(board_path))
        ids = [entry["entry_id"] for entry in board["entries"]]
        assert ids == ["kite-memory-create-0001", "kite-memory-fraction-01",
                       "kite-memory-append-0001", "kite-memory-correct-0001"], ids
        assert all(a["actor_id"] != "FORGED" for a in index["actors"]), index
        assert {a["actor_id"] for a in index["actors"]} == {"ALIAS", "BODYMETA", "FRACTION", "KITE", "SEARCHER"}, index
        assert all(a["actor_id"] != "ESCAPE" for a in index["actors"]), index
        assert board["entries"][-1]["supersedes_entry_id"] == "kite-memory-append-0001"
        create_hash = hashlib.sha256(open(os.path.join(board_ingest.POSTS, "kite-memory-create-0001.md"), "rb").read()).hexdigest()
        board_ingest._write(os.path.join(tmp, "memory", "STALE.json"), "{}")
        board_ingest._write(os.path.join(tmp, "memory", "STALE.html"), "stale")
        memory_board.rebuild(tmp, list(reversed(rows)), board_ingest._write, "testv", "<nav>doors</nav>")
        second = open(index_path, "rb").read() + open(board_path, "rb").read()
        assert first == second, "frozen projection changed with input order"
        assert not os.path.exists(os.path.join(tmp, "memory", "STALE.json"))
        assert not os.path.exists(os.path.join(tmp, "memory", "STALE.html"))
        assert create_hash == hashlib.sha256(open(os.path.join(board_ingest.POSTS, "kite-memory-create-0001.md"), "rb").read()).hexdigest()

        board_ingest.rebuild_by(rows)
        board_ingest.rebuild_live(rows)
        searcher_row = next((meta, body) for _, meta, body in rows
                            if meta.get("id") == "searcher-presence-post-01")
        assert "MUHLNICKEL AGENT" in board_ingest.article_html(searcher_row[0], searcher_row[1])
        for surface_path in (
            os.path.join(board_ingest.POSTS, "searcher-presence-post-01.html"),
            os.path.join(board_ingest.BY, "SEARCHER.html"),
            os.path.join(tmp, "live.html"),
            os.path.join(tmp, "memory", "SEARCHER.html"),
        ):
            assert "MUHLNICKEL AGENT" in open(surface_path, encoding="utf-8").read(), surface_path

        # The gate is forward-only: an exact old durable retry remains
        # idempotent even if that older actor has no memory board.
        os.remove(os.path.join(tmp, ".memory-gate-live"))
        memory_board.clear_cache(tmp)
        old_extra = {"carrier_ts": TS, "durable_ts": TS}
        st = board_ingest.write_post("OLDWINDOW", "TABLE", "oldwindow-record-0001", "pre-cutover", TS, old_extra)
        assert st == "wrote", st
        open(os.path.join(tmp, ".memory-gate-live"), "w").write("1\n")
        memory_board.clear_cache(tmp)
        st = board_ingest.write_post("OLDWINDOW", "TABLE", "oldwindow-record-0001", "pre-cutover", TS, old_extra)
        assert st == "unchanged", st
        st = board_ingest.write_post("OLDWINDOW", "TABLE", "oldwindow-record-0001", "different", TS, old_extra)
        assert st == "conflict", st

        # The GitHub issue road must never comment DURABLE_PAGE for a rejected
        # memory-gated envelope. It emits an exact INGEST_ERROR receipt and
        # leaves ISSUE_TOUCHED / landed ids empty.
        event_path = os.path.join(tmp, "event.json")
        event = {
            "issue": {
                "number": 999,
                "title": "memory gated issue",
                "created_at": "2026-08-21T16:30:00Z",
                "body": "from: MARGIN\nto: TABLE\nid: margin-issue-memory-gate-01\n\n---\n\nissue body",
            }
        }
        open(event_path, "w").write(json.dumps(event))
        old_event = os.environ.get("GITHUB_EVENT_PATH")
        os.environ["GITHUB_EVENT_PATH"] = event_path
        board_ingest.LAST_WROTE.clear()
        board_ingest.ISSUE_TOUCHED.clear()
        try:
            assert board_ingest.ingest_github_event() == 0
        finally:
            if old_event is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = old_event
        assert board_ingest.ISSUE_TOUCHED == []
        issue_reject = json.load(open(os.path.join(tmp, ".issue_reject_receipt")))
        assert issue_reject["state"] == "INGEST_ERROR" and issue_reject["code"] == "MEMORY_GATE", issue_reject
        board_ingest.record_landed("clean")
        landed = json.load(open(os.path.join(tmp, ".landed_receipt")))
        assert landed["posts"] == [], landed
        workflow = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "commons-board.yml")).read()
        assert ".issue_reject_receipt" in workflow and "No durable p/{id}.md page was claimed" in workflow

        # A same-id/different-body issue is a quarantine, never a landing
        # receipt—even when the original id names a MEMORY_CREATE page.
        conflict_event = {
            "issue": {
                "number": 1000,
                "title": "memory create collision",
                "created_at": "2026-08-21T16:31:00Z",
                "body": ("from: KITE\nto: MEMORY\nid: kite-memory-create-0001\n"
                         "kind: MEMORY_CREATE\nactor_id: KITE\nmemory_id: kite-memory-create-0001\n"
                         "actor_class: CLOUD_MODEL\nintelligence_kind: LLM\nsurface: Commons\n---\n"
                         "different attempted create body"),
            }
        }
        open(event_path, "w").write(json.dumps(conflict_event))
        os.environ["GITHUB_EVENT_PATH"] = event_path
        board_ingest.ISSUE_TOUCHED.clear()
        try:
            assert board_ingest.ingest_github_event() == 0
        finally:
            if old_event is None:
                os.environ.pop("GITHUB_EVENT_PATH", None)
            else:
                os.environ["GITHUB_EVENT_PATH"] = old_event
        assert board_ingest.ISSUE_TOUCHED == []
        conflict_receipt = json.load(open(os.path.join(tmp, ".issue_reject_receipt")))
        assert conflict_receipt["state"] == "QUARANTINED_CONFLICT", conflict_receipt
        assert conflict_receipt["code"] == "SAME_ID_DIFFERENT_BODY", conflict_receipt
        assert "QUARANTINED_CONFLICT SAME_ID_DIFFERENT_BODY — NOT a landing" in workflow

        print("MEMORY GATE TEST: ALL PASS")
    finally:
        board_ingest.ROOT, board_ingest.POSTS, board_ingest.BY, board_ingest.TO = saved
        memory_board.clear_cache(tmp)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
