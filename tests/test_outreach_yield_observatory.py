from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from revenue.outreach_yield_observatory import ObservatoryError, evaluate_document, render_markdown


def event(prospect, name, at, *, exp="exp-a", segment="hotel", offer="paid-discovery", route="email", evidence=None):
    row = {
        "prospect_key": prospect,
        "experiment_id": exp,
        "segment": segment,
        "offer": offer,
        "route": route,
        "event": name,
        "at": at,
    }
    if evidence is not None:
        row["evidence_ref"] = evidence
    return row


def base_doc():
    return {
        "schema_version": 1,
        "as_of": "2026-09-14T16:00:00Z",
        "maturation_hours": 72,
        "policy": {
            "min_matured_exposures": 2,
            "min_positive_reply_ppm": 250_000,
            "max_dnr_ppm": 500_000,
            "min_paid_scope_acceptances": 1,
            "min_payment_evidenced": 0,
        },
        "events": [],
    }


class ObservatoryTests(unittest.TestCase):
    def test_matured_denominator_and_full_reply_chain(self):
        doc = base_doc()
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "HUMAN_REPLY", "2026-09-10T12:00:00Z", evidence="msg:1"),
            event("lead-1", "POSITIVE_REPLY", "2026-09-10T12:10:00Z", evidence="msg:2"),
            event("lead-1", "PAID_SCOPE_ACCEPTED", "2026-09-10T13:00:00Z", evidence="msg:3"),
            event("lead-1", "PAYMENT_EVIDENCED", "2026-09-10T14:00:00Z", evidence="receipt:4"),
            event("lead-2", "SENT", "2026-09-10T11:00:00Z"),
            event("lead-3", "SENT", "2026-09-14T10:00:00Z"),
            # Early positive evidence still does not mature lead-3's denominator.
            event("lead-3", "HUMAN_REPLY", "2026-09-14T11:00:00Z", evidence="msg:5"),
            event("lead-3", "POSITIVE_REPLY", "2026-09-14T12:00:00Z", evidence="msg:6"),
        ]
        report = evaluate_document(doc)
        cohort = report["cohorts"][0]
        self.assertEqual(cohort["exposures"], 3)
        self.assertEqual(cohort["matured_exposures"], 2)
        self.assertEqual(cohort["immature_exposures"], 1)
        self.assertEqual(cohort["matured_human_replies"], 1)
        self.assertEqual(cohort["matured_positive_replies"], 1)
        self.assertEqual(cohort["matured_paid_scope_acceptances"], 1)
        self.assertEqual(cohort["matured_payment_evidenced"], 1)
        self.assertEqual(cohort["positive_reply_ppm"], 500_000)
        self.assertEqual(cohort["signal"], "SCALE_REVIEW")
        self.assertFalse(report["authority"]["outbound_action"])
        self.assertFalse(report["authority"]["accounting_recognition"])

    def test_support_gate_beats_early_success(self):
        doc = base_doc()
        doc["policy"]["min_matured_exposures"] = 3
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "HUMAN_REPLY", "2026-09-10T11:00:00Z", evidence="m1"),
            event("lead-1", "POSITIVE_REPLY", "2026-09-10T12:00:00Z", evidence="m2"),
            event("lead-1", "PAID_SCOPE_ACCEPTED", "2026-09-10T13:00:00Z", evidence="m3"),
        ]
        cohort = evaluate_document(doc)["cohorts"][0]
        self.assertEqual(cohort["signal"], "LEARN_MORE")
        self.assertIn("support", cohort["signal_reason"])

    def test_dnr_gate(self):
        doc = base_doc()
        doc["policy"]["max_dnr_ppm"] = 400_000
        doc["policy"]["min_paid_scope_acceptances"] = 0
        doc["policy"]["min_positive_reply_ppm"] = 0
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "DNR", "2026-09-10T11:00:00Z", evidence="dnr:1"),
            event("lead-2", "SENT", "2026-09-10T10:00:00Z"),
        ]
        cohort = evaluate_document(doc)["cohorts"][0]
        self.assertEqual(cohort["dnr_ppm"], 500_000)
        self.assertEqual(cohort["signal"], "STOP_DNR_REVIEW")

    def test_rejects_raw_email_pii_in_key_and_dimensions(self):
        doc = base_doc()
        doc["events"] = [
            event("person@example.com", "SENT", "2026-09-10T10:00:00Z")
        ]
        with self.assertRaisesRegex(ObservatoryError, "de-identified|raw email"):
            evaluate_document(doc)

        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z", segment="person@example.com")
        ]
        with self.assertRaisesRegex(ObservatoryError, "raw email"):
            evaluate_document(doc)

    def test_rejects_raw_email_pii_in_evidence_ref(self):
        doc = base_doc()
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event(
                "lead-1",
                "HUMAN_REPLY",
                "2026-09-10T11:00:00Z",
                evidence="person@example.com",
            ),
        ]
        with self.assertRaisesRegex(ObservatoryError, "opaque reference|raw email"):
            evaluate_document(doc)

    def test_rejects_future_and_naive_timestamps(self):
        doc = base_doc()
        doc["events"] = [event("lead-1", "SENT", "2026-09-15T10:00:00Z")]
        with self.assertRaisesRegex(ObservatoryError, "later than as_of"):
            evaluate_document(doc)

        doc = base_doc()
        doc["events"] = [event("lead-1", "SENT", "2026-09-10T10:00:00")]
        with self.assertRaisesRegex(ObservatoryError, "timezone"):
            evaluate_document(doc)

    def test_requires_explicit_reply_evidence_chain(self):
        doc = base_doc()
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "POSITIVE_REPLY", "2026-09-10T11:00:00Z", evidence="msg:2"),
        ]
        with self.assertRaisesRegex(ObservatoryError, "requires explicit HUMAN_REPLY"):
            evaluate_document(doc)

        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "HUMAN_REPLY", "2026-09-10T11:00:00Z", evidence="msg:1"),
            event("lead-1", "POSITIVE_REPLY", "2026-09-10T12:00:00Z", evidence="msg:2"),
            event("lead-1", "PAYMENT_EVIDENCED", "2026-09-10T13:00:00Z", evidence="receipt:3"),
        ]
        with self.assertRaisesRegex(ObservatoryError, "requires explicit PAID_SCOPE_ACCEPTED"):
            evaluate_document(doc)

    def test_rejects_negative_terminal_plus_reply(self):
        doc = base_doc()
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "DNR", "2026-09-10T11:00:00Z", evidence="dnr:1"),
            event("lead-1", "HUMAN_REPLY", "2026-09-10T12:00:00Z", evidence="msg:1"),
        ]
        with self.assertRaisesRegex(ObservatoryError, "cannot coexist"):
            evaluate_document(doc)

    def test_rejects_duplicate_exposure_event_and_dimension_drift(self):
        doc = base_doc()
        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "SENT", "2026-09-10T11:00:00Z"),
        ]
        with self.assertRaisesRegex(ObservatoryError, "duplicate SENT"):
            evaluate_document(doc)

        doc["events"] = [
            event("lead-1", "SENT", "2026-09-10T10:00:00Z"),
            event("lead-1", "HUMAN_REPLY", "2026-09-10T11:00:00Z", segment="saas", evidence="m1"),
        ]
        with self.assertRaisesRegex(ObservatoryError, "changed"):
            evaluate_document(doc)

    def test_deterministic_ranking_prefers_evidenced_funnel(self):
        doc = base_doc()
        doc["policy"].update(
            min_matured_exposures=1,
            min_positive_reply_ppm=0,
            max_dnr_ppm=1_000_000,
            min_paid_scope_acceptances=0,
        )
        doc["events"] = [
            event("a-1", "SENT", "2026-09-10T10:00:00Z", exp="exp-a"),
            event("b-1", "SENT", "2026-09-10T10:00:00Z", exp="exp-b"),
            event("b-1", "HUMAN_REPLY", "2026-09-10T11:00:00Z", exp="exp-b", evidence="b1"),
            event("b-1", "POSITIVE_REPLY", "2026-09-10T12:00:00Z", exp="exp-b", evidence="b2"),
        ]
        report = evaluate_document(doc)
        self.assertEqual([c["experiment_id"] for c in report["cohorts"]], ["exp-b", "exp-a"])
        self.assertEqual([c["rank"] for c in report["cohorts"]], [1, 2])

    def test_markdown_keeps_authority_boundary(self):
        doc = base_doc()
        doc["policy"]["min_paid_scope_acceptances"] = 0
        doc["events"] = [event("lead-1", "SENT", "2026-09-10T10:00:00Z")]
        text = render_markdown(evaluate_document(doc))
        self.assertIn("no send", text)
        self.assertIn("not revenue recognition", text)
        self.assertIn("Re-check live claims", text)

    def test_cli_json_and_markdown_roundtrip(self):
        doc = base_doc()
        doc["policy"]["min_paid_scope_acceptances"] = 0
        doc["events"] = [event("lead-1", "SENT", "2026-09-10T10:00:00Z")]
        cli = ROOT / "host" / "outreach_yield_observatory.py"
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "evidence.json"
            src.write_text(json.dumps(doc), encoding="utf-8")
            json_run = subprocess.run(
                [sys.executable, str(cli), str(src), "--format", "json"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json_run.returncode, 0, json_run.stderr)
            parsed = json.loads(json_run.stdout)
            self.assertEqual(parsed["schema_version"], 1)

            md_run = subprocess.run(
                [sys.executable, str(cli), str(src), "--format", "markdown"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(md_run.returncode, 0, md_run.stderr)
            self.assertIn("# Outreach Yield Observatory", md_run.stdout)

    def test_cli_fail_closed(self):
        cli = ROOT / "host" / "outreach_yield_observatory.py"
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "bad.json"
            src.write_text('{"schema_version": 1}', encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(cli), str(src)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 2)
            self.assertIn("as_of", run.stderr)


if __name__ == "__main__":
    unittest.main()
