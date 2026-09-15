import datetime as dt
import unittest
from unittest import mock

from host import claim_work as cw


class ClaimKeyTests(unittest.TestCase):
    def test_issue_key_is_exact_and_rejects_bool(self):
        self.assertEqual(cw.issue_key(13840), "issue-13840")
        for bad in (0, -1, True, "12"):
            with self.assertRaises(ValueError):
                cw.issue_key(bad)

    def test_named_work_normalizes_nfkc_case_and_space(self):
        a = cw.work_key("  ＢＵＩＬＤ   Invoice Desk  ")
        b = cw.work_key("build invoice desk")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("work-build-invoice-desk-"))
        self.assertLessEqual(len(a), 96)

    def test_same_slug_prefix_gets_distinct_digest(self):
        a = cw.work_key("alpha " + "x" * 80)
        b = cw.work_key("alpha " + "x" * 79 + "y")
        self.assertNotEqual(a, b)
        self.assertEqual(a.rsplit("-", 1)[0], b.rsplit("-", 1)[0])

    def test_named_work_rejects_empty_controls_and_oversize(self):
        for bad in ("", "   ", "abc\nxyz", "x" * 201):
            with self.assertRaises(ValueError):
                cw.work_key(bad)

    def test_exactly_one_target(self):
        with self.assertRaises(ValueError):
            cw.claim_key()
        with self.assertRaises(ValueError):
            cw.claim_key(issue=1, work="x")


class AdapterTests(unittest.TestCase):
    def test_issue_take_delegates_to_existing_ledger(self):
        with mock.patch.object(cw.cs, "holding_write", return_value={"ok": True}) as call:
            out = cw.write_claim(
                object(), "ZRJ-Q3M8", "take", issue=13840,
                ttl_s=900, note="recover", push=False, attempts=5,
            )
        self.assertTrue(out["ok"])
        self.assertEqual(out["key"], "issue-13840")
        args, kwargs = call.call_args
        self.assertEqual(args[1:4], ("issue-13840", "ZRJ-Q3M8", "take"))
        self.assertEqual(kwargs["ttl_s"], 900)
        self.assertEqual(kwargs["attempts"], 5)
        self.assertFalse(kwargs["push"])

    def test_named_take_preserves_operation_in_note(self):
        with mock.patch.object(cw.cs, "holding_write", return_value={"ok": True}) as call:
            out = cw.write_claim(object(), "seat", "take", work="Build Foo", note="source lane")
        self.assertEqual(out["operation"], "build foo")
        note = call.call_args.kwargs["note"]
        self.assertIn("operation=build foo", note)
        self.assertIn("source lane", note)

    def test_competing_holder_stays_failure(self):
        collision = {"ok": False, "held_by": "earlier-seat"}
        with mock.patch.object(cw.cs, "holding_write", return_value=collision):
            out = cw.write_claim(object(), "later-seat", "take", issue=7)
        self.assertFalse(out["ok"])
        self.assertEqual(out["held_by"], "earlier-seat")

    def test_status_distinguishes_missing_released_and_live(self):
        rows = [
            {"key": "issue-1", "state": "RELEASED", "live": False},
            {"key": "issue-2", "state": "HELD", "live": True},
        ]
        with mock.patch.object(cw.cs, "holdings_list", return_value={"tip": "t", "holdings": rows}):
            self.assertFalse(cw.claim_status(object(), issue=1)["held"])
            self.assertTrue(cw.claim_status(object(), issue=2)["held"])
            self.assertIsNone(cw.claim_status(object(), issue=3)["record"])

    def test_future_and_expired_heartbeat_semantics(self):
        now = dt.datetime(2026, 9, 14, tzinfo=dt.timezone.utc)
        future = {"state": "HELD", "heartbeat_at": "2026-09-14T00:10:00Z", "ttl_s": 60}
        self.assertTrue(cw.cs._holding_live(future, now))
        later = dt.datetime(2026, 9, 14, 0, 10, tzinfo=dt.timezone.utc)
        old = {"state": "HELD", "heartbeat_at": "2026-09-14T00:00:00Z", "ttl_s": 60}
        self.assertFalse(cw.cs._holding_live(old, later))

    def test_same_holder_clock_regression_preserves_later_heartbeat(self):
        future = "2026-09-14T00:10:00Z"
        current = {
            "schema": cw.cs.HOLDING_SCHEMA, "key": "issue-8", "holder": "same-seat",
            "state": "HELD", "heartbeat_at": future, "taken_at": future, "ttl_s": 1800,
        }
        path = cw.cs._holding_path("issue-8")

        class FakeGit:
            root = "."
            def fetch(self, *_args, **_kwargs):
                return None

        observed = dt.datetime(2026, 9, 14, 0, 0, tzinfo=dt.timezone.utc)
        with mock.patch.object(cw.cs, "_remote_tip", return_value="tip"), \
             mock.patch.object(cw.cs, "_read_holdings", return_value={path: current}), \
             mock.patch.object(cw.cs, "_holdings_commit", return_value="commit") as commit_call:
            out = cw.cs.holding_write(
                FakeGit(), "issue-8", "same-seat", "renew", now=observed, push=False,
            )
        self.assertTrue(out["ok"])
        self.assertEqual(cw.cs._iso(commit_call.call_args.args[4]), future)


if __name__ == "__main__":
    unittest.main()
