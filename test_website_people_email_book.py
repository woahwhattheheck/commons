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


class WebsitePeopleEmailBookTests(unittest.TestCase):
    def test_fixture_finds_people_drafts_email_and_stages_booking(self) -> None:
        result = fixture_loop()
        ids = [person["person_id"] for person in result["people"]]
        self.assertEqual(ids, ["ava-example-test", "noah-example-test", "riley-quiet", "sam-example-test"])
        self.assertEqual(result["truth"]["people_found"], 4)
        self.assertEqual(result["truth"]["emails_drafted"], 3)
        self.assertEqual(result["truth"]["calls_booked"], 0)
        self.assertEqual(result["truth"]["transport_actions"], 0)
        self.assertEqual(result["truth"]["cash_usd"], 0)
        self.assertEqual(result["truth"]["mailbox"], "NEEDS_OWNER_MAILBOX")
        self.assertEqual(result["website"]["book_url"], "https://cal.com/tokenjunkielabs/intro")
        self.assertEqual(result["website"]["headline"], "Crash-resume proof for production agent teams")

    def test_missing_mailto_is_not_invented(self) -> None:
        result = fixture_loop()
        riley = next(person for person in result["people"] if person["person_id"] == "riley-quiet")
        self.assertIsNone(riley["email"])
        self.assertEqual(riley["route"]["state"], "UNVERIFIED")
        self.assertFalse(any(item["person_id"] == "riley-quiet" for item in result["emails"]))
        self.assertNotIn("riley@", json.dumps(result))

    def test_json_ld_person_is_discovered(self) -> None:
        result = fixture_loop()
        sam = next(person for person in result["people"] if person["person_id"] == "sam-example-test")
        self.assertEqual(sam["email"], "sam@example.test")
        self.assertEqual(sam["source"], "json-ld")
        self.assertEqual(sam["role"], "Founder")

    def test_drafts_quote_site_need_and_book_cta(self) -> None:
        result = fixture_loop()
        ava = next(item for item in result["emails"] if item["person_id"] == "ava-example-test")
        body = ava["draft"]["body"]
        self.assertEqual(ava["transport"], "STAGED_NOT_SENT")
        self.assertIn("Our agents die mid-job and we have no crash-resume receipt.", body)
        self.assertIn("https://cal.com/tokenjunkielabs/intro", body)
        self.assertIn("opt out", body)
        self.assertIn("Not sent", body)
        self.assertIn("book a call", ava["draft"]["subject"].casefold())
        booking = next(item for item in result["bookings"] if item["person_id"] == "ava-example-test")
        self.assertEqual(booking["state"], "STAGED_NOT_BOOKED")
        self.assertEqual(booking["calls_booked"], 0)

    def test_does_not_remint_related_surfaces(self) -> None:
        result = fixture_loop()
        for path in (
            "revenue/smart_outreach",
            "host/smart_outreach.py",
            "revenue/subzero_gtm",
            "host/swarm_mail.py",
            "revenue/reply_to_revenue",
        ):
            self.assertIn(path, result["does_not_replace"])
        source = HOST.read_text(encoding="utf-8")
        self.assertNotIn("import smart_outreach", source)
        self.assertNotIn("from smart_outreach", source)
        self.assertNotIn("subzero_gtm.build", source)

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
        self.assertIn("owner mailbox", proc.stderr.casefold())
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
        self.assertEqual(validate.strip(), "VALID 1 website 4 people 3 drafts 0 booked 0 sent")

    def test_checked_in_loop_matches_fixture_truth(self) -> None:
        landed = json.loads(LOOP_JSON.read_text(encoding="utf-8"))
        loop.validate_loop(landed)
        built = fixture_loop()
        self.assertEqual(built["truth"], landed["truth"])
        self.assertEqual(
            [person["person_id"] for person in built["people"]],
            [person["person_id"] for person in landed["people"]],
        )
        self.assertEqual(len(built["emails"]), len(landed["emails"]))


if __name__ == "__main__":
    unittest.main()
