#!/usr/bin/env python3
"""Contract for host/equipment_ledger.py.

The fixtures are built the way the carrier builds its posts: one JSON
response, a SHA-256 of it, 28,000-character parts in wrappers, and each posted
part appearing as messages of at most 4,000 characters. Every fixture is
synthetic. A drift test runs the carrier's own request parser beside the
ledger's on the same texts, so the two cannot disagree about which envelopes
the carrier executes.
"""

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from host import equipment_ledger as ledger  # noqa: E402
from integrations.shared_equipment import slack_carrier  # noqa: E402

ASKER = "Bernays <asker@example.com>"
CARRIER = "Commons Grok <carrier@example.com>"
FOOTER = "\n*Sent using* <@U0BSAL3CZ4Y|ChatGPT>"


def request(rid, name="github_read_file", cid="call", arguments=None, before="", footer=FOOTER):
    body = json.dumps({"request_id": rid, "call_id": cid, "name": name,
                       "arguments": arguments if arguments is not None else {"path": "README.md"}})
    return before + "<commons_equipment_request>" + body + "</commons_equipment_request>" + footer


def answer(rid, result, cid="call", part_size=28000, slack_size=4000, fence=False):
    """Message texts for one carrier answer, split the way the thread shows it."""
    response = json.dumps({"request_id": rid, "call_id": cid, "result": result},
                          ensure_ascii=False)
    digest = hashlib.sha256(response.encode("utf-8")).hexdigest()
    parts = [response[i:i + part_size] for i in range(0, len(response), part_size)]
    messages = []
    for index, part in enumerate(parts, start=1):
        text = ('<commons_equipment_result request_id=%s call_id=%s part="%d/%d" sha256="%s">\n%s\n'
                "</commons_equipment_result>" % (json.dumps(rid), json.dumps(cid), index,
                                                 len(parts), digest, part))
        if fence:
            text = "```\n" + text + "\n```"
        messages.extend(text[i:i + slack_size] for i in range(0, len(text), slack_size))
    return messages


def ok(payload=None):
    return {"isError": False, "result": payload if payload is not None else {"sha": "abc", "size": 12}}


def api_page(rows, has_more=False, start=1789000000):
    """Web API replies JSON; Slack escapes &, < and > in text."""
    out = []
    for offset, (author, text) in enumerate(rows):
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.append({"ts": "%d.%06d" % (start + offset * 10, offset), "username": author,
                    "text": escaped})
    return json.dumps({"ok": True, "messages": out, "has_more": has_more,
                       "response_metadata": {"next_cursor": "abc" if has_more else ""}})


def detailed_page(rows, start=1789000000, more=False, fetched=None):
    """Connector detailed text. `fetched` > printed replies reproduces the
    connector's silent cut: the header and "of N" count what it fetched."""
    total = fetched if fetched is not None else len(rows) - 1
    blocks = []
    for offset, (author, text) in enumerate(rows):
        head = "=== THREAD PARENT MESSAGE ===" if offset == 0 else \
            "--- Reply %d of %d ---" % (offset, total)
        block = "%s\nFrom: %s (U%07d)\nTime: 2026-09-10 12:00:00 EDT\nMessage TS: %d.%06d\n%s" % (
            head, author, offset, start + offset * 10, offset, text)
        if offset == 0:
            block += "\n\n=== THREAD REPLIES (%d total) ===\n" % total
        blocks.append(block)
    text = "\n\n".join(blocks) + "\n"
    info = "There are more messages in this thread." if more else \
        "There are no more messages in this thread.\n"
    return json.dumps({"messages": text, "pagination_info": info})


def concise_page(rows, more=False):
    parent_author, parent = rows[0]
    text = "THREAD: " + parent + " [" + parent_author + "]\n"
    for author, body in rows[1:]:
        text += "\n> " + author + ": " + body
    text += "\n"
    info = "There are more messages in this thread. To view the next page, use cursor: `x`" \
        if more else "There are no more messages in this thread.\n"
    return json.dumps({"messages": text, "pagination_info": info})


def run(*pages, now=None, overdue_after_s=ledger.OVERDUE_AFTER_S):
    merged = ledger.merge_pages([ledger.read_page(page) for page in pages])
    return ledger.build(merged[0], merged[1], now, overdue_after_s)


def row(result, rid):
    found = [r for r in result["rows"] if r["request_id"] == rid]
    assert len(found) == 1, (rid, [r["request_id"] for r in result["rows"]])
    return found[0]


PARENT = ("Astra <root@example.com>", "M3 equipment thread")


class TestAnswersArriveWhole(unittest.TestCase):
    def test_an_answer_split_across_slack_messages_is_joined_and_verified(self):
        big = ok({"content": "x" * 9500})
        messages = answer("r1", big)
        self.assertGreater(len(messages), 2, "fixture must actually split")
        rows = [PARENT, (ASKER, request("r1"))] + [(CARRIER, m) for m in messages]
        result = run(api_page(rows))
        r = row(result, "r1")
        self.assertEqual(r["state"], "DELIVERED")
        self.assertEqual(r["digest"], "MATCH")
        self.assertEqual(r["parts"], {"expected": 1, "present": 1, "closed": 1})
        self.assertEqual(r["answer_after_s"], 10.0)

    def test_api_text_is_decoded_one_layer_before_matching(self):
        tricky = ok({"body": "a <b> & c &lt;literal&gt;"})
        rows = [PARENT, (ASKER, request("r2"))] + [(CARRIER, m) for m in answer("r2", tricky)]
        page = api_page(rows)
        self.assertIn("&lt;commons_equipment_request&gt;", page)
        r = row(run(page), "r2")
        self.assertEqual((r["state"], r["digest"]), ("DELIVERED", "MATCH"))

    def test_a_fenced_metadata_answer_is_read_inside_its_fence(self):
        rows = [PARENT, (ASKER, request("cat", name="equipment_catalog", arguments={}))]
        rows += [(CARRIER, m) for m in answer("cat", {"tools": [{"name": "a"}]}, fence=True)]
        self.assertEqual(row(run(api_page(rows)), "cat")["state"], "DELIVERED")

    def test_multi_part_answers_join_in_part_order(self):
        rows = [PARENT, (ASKER, request("r3"))]
        rows += [(CARRIER, m) for m in answer("r3", ok({"blob": "y" * 7000}), part_size=3000)]
        r = row(run(api_page(rows)), "r3")
        self.assertEqual(r["parts"]["expected"], 3)
        self.assertEqual((r["state"], r["digest"]), ("DELIVERED", "MATCH"))


class TestWhatAnAnswerCanSay(unittest.TestCase):
    def ledger_for(self, result):
        rows = [PARENT, (ASKER, request("q"))] + [(CARRIER, m) for m in answer("q", result)]
        return row(run(api_page(rows)), "q")

    def test_failure_uses_the_carriers_rule_and_names_the_code(self):
        r = self.ledger_for({"isError": True, "result": {
            "error": {"class": "FileNotFoundError", "code": "codex_executable_unavailable"}}})
        self.assertEqual((r["state"], r["error"]), ("ERROR", "codex_executable_unavailable"))

    def test_unknown_effect_is_uncertain_not_failed(self):
        r = self.ledger_for({"isError": True, "uncertain": True,
                             "error": "tool_effect_unknown_after_interruption"})
        self.assertEqual((r["state"], r["error"]),
                         ("UNCERTAIN", "tool_effect_unknown_after_interruption"))

    def test_a_status_read_describing_a_failed_job_is_delivered(self):
        r = self.ledger_for({"isError": False, "result": {"job": "failed", "ok_to_retry": False}})
        self.assertEqual(r["state"], "DELIVERED")

    def test_altered_bytes_do_not_reproduce_the_digest(self):
        messages = answer("q", ok())
        messages[0] = messages[0].replace('"size": 12', '"size": 13')
        rows = [PARENT, (ASKER, request("q"))] + [(CARRIER, m) for m in messages]
        r = row(run(api_page(rows)), "q")
        self.assertEqual((r["state"], r["digest"]), ("DIGEST_MISMATCH", "MISMATCH"))


class TestWhatIsMissing(unittest.TestCase):
    def test_a_missing_part_is_partial(self):
        messages = answer("m", ok({"blob": "z" * 5000}), part_size=4000, slack_size=100000)
        self.assertEqual(len(messages), 2)
        rows = [PARENT, (ASKER, request("m")), (CARRIER, messages[0])]
        r = row(run(api_page(rows)), "m")
        self.assertEqual(r["state"], "PARTIAL")
        self.assertEqual(r["parts"], {"expected": 2, "present": 1, "closed": 1})
        self.assertEqual(r["digest"], "NOT_CHECKED")

    def test_a_part_whose_end_never_arrived_is_partial(self):
        messages = answer("t", ok({"blob": "w" * 9000}))
        rows = [PARENT, (ASKER, request("t"))] + [(CARRIER, m) for m in messages[:-1]]
        r = row(run(api_page(rows)), "t")
        self.assertEqual(r["state"], "PARTIAL")
        self.assertEqual(r["parts"]["closed"], 0)

    def test_no_answer_is_pending_with_its_age_against_the_copy(self):
        rows = [PARENT, (ASKER, request("p")), (ASKER, "unrelated"), (ASKER, "later"),
                ("Other <o@example.com>", "much later")]
        result = run(api_page(rows))
        r = row(result, "p")
        self.assertEqual(r["state"], "PENDING")
        self.assertEqual(r["age_s"], 30.0)
        self.assertFalse(r["overdue"])
        self.assertEqual(result["source"]["reference_source"], "newest_message")
        late = row(run(api_page(rows), now=1789000000 + 10 + 301), "p")
        self.assertTrue(late["overdue"])
        tight = row(run(api_page(rows), overdue_after_s=20), "p")
        self.assertTrue(tight["overdue"])

    def test_an_answer_with_no_request_in_the_copy_is_an_orphan(self):
        rows = [PARENT] + [(CARRIER, m) for m in answer("older", ok())]
        result = run(api_page(rows))
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["orphan_results"][0]["request_id"], "older")
        self.assertEqual(result["orphan_results"][0]["state"], "DELIVERED")


class TestWhatTheCarrierExecutes(unittest.TestCase):
    def test_prose_before_the_envelope_means_it_was_never_asked(self):
        rows = [PARENT,
                (ASKER, request("rowan", before="Context line first.\n")),
                (ASKER, "delivery check: still no result"),
                (ASKER, request("rowan"))]
        rows += [(CARRIER, m) for m in answer("rowan", ok())]
        result = run(api_page(rows))
        r = row(result, "rowan")
        self.assertEqual(len(r["asked"]), 1)
        self.assertEqual(r["asked"][0]["ts"], "1789000030.000003")
        self.assertEqual(r["state"], "DELIVERED")
        self.assertEqual(result["quoted_envelopes"][0]["request_id"], "rowan")

    def test_a_repost_keeps_the_newest_whole_answer_and_counts_all(self):
        first = answer("again", ok({"blob": "v" * 5000}), part_size=4000, slack_size=100000)
        rows = [PARENT, (ASKER, request("again")), (CARRIER, first[0]),
                (ASKER, request("again"))]
        rows += [(CARRIER, m) for m in answer("again", ok({"blob": "v" * 5000}),
                                              part_size=4000, slack_size=100000)]
        r = row(run(api_page(rows)), "again")
        self.assertEqual((r["state"], r["answers"], len(r["asked"])), ("DELIVERED", 2, 2))
        self.assertEqual(r["answer_after_s"], 10.0)

    def test_an_unreadable_envelope_is_listed_with_its_reason(self):
        rows = [PARENT, (ASKER, "<commons_equipment_request>{not json</commons_equipment_request>")]
        result = run(api_page(rows))
        self.assertEqual(result["rows"], [])
        self.assertIn("not JSON", result["unreadable_requests"][0]["reason"])

    def test_the_ledger_and_the_carrier_agree_on_every_request_text(self):
        body = '{"request_id":"a","call_id":"b","name":"n","arguments":{}}'
        texts = [
            "<commons_equipment_request>" + body + "</commons_equipment_request>",
            "  <commons_equipment_request>" + body + "</commons_equipment_request>\nfooter",
            "&lt;commons_equipment_request&gt;" + body + "&lt;/commons_equipment_request&gt;",
            "prose\n<commons_equipment_request>" + body + "</commons_equipment_request>",
            "<commons_equipment_request>" + body,
            "<commons_equipment_request>[1]</commons_equipment_request>",
            '<commons_equipment_request>{"request_id":"","call_id":"b","name":"n"}'
            "</commons_equipment_request>",
            "no envelope at all",
        ]
        for text in texts:
            try:
                carrier = slack_carrier.parse_request(text)
            except ValueError:
                carrier = "RAISES"
            mine = ledger.parse_request(text)
            if carrier == "RAISES":
                self.assertIsNotNone(mine, text)
                self.assertIsNone(mine[0], text)
            elif carrier is None:
                self.assertTrue(mine is None or mine[0] == "QUOTED", text)
            else:
                self.assertEqual(mine[0], carrier, text)


class TestEveryShapeOfTheThread(unittest.TestCase):
    def rows(self):
        rows = [PARENT, (ASKER, request("d1")), (ASKER, request("d2", name="token_pool_status",
                                                                  arguments={"provider": "codex"}))]
        rows += [(CARRIER, m) for m in answer("d1", ok({"blob": "u" * 8500}))]
        return rows

    def test_detailed_connector_text_keeps_the_clock(self):
        result = run(detailed_page(self.rows()))
        r = row(result, "d1")
        self.assertEqual((r["state"], r["digest"]), ("DELIVERED", "MATCH"))
        self.assertEqual(r["answer_after_s"], 20.0)
        self.assertEqual(r["asked"][0]["by"], "Bernays")
        self.assertEqual(r["asked"][0]["via"], "ChatGPT")
        pending = row(result, "d2")
        self.assertEqual(pending["state"], "PENDING")
        self.assertEqual(pending["age_s"], 30.0)
        self.assertEqual(result["source"]["pages"][0]["more"], False)

    def test_concise_connector_text_has_no_clock_and_says_so(self):
        result = run(concise_page(self.rows(), more=True))
        r = row(result, "d1")
        self.assertEqual((r["state"], r["digest"]), ("DELIVERED", "MATCH"))
        self.assertEqual(r["answer_after_s"], "UNKNOWN")
        pending = row(result, "d2")
        self.assertEqual((pending["age_s"], pending["overdue"]), ("UNKNOWN", "UNKNOWN"))
        self.assertEqual(result["source"]["reference_source"], "UNKNOWN")
        self.assertEqual(result["source"]["pages"][0]["more"], True)

    def test_a_tool_results_file_wrapping_connector_text_is_read_as_is(self):
        wrapped = json.dumps([{"type": "text", "text": concise_page(self.rows())}])
        result = run(wrapped)
        self.assertEqual(row(result, "d1")["state"], "DELIVERED")
        self.assertEqual(result["source"]["pages"][0]["more"], False)

    def test_api_pages_merge_by_timestamp_and_the_newest_end_is_named(self):
        rows = self.rows()
        older = api_page(rows[:3], has_more=True)
        newer = json.loads(api_page(rows, has_more=False))
        newer["messages"] = newer["messages"][2:]
        result = run(json.dumps(newer), older)
        self.assertEqual(result["source"]["messages"], len(rows))
        self.assertEqual(result["source"]["newest_end_seen"], True)
        self.assertEqual(row(result, "d1")["state"], "DELIVERED")
        self.assertEqual(run(older)["source"]["newest_end_seen"], "UNKNOWN")
        self.assertEqual(run(detailed_page(rows))["source"]["newest_end_seen"], "UNKNOWN")

    def test_a_page_that_printed_fewer_replies_than_it_counted_is_a_gap(self):
        # The connector counted 9 replies, printed 3, and still said "no more".
        rows = [PARENT, (ASKER, request("g1")), (ASKER, request("g2")), (CARRIER, "noise")]
        result = run(detailed_page(rows, fetched=9))
        gaps = result["source"]["gaps"]
        self.assertEqual(gaps, [{"after_ts": "1789000030.000003", "dropped": 6}])
        self.assertEqual(result["source"]["pages"][0]["dropped"], 6)
        self.assertEqual(result["source"]["pages"][0]["more"], False)
        for rid in ("g1", "g2"):
            self.assertIs(row(result, rid)["may_be_in_gap"], True,
                          "the answer is newer than its request and may be among the dropped replies")
        text = ledger.as_text(result)
        self.assertIn("GAP: 6 replies dropped after 1789000030.000003", text)
        self.assertIn("(answer may be in a GAP)", text)

    def test_a_gap_older_than_the_request_cannot_hold_its_answer(self):
        rows = [PARENT, (CARRIER, "older noise")]
        cut = detailed_page(rows, fetched=5)
        newer = detailed_page([PARENT, (CARRIER, "x"), (CARRIER, "y"), (ASKER, request("late"))],
                              start=1789000500)
        result = run(cut, newer)
        self.assertIs(row(result, "late")["may_be_in_gap"], False)
        self.assertEqual(len(result["source"]["gaps"]), 1)

    def cut_and_rest(self):
        """A newest page cut after reply 2, and the 3 replies it dropped."""
        rows = [PARENT, (ASKER, request("f1")), (ASKER, request("f2"))]
        dropped = [(CARRIER, m) for m in answer("f1", ok())] + [(ASKER, "note"), (ASKER, "note 2")]
        cut = detailed_page(rows, fetched=2 + len(dropped))
        rest = detailed_page([PARENT] + dropped, start=1789000030)
        return cut, rest, len(dropped)

    def test_a_follow_up_read_from_the_last_printed_reply_fills_the_gap(self):
        cut, rest, dropped = self.cut_and_rest()
        pages = [tuple(ledger.read_page(cut)) + (None,),
                 tuple(ledger.read_page(rest)) + ("1789000020.000002",)]
        merged = ledger.merge_pages(pages)
        result = ledger.build(merged[0], merged[1])
        self.assertEqual(result["source"]["gaps"],
                         [{"after_ts": "1789000020.000002", "dropped": dropped, "filled_by_page": 1}])
        self.assertEqual(row(result, "f1")["state"], "DELIVERED")
        self.assertNotIn("may_be_in_gap", row(result, "f2"))
        self.assertIn("GAP FILLED: %d replies dropped after 1789000020.000002; page 2 holds them" % dropped,
                      ledger.as_text(result))

    def test_a_follow_up_that_started_later_or_is_unnamed_does_not_fill_it(self):
        cut, rest, _ = self.cut_and_rest()
        for oldest in ("1789000020.520000", None):
            pages = [tuple(ledger.read_page(cut)) + (None,), tuple(ledger.read_page(rest)) + (oldest,)]
            merged = ledger.merge_pages(pages)
            result = ledger.build(merged[0], merged[1])
            self.assertNotIn("filled_by_page", result["source"]["gaps"][0], oldest)
            self.assertIs(row(result, "f2")["may_be_in_gap"], True, oldest)

    def test_page_arguments_name_the_follow_up_start(self):
        self.assertEqual(ledger.page_argument(r"C:\x\page.txt@oldest=1788840607.515809"),
                         (r"C:\x\page.txt", "1788840607.515809"))
        self.assertEqual(ledger.page_argument(r"C:\x\page.txt"), (r"C:\x\page.txt", None))
        self.assertEqual(ledger.page_argument("a@oldest=soon"), ("a@oldest=soon", None))

    def test_a_whole_page_reports_no_gap(self):
        result = run(detailed_page(self.rows()))
        self.assertEqual(result["source"]["gaps"], [])
        self.assertNotIn("may_be_in_gap", row(result, "d2"))
        self.assertNotIn("dropped", result["source"]["pages"][0])

    def test_repeated_concise_parents_are_dropped_and_replies_kept(self):
        page = concise_page(self.rows())
        result = run(page, page)
        self.assertEqual(result["source"]["messages"], 2 * len(self.rows()) - 1)
        self.assertEqual(len(row(result, "d1")["asked"]), 2,
                         "a byte-identical repost is kept as a repost, never merged away")


class TestWhatTheLedgerNeverCopies(unittest.TestCase):
    def test_no_argument_value_and_no_result_content_leave_the_thread(self):
        args = {"credential_ref": "kaggle/api-token", "recipient_public_key": "PUBKEY-VALUE",
                "transfer_id": "TRANSFER-VALUE"}
        sealed = ok({"credential_ref": "kaggle/api-token", "ciphertext": "CIPHERTEXT-VALUE",
                     "nonce": "NONCE-VALUE"})
        rows = [PARENT, (ASKER, request("c", name="credential_retrieve_sealed", arguments=args))]
        rows += [(CARRIER, m) for m in answer("c", sealed)]
        result = run(api_page(rows))
        out = json.dumps(result)
        for secret in ("PUBKEY-VALUE", "TRANSFER-VALUE", "CIPHERTEXT-VALUE", "NONCE-VALUE"):
            self.assertNotIn(secret, out)
        r = row(result, "c")
        self.assertEqual(r["credential_ref"], "kaggle/api-token")
        self.assertEqual(r["argument_names"],
                         ["credential_ref", "recipient_public_key", "transfer_id"])
        self.assertEqual(r["state"], "DELIVERED")

    def test_notes_are_capped(self):
        text = request("n", footer="\n" + "long note " * 40 + FOOTER)
        r = row(run(api_page([PARENT, (ASKER, text)])), "n")
        self.assertEqual(len(r["asked"][0]["note"]), ledger.NOTE_CAP)
        self.assertTrue(r["asked"][0]["note"].endswith("…"))


class TestShape(unittest.TestCase):
    def test_every_state_is_counted_even_at_zero(self):
        result = run(api_page([PARENT]))
        self.assertEqual(tuple(result["counts"]["by_state"]), ledger.STATES)
        self.assertEqual(result["schema"], "commons.equipment_ledger.v1")

    def test_the_command_line_prints_json_and_text(self):
        folder = tempfile.mkdtemp(prefix="equipment-ledger-")
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        path = os.path.join(folder, "page.json")
        rows = [PARENT, (ASKER, request("cli")), (ASKER, request("wait"))]
        rows += [(CARRIER, m) for m in answer("cli", ok())]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(api_page(rows))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ledger.main([path])
        self.assertEqual(json.loads(buffer.getvalue())["counts"]["requests"], 2)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ledger.main([path, "--text", "--now", "2026-09-11T00:00:00Z"])
        text = buffer.getvalue()
        self.assertIn("DELIVERED", text)
        self.assertIn("PENDING", text)
        self.assertIn("OVERDUE", text)


if __name__ == "__main__":
    unittest.main()
