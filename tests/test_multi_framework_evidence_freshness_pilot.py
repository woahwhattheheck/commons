from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from revenue.multi_framework_evidence_freshness_pilot.pilot import (
    DIAGNOSTIC_PRICE_USD_CENTS,
    INTEGRATION_PRICE_USD_CENTS,
    MAX_DIAGNOSTIC_EVIDENCE,
    PilotError,
    compile_pilot,
    main,
    render_buyer_markdown,
    verify_pilot,
)

AS_OF = datetime(2026, 9, 13, 14, 0, 0, tzinfo=timezone.utc)


def evidence(eid: str, **overrides):
    row = {
        "evidence_id": eid,
        "owner_ref": f"owner-{eid}",
        "collected_at": "2026-08-01T00:00:00Z",
        "coverage_start": "2026-01-01T00:00:00Z",
        "coverage_end": "2026-06-30T00:00:00Z",
        "mappings": [{"framework": "SOC2", "control": "CC1.1"}],
        "checksum_sha256": (eid[0] if eid[0] in "abcdef" else "a") * 64,
        "freshness_rule_id": "fresh-120",
        "source_ref": f"source-{eid}",
    }
    row.update(overrides)
    return row


def raw_fixture(rows=None):
    if rows is None:
        rows = [
            evidence("a-reusable"),
            evidence("b-stale", collected_at="2026-01-01T00:00:00Z"),
            evidence("c-scope", mappings=[{"framework": "SOC2", "control": "CC9.9"}]),
            evidence("d-owner", owner_ref=""),
            evidence("e-incomplete", checksum_sha256=""),
        ]
    return {
        "schema": "commons.multi-framework-evidence-freshness/v1",
        "assessment": {
            "assessment_id": "assessment-2026-q3",
            "period_start": "2026-01-01T00:00:00Z",
            "period_end": "2026-06-30T00:00:00Z",
            "scope": [
                {"framework": "SOC2", "control": "CC1.1"},
                {"framework": "ISO27001", "control": "A.5.1"},
                {"framework": "HITRUST", "control": "01.a"},
                {"framework": "PCI-DSS", "control": "1.1"},
            ],
        },
        "freshness_policy": {"rule_id": "fresh-120", "max_age_days": 120},
        "evidence": rows,
    }


class PilotTests(unittest.TestCase):
    def test_compiles_fixed_commercial_packet_from_landed_gate(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        self.assertTrue(verify_pilot(packet))
        self.assertEqual(packet["diagnostic"]["counts"], {
            "REUSABLE": 1, "STALE": 1, "SCOPE_MISMATCH": 1, "MISSING_OWNER": 1, "INCOMPLETE": 1,
        })
        self.assertEqual(packet["offer"]["diagnostic_price_cents"], DIAGNOSTIC_PRICE_USD_CENTS)
        self.assertEqual(packet["offer"]["integration_sprint_price_cents"], INTEGRATION_PRICE_USD_CENTS)
        self.assertFalse(packet["offer"]["free_custom_adapter"])
        self.assertTrue(packet["offer"]["integration_requires_paid_diagnostic"])

    def test_base_packet_is_reverified_and_bound(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        self.assertEqual(packet["base_binding"]["base_receipt_sha256"], packet["base_packet"]["receipt_sha256"])
        self.assertEqual(len(packet["base_binding"]["base_packet_sha256"]), 64)

    def test_500_object_limit_is_exact(self):
        rows = [evidence(f"a{i:03d}", source_ref=f"source-{i}") for i in range(MAX_DIAGNOSTIC_EVIDENCE)]
        self.assertEqual(compile_pilot(raw_fixture(rows), trusted_as_of=AS_OF)["diagnostic"]["evidence_object_count"], 500)
        rows.append(evidence("a501", source_ref="source-501"))
        with self.assertRaisesRegex(PilotError, "evidence_limit_exceeded"):
            compile_pilot(raw_fixture(rows), trusted_as_of=AS_OF)

    def test_buyer_report_is_aggregate_and_privacy_minimized(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        report = render_buyer_markdown(packet)
        self.assertIn("$3,500 fixed", report)
        self.assertIn("$10,000", report)
        self.assertIn("not an audit opinion", report)
        self.assertNotIn("owner-a-reusable", report)
        self.assertNotIn("source-a-reusable", report)
        self.assertNotIn("a-reusable", report)
        self.assertNotIn("a" * 64, report)

    def test_reason_counts_are_aggregate(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        got = {r["reason"]: r["count"] for r in packet["diagnostic"]["reason_counts"]}
        self.assertEqual(got["FRESHNESS_WINDOW_EXCEEDED"], 1)
        self.assertEqual(got["MAPPING_OUTSIDE_ASSESSMENT_SCOPE"], 1)
        self.assertEqual(got["MISSING_OWNER"], 1)
        self.assertEqual(got["MISSING_CHECKSUM"], 1)

    def test_all_authority_is_false(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_resealed_price_tamper_fails_recompile(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        packet["offer"]["diagnostic_price_cents"] = 1
        packet["receipt_sha256"] = "0" * 64
        with self.assertRaisesRegex(PilotError, "recompile_mismatch"):
            verify_pilot(packet)

    def test_resealed_free_adapter_tamper_fails(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        packet["offer"]["free_custom_adapter"] = True
        with self.assertRaises(PilotError):
            verify_pilot(packet)

    def test_resealed_authority_escalation_fails(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        packet["authority"]["audit_opinion"] = True
        with self.assertRaises(PilotError):
            verify_pilot(packet)

    def test_input_order_is_deterministic_through_base_engine(self):
        a = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        b = compile_pilot(raw_fixture(list(reversed(raw_fixture()["evidence"]))), trusted_as_of=AS_OF)
        self.assertEqual(a["diagnostic"], b["diagnostic"])
        self.assertEqual(a["base_binding"], b["base_binding"])

    def test_naive_trusted_time_is_rejected(self):
        with self.assertRaisesRegex(PilotError, "timezone_required"):
            compile_pilot(raw_fixture(), trusted_as_of=datetime(2026, 9, 13, 14, 0, 0))

    def test_cli_owns_current_time_and_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / "in.json"
            out = Path(td) / "out.json"
            inp.write_text(json.dumps(raw_fixture()), encoding="utf-8")
            self.assertEqual(main(["compile", str(inp), str(out)]), 0)
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertLess(abs(datetime.now(timezone.utc).timestamp() - datetime.strptime(packet["evaluated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()), 10)
            self.assertEqual(main(["verify", str(out)]), 0)

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / "in.json"
            out = Path(td) / "out.json"
            inp.write_text(json.dumps(raw_fixture()), encoding="utf-8")
            out.write_text("owned", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                main(["compile", str(inp), str(out)])
            self.assertEqual(out.read_text(encoding="utf-8"), "owned")

    @unittest.skipIf(os.name == "nt", "symlink permissions vary on Windows")
    def test_cli_rejects_symlink_input(self):
        with tempfile.TemporaryDirectory() as td:
            real = Path(td) / "real.json"
            link = Path(td) / "link.json"
            out = Path(td) / "out.json"
            real.write_text(json.dumps(raw_fixture()), encoding="utf-8")
            link.symlink_to(real)
            with self.assertRaises(PilotError):
                main(["compile", str(link), str(out)])

    def test_buyer_report_hash_binds_report_body(self):
        packet = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        report = render_buyer_markdown(packet)
        body = report.split("Receipt:", 1)[0]
        import hashlib
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), packet["buyer_report_sha256"])

    def test_receipt_is_deterministic(self):
        a = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        b = compile_pilot(raw_fixture(), trusted_as_of=AS_OF)
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
