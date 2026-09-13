from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.teaming_conversion.control import (
    ControlError, DuplicateKeyError, INPUT_SCHEMA, POLICY_SCHEMA, canonical_bytes,
    compile_bytes, compile_control, parse_json_bytes, parse_receipt_bytes,
    read_bounded_regular, render_markdown, verify_bytes, verify_control,
    write_exclusive_regular,
)

NOW = datetime(2026, 9, 13, 13, 0, 0, tzinfo=timezone.utc)
D, E, F = "a" * 64, "b" * 64, "c" * 64


def policy() -> dict:
    return {
        "schema_version": POLICY_SCHEMA,
        "max_reply_age_seconds": 7 * 86400,
        "max_source_age_seconds": 2 * 86400,
        "max_future_skew_seconds": 60,
        "required_asset_ids": ["asset-summary"],
        "required_clear_gate_ids": ["gate-prime"],
    }


def packet() -> dict:
    return {
        "schema_version": INPUT_SCHEMA,
        "opportunity": {
            "opportunity_id": "opp-iowa-18649", "counterparty_ref": "org-clarks",
            "thread_id": "thread-clarks-1", "source_digest": D,
            "source_checked_at": "2026-09-13T12:00:00Z",
        },
        "observations": [{
            "observation_id": "obs-1", "thread_id": "thread-clarks-1", "message_id": "msg-1",
            "sender_ref": "contact-prime-1", "sender_role": "PRIME_CONTACT",
            "received_at": "2026-09-13T12:30:00Z", "content_sha256": E,
            "source_class": "GMAIL", "interpretation": "POSITIVE_CONTINUE",
            "supersedes_observation_id": None, "clarification_codes": [],
        }],
        "assets": [
            {
                "asset_id": "asset-summary", "title": "Prospect-safe capability summary",
                "version": "v1", "sha256": F, "prep_state": "READY",
                "release_class": "PROSPECT_SAFE_SUMMARY", "required_for_followup": True,
                "safe_snippets": ["Assessment delivery is evidence-led and bounded to the agreed scope."],
            },
            {
                "asset_id": "asset-internal-method", "title": "Internal scoring workbook",
                "version": "v3", "sha256": D, "prep_state": "READY",
                "release_class": "INTERNAL_ONLY", "required_for_followup": False,
                "safe_snippets": ["THIS MUST NEVER LEAK"],
            },
        ],
        "release_records": [],
        "qualification_gates": [{"gate_id": "gate-prime", "mandatory": True, "state": "CLEAR", "owner_action": None}],
        "commitments": [], "requested_asset_ids": [],
    }


def obs2(*, interpretation="DECLINED", at="2026-09-13T12:45:00Z", supersedes="obs-1") -> dict:
    return {
        "observation_id": "obs-2", "thread_id": "thread-clarks-1", "message_id": "msg-2",
        "sender_ref": "contact-prime-1", "sender_role": "PRIME_CONTACT", "received_at": at,
        "content_sha256": F, "source_class": "GMAIL", "interpretation": interpretation,
        "supersedes_observation_id": supersedes, "clarification_codes": [],
    }


class TeamingConversionTests(unittest.TestCase):
    def comp(self, p=None, pol=None):
        return compile_control(p or packet(), pol or policy(), as_of=NOW)

    def test_core_dispositions_and_authority(self):
        r = self.comp()
        self.assertEqual(r["payload"]["disposition"], "FOLLOWUP_READY")
        a = r["payload"]["authority"]
        self.assertTrue(a["owner_review_only"])
        self.assertTrue(all(not v for k, v in a.items() if k != "owner_review_only"))
        for interpretation, expected in [
            ("CONDITIONAL_INTEREST", "FOLLOWUP_READY"), ("REQUESTED_MORE_INFO", "NEEDS_CLARIFICATION"),
            ("AMBIGUOUS", "NEEDS_CLARIFICATION"), ("DECLINED", "DECLINED")]:
            with self.subTest(interpretation=interpretation):
                p = packet(); p["observations"][0]["interpretation"] = interpretation
                self.assertEqual(self.comp(p)["payload"]["disposition"], expected)

    def test_internal_assets_never_project(self):
        r = self.comp(); payload = r["payload"]
        self.assertNotIn("asset-internal-method", {x["asset_id"] for x in payload["safe_assets"]})
        self.assertNotIn("THIS MUST NEVER LEAK", str(payload))
        self.assertNotIn("THIS MUST NEVER LEAK", render_markdown(r))
        p = packet(); p["requested_asset_ids"] = ["asset-internal-method"]
        r = self.comp(p)
        self.assertEqual(r["payload"]["disposition"], "ASSET_PREP_REQUIRED")

    def test_required_asset_states_and_exact_owner_release(self):
        for mutation, blocker in [
            (lambda p: p.__setitem__("assets", [p["assets"][1]]), "required_asset_missing:asset-summary"),
            (lambda p: p["assets"][0].__setitem__("prep_state", "DRAFT"), "required_asset_not_ready:asset-summary"),
        ]:
            p = packet(); mutation(p); r = self.comp(p)
            self.assertEqual(r["payload"]["disposition"], "ASSET_PREP_REQUIRED")
            self.assertIn(blocker, r["payload"]["asset_blockers"])
        p = packet(); p["assets"][0]["release_class"] = "OWNER_APPROVAL_REQUIRED"
        self.assertEqual(self.comp(p)["payload"]["disposition"], "ASSET_PREP_REQUIRED")
        p["release_records"] = [{
            "release_id": "rel-1", "asset_id": "asset-summary", "asset_version": "v1",
            "asset_sha256": F, "approved_at": "2026-09-13T12:40:00Z", "approved_by_ref": "owner-1",
        }]
        self.assertEqual(self.comp(p)["payload"]["disposition"], "FOLLOWUP_READY")
        p["release_records"][0]["asset_sha256"] = D
        self.assertEqual(self.comp(p)["payload"]["disposition"], "ASSET_PREP_REQUIRED")

    def test_qualification_and_commitment_fences(self):
        for state in ("BLOCKED", "UNKNOWN", "CURABLE"):
            p = packet(); p["qualification_gates"][0]["state"] = state
            self.assertEqual(self.comp(p)["payload"]["disposition"], "QUALIFICATION_BLOCKED")
        p = packet(); p["commitments"] = [{
            "commitment_id": "commit-staff", "kind": "STAFFING", "required_for_followup": True,
            "approved": False, "safe_fact": None, "approval_ref": None,
        }]
        self.assertEqual(self.comp(p)["payload"]["disposition"], "QUALIFICATION_BLOCKED")
        p["commitments"][0].update(approved=True, safe_fact="Approved staffing fact.", approval_ref="approval-1")
        r = self.comp(p)
        self.assertEqual(r["payload"]["disposition"], "FOLLOWUP_READY")
        self.assertIn("Approved staffing fact.", r["payload"]["talking_points"])
        p["commitments"][0].update(approved=False, safe_fact="smuggle", approval_ref=None)
        with self.assertRaises(ControlError): self.comp(p)

    def test_observation_conflict_thread_supersession_and_time(self):
        p = packet(); bad = copy.deepcopy(p["observations"][0]); bad["content_sha256"] = F
        p["observations"].append(bad)
        self.assertEqual(self.comp(p)["payload"]["disposition"], "HOLD")
        p = packet(); p["observations"][0]["thread_id"] = "thread-other"
        self.assertIn("cross_thread_observation:obs-1", self.comp(p)["payload"]["blockers"])
        p = packet(); p["observations"].append(obs2())
        self.assertEqual(self.comp(p)["payload"]["disposition"], "DECLINED")
        p = packet(); p["observations"].append(obs2(supersedes="obs-missing"))
        self.assertEqual(self.comp(p)["payload"]["disposition"], "HOLD")
        for field, value, blocker in [
            (("observations", 0, "received_at"), "2026-09-13T13:02:00Z", "future_observation:obs-1"),
            (("observations", 0, "received_at"), "2026-09-01T12:30:00Z", "current_observation_stale"),
            (("opportunity", "source_checked_at"), "2026-09-01T12:00:00Z", "opportunity_source_stale"),
        ]:
            p = packet()
            if len(field) == 3: p[field[0]][field[1]][field[2]] = value
            else: p[field[0]][field[1]] = value
            self.assertIn(blocker, self.comp(p)["payload"]["blockers"])

    def test_future_release_fails_closed(self):
        p = packet(); p["assets"][0]["release_class"] = "OWNER_APPROVAL_REQUIRED"
        p["release_records"] = [{
            "release_id": "rel-1", "asset_id": "asset-summary", "asset_version": "v1",
            "asset_sha256": F, "approved_at": "2026-09-13T13:02:00Z", "approved_by_ref": "owner-1",
        }]
        r = self.comp(p); self.assertEqual(r["payload"]["disposition"], "HOLD")
        self.assertIn("future_release_record:rel-1", r["payload"]["blockers"])

    def test_strict_json_types_refs_and_time(self):
        p = packet(); p["assets"][0]["required_for_followup"] = 1
        with self.assertRaises(ControlError): self.comp(p)
        pol = policy(); pol["max_reply_age_seconds"] = True
        with self.assertRaises(ControlError): self.comp(packet(), pol)
        for value in ("person@example.com", "../../secret", "api-key-secret"):
            p = packet(); p["opportunity"]["counterparty_ref"] = value
            with self.assertRaises(ControlError): self.comp(p)
        with self.assertRaises(DuplicateKeyError):
            parse_json_bytes(b'{"x":1,"x":2}', "x")
        with self.assertRaises(ControlError): parse_json_bytes(b'{"x":NaN}', "x")
        for value in ("2026-09-13T08:00:00-04:00", "2026-09-13T12:00:00.123Z"):
            p = packet(); p["opportunity"]["source_checked_at"] = value
            with self.assertRaises(ControlError): self.comp(p)

    def test_receipt_verifiers_tamper_policy_and_exact_bytes(self):
        r = self.comp(); verify_control(packet(), policy(), r)
        tampered = copy.deepcopy(r); tampered["payload"]["disposition"] = "DECLINED"
        with self.assertRaises(ControlError): parse_receipt_bytes(canonical_bytes(tampered))
        pol = policy(); pol["max_reply_age_seconds"] -= 1
        with self.assertRaises(ControlError): verify_control(packet(), pol, r)
        pb, qb = canonical_bytes(packet()), canonical_bytes(policy())
        exact = compile_bytes(pb, qb, as_of=NOW); verify_bytes(pb, qb, canonical_bytes(exact))
        with self.assertRaises(ControlError): verify_bytes(b" " + pb, qb, canonical_bytes(exact))

    def test_determinism_and_order_invariant_projection(self):
        p1 = packet(); p1["assets"].append({
            "asset_id": "asset-public", "title": "Public reference", "version": "v1", "sha256": E,
            "prep_state": "READY", "release_class": "PROSPECT_SAFE_PUBLIC_REFERENCE",
            "required_for_followup": False, "safe_snippets": ["Public reference fact."],
        })
        p2 = copy.deepcopy(p1); p2["assets"].reverse()
        r1, r2 = self.comp(p1)["payload"], self.comp(p2)["payload"]
        for key in ("disposition", "safe_assets", "talking_points", "asset_blockers", "qualification_blockers"):
            self.assertEqual(r1[key], r2[key])
        md = render_markdown(self.comp())
        self.assertEqual(md, render_markdown(self.comp()))
        self.assertIn("Owner review only", md)

    def test_regular_io_and_cli(self):
        from revenue.teaming_conversion import cli
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); inp, pol = root/"packet.json", root/"policy.json"
            outj, outm = root/"receipt.json", root/"receipt.md"
            inp.write_bytes(canonical_bytes(packet())); pol.write_bytes(canonical_bytes(policy()))
            self.assertEqual(read_bounded_regular(inp), canonical_bytes(packet()))
            self.assertEqual(cli.main(["compile", "--input", str(inp), "--policy", str(pol),
                                       "--json-output", str(outj), "--markdown-output", str(outm)]), 0)
            self.assertEqual(cli.main(["verify", "--input", str(inp), "--policy", str(pol), "--receipt", str(outj)]), 0)
            self.assertEqual(cli.main(["compile", "--input", str(inp), "--policy", str(pol),
                                       "--json-output", str(outj), "--markdown-output", str(outm)]), 2)
            link = root/"link"; link.symlink_to(inp)
            with self.assertRaises(ControlError): read_bounded_regular(link)
            extra = root/"extra"; write_exclusive_regular(extra, b"x")
            with self.assertRaises(ControlError): write_exclusive_regular(extra, b"y")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_fifo_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td)/"pipe"; os.mkfifo(fifo)
            with self.assertRaises(ControlError): read_bounded_regular(fifo)

    def test_python_optimized(self):
        if sys.flags.optimize:
            self.skipTest("already optimized")
        root = Path(__file__).resolve().parents[2]; env = dict(os.environ); env["PYTHONPATH"] = str(root)
        proc = subprocess.run([sys.executable, "-O", "-m", "unittest", "revenue.teaming_conversion.test_control"],
                              cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
