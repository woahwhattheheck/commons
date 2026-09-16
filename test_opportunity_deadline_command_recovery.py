from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from revenue.opportunity_deadline_command import engine

AS_OF = "2026-09-13T12:00:00Z"
H = "a" * 64
H2 = "b" * 64


def policy(**overrides):
    value = {
        "schema_version": engine.POLICY_VERSION,
        "max_source_age_minutes": 10080,
        "critical_window_minutes": 1440,
        "high_window_minutes": 10080,
        "addenda_review_window_minutes": 20160,
    }
    value.update(overrides)
    return value


def source(source_id="official-1", authority="OFFICIAL", captured_at="2026-09-13T10:00:00Z", sha=H,
           url="https://buyer.example.gov/rfp", generation=1):
    return {
        "source_id": source_id,
        "authority": authority,
        "captured_at": captured_at,
        "sha256": sha,
        "url": url,
        "label": f"Source {source_id}",
        "generation": generation,
    }


def deadline(deadline_id="response-1", kind="RESPONSE", at="2026-09-20T12:00:00Z", source_id="official-1",
             generation=1, **optional):
    value = {
        "deadline_id": deadline_id,
        "kind": kind,
        "at": at,
        "source_id": source_id,
        "generation": generation,
    }
    value.update(optional)
    return value


def opportunity(**overrides):
    value = {
        "opportunity_id": "opp-1",
        "buyer": "Buyer",
        "solicitation_id": "RFP-1",
        "title": "Title",
        "owner_ref": "OWNER",
        "route_state": "TEAMING",
        "source_set_complete": True,
        "controlling_source_id": "official-1",
        "packet_state": "COMPLETE",
        "sources": [source()],
        "deadlines": [deadline()],
        "blocker_codes": [],
        "owner_action_refs": ["OWNER-REVIEW"],
    }
    value.update(overrides)
    return value


def packet(op):
    return {"schema_version": engine.INPUT_VERSION, "opportunities": [op]}


def row(op, pol=None):
    return engine.compile_portfolio(packet(op), pol or policy(), as_of=AS_OF)["rows"][0]


class RecoveryTests(unittest.TestCase):
    def test_incomplete_past_evidence_preempts_expired(self):
        op = opportunity(source_set_complete=False, deadlines=[deadline(at=AS_OF)])
        self.assertEqual(row(op)["operating_state"], "SOURCE_RECOVERY_REQUIRED")

    def test_secondary_past_evidence_preempts_expired(self):
        op = opportunity(
            sources=[source(), source("mirror", "SECONDARY", sha=H2, url="https://mirror.example/rfp")],
            deadlines=[deadline(at=AS_OF, source_id="mirror")],
        )
        self.assertEqual(row(op)["operating_state"], "SOURCE_RECOVERY_REQUIRED")

    def test_critical_window_is_exact_to_second(self):
        op = opportunity(deadlines=[deadline(at="2026-09-14T12:00:01Z")])
        got = row(op)
        self.assertEqual(got["operating_state"], "RESPONSE_WINDOW_OPEN")
        self.assertEqual(got["priority"], "HIGH")
        self.assertEqual(got["next_deadline"]["minutes_remaining"], 1441)

    def test_source_freshness_is_exact_to_second(self):
        op = opportunity(sources=[source(captured_at="2026-09-13T10:59:59Z")])
        got = row(op, policy(max_source_age_minutes=60))
        self.assertEqual(got["operating_state"], "SOURCE_RECOVERY_REQUIRED")
        self.assertIn("STALE_OFFICIAL_SOURCE", got["reason_codes"])

    def test_supersession_requires_later_official_source_generation(self):
        op = opportunity(deadlines=[
            deadline("response-1", at="2026-09-16T12:00:00Z", generation=1),
            deadline("response-2", at="2026-09-20T12:00:00Z", generation=2,
                     supersedes_deadline_id="response-1"),
        ])
        with self.assertRaisesRegex(engine.EvidenceError, "source generation must increase"):
            row(op)

    def test_supersession_accepts_later_official_source_generation(self):
        op = opportunity(
            sources=[
                source("official-1", generation=1),
                source("official-2", generation=2, sha=H2, url="https://buyer.example.gov/addendum"),
            ],
            deadlines=[
                deadline("response-1", at="2026-09-16T12:00:00Z", generation=1, source_id="official-1"),
                deadline("response-2", at="2026-09-20T12:00:00Z", generation=2, source_id="official-2",
                         supersedes_deadline_id="response-1"),
            ],
        )
        got = row(op)
        self.assertEqual(got["next_deadline"]["deadline_id"], "response-2")

    def test_read_is_bound_to_opened_inode(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "input.json"
            replacement = Path(tmp) / "replacement.json"
            p.write_text('{"value":1}', encoding="utf-8")
            replacement.write_text('{"value":2}', encoding="utf-8")
            real_open = os.open
            swapped = False

            def racing_open(path, flags, *args, **kwargs):
                nonlocal swapped
                fd = real_open(path, flags, *args, **kwargs)
                if not swapped:
                    os.replace(replacement, p)
                    swapped = True
                return fd

            with patch.object(engine.os, "open", side_effect=racing_open):
                self.assertEqual(engine.read_bounded_json(p), {"value": 1})
            self.assertEqual(p.read_text(encoding="utf-8"), '{"value":2}')

    def test_failed_write_does_not_unlink_replacement_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            moved = Path(tmp) / "created-but-moved.json"
            real_fdopen = os.fdopen

            class SwappingWriter:
                def __init__(self, fd, mode):
                    self._handle = real_fdopen(fd, mode)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    self._handle.close()
                    return False

                def write(self, data):
                    self._handle.write(data[:1])
                    self._handle.flush()
                    os.replace(p, moved)
                    p.write_bytes(b"replacement")
                    raise OSError("synthetic write failure")

                def flush(self):
                    self._handle.flush()

                def fileno(self):
                    return self._handle.fileno()

            with patch.object(engine.os, "fdopen", side_effect=lambda fd, mode: SwappingWriter(fd, mode)):
                with self.assertRaises(OSError):
                    engine.write_new_file(p, b"payload")
            self.assertEqual(p.read_bytes(), b"replacement")
            self.assertTrue(moved.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
