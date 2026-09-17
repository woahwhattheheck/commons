from __future__ import annotations

import subprocess
import sys
import unittest

from revenue.inbound_reply_triage.core import INPUT_SCHEMA, TriageError, compile_triage


def _event(kind: str, at: str, key: str) -> dict[str, object]:
    return {"id": key, "type": kind, "at": at, "evidence_refs": [f"evidence:{key}"]}


def _lease() -> dict[str, object]:
    return {
        "holder": "swarm-z",
        "acquired_at": "2026-09-17T02:00:00Z",
        "expires_at": "2026-09-17T06:00:00Z",
        "evidence_refs": ["slack:lease:recovery"],
    }


def _lane(*, org: str = "Acme", route: str = "sales@example.com", events=None, lease=None):
    return {
        "id": "lane-a",
        "org_key": org,
        "route_key": route,
        "domain": "example.com",
        "purpose_key": "PAID-WORK",
        "thread_key": "thread:lane-a",
        "lease": lease,
        "events": list(events or []),
    }


def _source(lane):
    return {
        "schema": INPUT_SCHEMA,
        "evaluation_at": "2026-09-17T04:00:00Z",
        "stale_after_minutes": 120,
        "lanes": [lane],
    }


class InboundReply15431RecoveryTests(unittest.TestCase):
    def test_trim_erased_unicode_never_aliases_a_clean_binding(self):
        cases = [
            ("org", "Acme\u2028", "sales@example.com"),
            ("org", "\u2029Acme", "sales@example.com"),
            ("org", "Acme\u00a0", "sales@example.com"),
            ("org", "\u3000Acme", "sales@example.com"),
            ("org", "Acme\u1680", "sales@example.com"),
            ("org", "\u1680Acme", "sales@example.com"),
            ("route", "Acme", "sales@example.com\u2028"),
            ("route", "Acme", "\u2029sales@example.com"),
            ("route", "Acme", "sales@example.com\u00a0"),
            ("route", "Acme", "\u3000sales@example.com"),
            ("route", "Acme", "sales@example.com\u1680"),
            ("route", "Acme", "\u1680sales@example.com"),
        ]
        for label, org, route in cases:
            with self.subTest(label=label, org=repr(org), route=repr(route)):
                with self.assertRaises(TriageError):
                    compile_triage(_source(_lane(org=org, route=route)))

    def test_plain_ascii_surrounding_space_is_the_only_trimmed_boundary_here(self):
        packet = compile_triage(_source(_lane(org=" Acme ", route=" sales@example.com ")))
        binding = packet["lanes"][0]["binding"]
        self.assertEqual(binding["org_key"], "Acme")
        self.assertEqual(binding["route_key"], "sales@example.com")

    def test_same_second_human_then_draft_cannot_mint_owner_review_ready(self):
        events = [
            _event("HUMAN_REPLY", "2026-09-17T03:00:00Z", "h"),
            _event("RESPONSE_DRAFT_READY", "2026-09-17T03:00:00Z", "d"),
        ]
        with self.assertRaisesRegex(TriageError, "strictly earlier HUMAN_REPLY"):
            compile_triage(_source(_lane(events=events, lease=_lease())))

    def test_same_second_draft_then_human_is_also_rejected(self):
        events = [
            _event("RESPONSE_DRAFT_READY", "2026-09-17T03:00:00Z", "d"),
            _event("HUMAN_REPLY", "2026-09-17T03:00:00Z", "h"),
        ]
        with self.assertRaisesRegex(TriageError, "prior HUMAN_REPLY|strictly earlier HUMAN_REPLY"):
            compile_triage(_source(_lane(events=events, lease=_lease())))

    def test_strict_human_before_draft_remains_valid_owner_review_state(self):
        events = [
            _event("HUMAN_REPLY", "2026-09-17T03:00:00Z", "h"),
            _event("RESPONSE_DRAFT_READY", "2026-09-17T03:00:01Z", "d"),
        ]
        row = compile_triage(_source(_lane(events=events, lease=_lease())))["owner_review_queue"][0]
        self.assertEqual(row["state"], "RESPONSE_READY_OWNER_REVIEW")
        self.assertEqual(row["next_gate"], "MUSE_REQUIRED_BEFORE_ANY_SEND")

    def test_recovery_suite_runs_under_optimized_python(self):
        if sys.flags.optimize:
            return
        proc = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "-v", self.__class__.__module__],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        combined = proc.stdout + proc.stderr
        self.assertIn("Ran 6 tests", combined)
        self.assertIn("OK", combined)


if __name__ == "__main__":
    unittest.main()
