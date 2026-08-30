from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "website_people_email_book", ROOT / "host" / "website_people_email_book.py"
)
assert SPEC and SPEC.loader
loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loop)

FIXTURE = ROOT / "revenue" / "website_people_email_book" / "fixture_seller.html"
LOOP_JSON = ROOT / "revenue" / "website_people_email_book" / "loop.json"
SOURCE = "revenue/website_people_email_book/fixture_seller.html"
HOST = ROOT / "host" / "website_people_email_book.py"


def fixture_loop() -> dict:
    return loop.build_loop(FIXTURE.read_text(encoding="utf-8"), SOURCE)


def measured_mailbox_status() -> dict:
    return {
        "kind": "SWARM_MAIL_PRIVATE_RUNTIME_STATUS",
        "inboxes": [
            {
                "inbox_id": "codex-sales",
                "model_family": "CODEX",
                "state": "MEASURED",
                "address_ref": "opaque:address:codex-owner-0001",
            }
        ],
        "counts": {"measured_inboxes": 1},
        "commercial_success": "UNMEASURED_BY_MAIL",
    }


def prospect_catalog(email: str = "buyer@prospect.test") -> dict:
    return {
        "schema_version": "commons-smart-outreach/v1",
        "kind": "SMART_OUTREACH_CANDIDATES",
        "generated_at": "2026-08-30T13:14:08Z",
        "offer": {
            "sku_id": "seed-website-offer",
            "name": "Seed website offer",
            "price_usd": 2500,
            "proof_url": "https://seller.test/proof",
            "intake_url": "https://seller.test/intake",
        },
        "prospects": [
            {
                "prospect_id": "external-buyer",
                "organization": "External Buyer",
                "recipient_email": email,
                "evidence": {
                    "source_url": "https://prospect.test/incident",
                    "observed_at": "2026-08-30T13:00:00Z",
                    "exact_quote": "Our production agent failure needs reliable recovery and replay.",
                },
                "owner_role": "Head of Agent Reliability",
                "route": {"kind": "EMAIL", "value": email, "state": "VERIFIED"},
                "proof_hypothesis": "Can one production failure recover with a replay receipt?",
                "occupied_by": None,
                "do_not_contact": False,
                "disqualifiers": [],
            }
        ],
    }


class WebsitePeopleEmailBookTests(unittest.TestCase):
    def test_default_uses_external_evidence_catalog_not_seller_people(self) -> None:
        result = fixture_loop()
        self.assertEqual(result["truth"]["prospects_found"], 4)
        self.assertEqual(result["truth"]["seller_contacts_observed"], 4)
        self.assertEqual(result["truth"]["emails_drafted"], 1)
        self.assertEqual(result["truth"]["calls_booked"], 0)
        self.assertEqual(result["truth"]["transport_actions"], 0)
        self.assertEqual(result["truth"]["cash_usd"], 0)
        self.assertEqual(result["truth"]["mailbox"], "NEEDS_OWNER_MAILBOX")
        organizations = {item["organization"] for item in result["prospects"]}
        self.assertEqual(
            organizations,
            {"AnythingLLM / Mintplex Labs", "Composio", "Metaforms", "SigNoz"},
        )
        self.assertNotIn("Ava Platform", organizations)
        composio = next(item for item in result["emails"] if item["prospect_id"] == "composio")
        self.assertEqual(composio["to"], "support@composio.dev")
        self.assertEqual(composio["transport"], "STAGED_NOT_SENT")

    def test_qualified_external_prospect_gets_evidence_bound_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = loop.build_loop(
                FIXTURE.read_text(encoding="utf-8"),
                SOURCE,
                prospect_catalog(),
                Path(directory),
            )
        self.assertEqual(result["truth"]["prospects_found"], 1)
        self.assertEqual(result["truth"]["emails_drafted"], 1)
        email = result["emails"][0]
        self.assertEqual(email["prospect_id"], "external-buyer")
        self.assertEqual(email["to"], "buyer@prospect.test")
        self.assertEqual(email["transport"], "STAGED_NOT_SENT")
        self.assertIn("Our production agent failure needs reliable recovery and replay.", email["draft"]["body"])
        self.assertIn("https://prospect.test/incident", email["draft"]["body"])
        self.assertIn("https://cal.com/tokenjunkielabs/intro", email["draft"]["body"])
        self.assertIn("opt out", email["draft"]["body"])
        self.assertEqual(result["bookings"][0]["state"], "STAGED_NOT_BOOKED")

    def test_redacted_swarm_status_can_measure_owner_mailbox_without_enabling_send(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = loop.build_loop(
                FIXTURE.read_text(encoding="utf-8"),
                SOURCE,
                prospect_catalog(),
                Path(directory),
                mailbox_status=measured_mailbox_status(),
            )
        loop.validate_loop(result)
        self.assertEqual(result["truth"]["mailbox"], "OWNER_MAILBOX_MEASURED")
        self.assertEqual(result["truth"]["transport_actions"], 0)
        self.assertEqual(result["emails"][0]["transport"], "STAGED_NOT_SENT")
        self.assertNotIn("@", json.dumps(result["mailbox_runtime"]))

    def test_mailbox_truth_cannot_be_promoted_without_redacted_runtime_evidence(self) -> None:
        result = fixture_loop()
        result["truth"]["mailbox"] = "OWNER_MAILBOX_MEASURED"
        with self.assertRaisesRegex(loop.LoopError, "must match"):
            loop.validate_loop(result)

    def test_mailbox_status_rejects_raw_address_or_inconsistent_count(self) -> None:
        exposed = measured_mailbox_status()
        exposed["inboxes"][0]["address_ref"] = "codex@example.test"
        with self.assertRaisesRegex(loop.LoopError, "must not contain"):
            loop.build_loop(
                FIXTURE.read_text(encoding="utf-8"),
                SOURCE,
                mailbox_status=exposed,
            )
        inconsistent = measured_mailbox_status()
        inconsistent["counts"]["measured_inboxes"] = 0
        with self.assertRaisesRegex(loop.LoopError, "does not match"):
            loop.build_loop(
                FIXTURE.read_text(encoding="utf-8"),
                SOURCE,
                mailbox_status=inconsistent,
            )

    def test_seller_contact_is_never_reclassified_as_external_prospect(self) -> None:
        catalog = prospect_catalog("ava@example.test")
        with tempfile.TemporaryDirectory() as directory:
            result = loop.build_loop(
                FIXTURE.read_text(encoding="utf-8"), SOURCE, catalog, Path(directory)
            )
        prospect = result["prospects"][0]
        self.assertEqual(prospect["decision"], "HOLD_SELLER_CONTACT")
        self.assertEqual(result["emails"], [])
        self.assertEqual(result["bookings"], [])

    def test_missing_route_is_not_invented(self) -> None:
        catalog = prospect_catalog()
        catalog["prospects"][0]["recipient_email"] = None
        catalog["prospects"][0]["route"] = {
            "kind": "FIRST_PARTY_ROUTE",
            "value": None,
            "state": "UNVERIFIED",
        }
        with tempfile.TemporaryDirectory() as directory:
            result = loop.build_loop(
                FIXTURE.read_text(encoding="utf-8"), SOURCE, catalog, Path(directory)
            )
        self.assertEqual(result["prospects"][0]["decision"], "RESEARCH_REQUIRED")
        self.assertEqual(result["emails"], [])
        self.assertNotIn("external-buyer@", json.dumps(result))

    def test_json_ld_person_is_seller_context_only(self) -> None:
        result = fixture_loop()
        sam = next(item for item in result["seller_contacts"] if item["contact_id"] == "sam-example-test")
        self.assertEqual(sam["email"], "sam@example.test")
        self.assertEqual(sam["source"], "json-ld")
        self.assertIn("never treat", sam["next_action"])
        self.assertFalse(any(email["to"] == "sam@example.test" for email in result["emails"]))

    def test_composes_existing_smart_outreach_planner(self) -> None:
        result = fixture_loop()
        self.assertIn("current evidence-bound prospect discovery", result["compose"]["smart_outreach"])
        source = HOST.read_text(encoding="utf-8")
        self.assertIn('ROOT / "host" / "smart_outreach.py"', source)
        self.assertIn("planner.build_plan", source)
        self.assertIn('ROOT / "revenue" / "smart_outreach" / "candidates.json"', source)

    def test_empty_html_fails_closed(self) -> None:
        with self.assertRaises(loop.LoopError):
            loop.build_loop("   ", SOURCE)

    def test_url_must_be_https(self) -> None:
        with self.assertRaises(loop.LoopError):
            loop.fetch_url("http://example.test")

    def test_send_exits_3_and_does_not_claim_transport(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HOST), "run", "--send"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 3)
        self.assertIn("this planner never transports mail", proc.stderr.casefold())
        self.assertIn("swarm mail", proc.stderr.casefold())
        self.assertEqual(proc.stdout.strip(), "")

    def test_cli_run_is_deterministic_and_validate_matches(self) -> None:
        command = [sys.executable, str(HOST), "run", "--html", str(FIXTURE)]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        parsed = json.loads(first)
        loop.validate_loop(parsed)
        self.assertEqual(parsed["truth"]["transport_actions"], 0)
        self.assertEqual(parsed["truth"]["calls_booked"], 0)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "loop.json"
            output.write_text(first, encoding="utf-8")
            validate = subprocess.run(
                [sys.executable, str(HOST), "validate", "--input", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        self.assertEqual(validate.strip(), "VALID 1 website 4 prospects 1 drafts 0 booked 0 sent")

    def test_checked_in_loop_matches_current_evidence_catalog(self) -> None:
        landed = json.loads(LOOP_JSON.read_text(encoding="utf-8"))
        loop.validate_loop(landed)
        built = fixture_loop()
        self.assertEqual(built["truth"], landed["truth"])
        self.assertEqual(
            [item["prospect_id"] for item in built["prospects"]],
            [item["prospect_id"] for item in landed["prospects"]],
        )
        self.assertEqual(built["emails"], landed["emails"])


if __name__ == "__main__":
    unittest.main()
