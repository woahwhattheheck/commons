#!/usr/bin/env python3
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "autogtm_same_loop", ROOT / "host" / "autogtm_same_loop.py"
)
assert SPEC and SPEC.loader
loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loop)
HTML = (ROOT / "revenue/website_people_email_book/fixture_seller.html").read_text(
    encoding="utf-8"
)
CATALOG = json.loads(
    (ROOT / "revenue/smart_outreach/candidates.json").read_text(encoding="utf-8")
)


def fake_401(_url: str) -> tuple[int, str]:
    return 401, '{"detail":"Missing API key"}'


def fake_down(_url: str) -> tuple[int, str]:
    return 0, "network down"


class TestAutogtmSameLoop(unittest.TestCase):
    def test_unasked_autopilot_is_not_a_send(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_401
        )
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["autopilot"]["state"], "UNASKED")
        self.assertFalse(row["sent"])
        self.assertEqual(row["booked"], 0)
        self.assertEqual(row["cash_usd"], 0)
        self.assertTrue(row["no_auth"])
        self.assertTrue(row["no_gate"])

    def test_autopilot_is_refused_and_never_sends(self) -> None:
        row = loop.measure(
            html=HTML,
            source="fixture",
            catalog=CATALOG,
            asked_autopilot=True,
            opener=fake_401,
        )
        self.assertEqual(row["autopilot"]["state"], "REFUSED")
        self.assertFalse(row["autopilot"]["sent"])
        self.assertFalse(row["sent"])
        self.assertEqual(row["steps"], list(loop.STEPS))

    def test_explee_missing_key_is_finder_failed_never_zero(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_401
        )
        api = row["explee_api"]
        self.assertEqual(api["http"], 401)
        self.assertEqual(api["state"], "FINDER-FAILED")
        self.assertFalse(api["permission"])
        self.assertEqual(api["external"], "EXTERNAL_PROVIDER_ACTION")
        self.assertNotEqual(api["http"], 0)

    def test_explee_network_miss_is_finder_failed_not_clear(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_down
        )
        self.assertEqual(row["explee_api"]["state"], "FINDER-FAILED")
        self.assertEqual(row["explee_api"]["http"], 0)
        self.assertIn("never silent 0", row["explee_api"]["note"])

    def test_same_eight_steps_as_open_twin(self) -> None:
        self.assertEqual(
            loop.STEPS,
            (
                "set_context",
                "choose_mode",
                "generate_queries",
                "search_extract",
                "enrich_score",
                "draft_campaign",
                "approve_or_autopilot",
                "sync_status",
            ),
        )
        self.assertEqual(loop.OPEN_TWIN, "https://github.com/cmn-labs/autogtm")
        self.assertEqual(loop.EXPLEE_DOOR, "https://explee.com/")

    def test_context_and_queries_come_from_website(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_401
        )
        self.assertEqual(row["context"]["state"], "INTEGRATED")
        self.assertIn("crash-resume", row["context"]["offer"].lower())
        self.assertGreaterEqual(len(row["queries"]), 3)
        self.assertGreaterEqual(len(row["drafts"]), 1)
        self.assertTrue(all(d["state"] == "DRAFT" and d["sent"] is False for d in row["drafts"]))

    def test_occupied_prospect_is_not_drafted(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_401
        )
        ids = {d["prospect_id"] for d in row["drafts"]}
        self.assertNotIn("metaforms", ids)

    def test_do_not_remint_existing_explee_loop(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_401
        )
        self.assertIn("website-people-email-book-20260830-01", row["do_not_remint"])
        self.assertIn("host/smart_outreach.py", row["do_not_remint"])

    def test_https_required_for_url(self) -> None:
        with self.assertRaises(ValueError):
            loop.load_html("http://example.com", loop.DEFAULT_HTML)

    def test_boards_lists_autogtm_door(self) -> None:
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html"', boards)
        self.assertIn("same loop as Explee", boards)
        door = (ROOT / "door.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn('["autogtm.html", "AutoGTM"]', door)
        self.assertIn('href="./autogtm.html">AutoGTM</a>', index)
        self.assertIn('href="./autogtm.html">AutoGTM</a>', gen)

    def test_peer_ack_does_not_remint_harborline_or_lead(self) -> None:
        ack = (ROOT / "p/cursor-autogtm-ack-peers-20260902-01.md").read_text(
            encoding="utf-8"
        )
        harbor = (ROOT / "p/cursor-explee-qualify-clone-20260902-01.md").read_text(
            encoding="utf-8"
        )
        lead = ROOT / "p/cursor-explee-skills-adopt-20260902-01.md"
        self.assertIn("aceb4aead", ack)
        self.assertIn("cursor-explee-skills-adopt-20260902-01", ack)
        self.assertIn("did **not** steal", ack)
        self.assertIn("will **not** remint that id", ack)
        self.assertIn("/qualify", harbor)
        # LEAD unique leftover landed unread. "Will not remint that id" is not
        # "LEAD receipt must stay absent." Absence pin went red at #8289.
        self.assertTrue(lead.exists())
        lead_text = lead.read_text(encoding="utf-8")
        self.assertIn("Sheshiyer", lead_text)
        self.assertIn("4908bce4", lead_text)
        self.assertIn("bdfc9240e", lead_text)

    def test_composes_website_people_email_book_extract(self) -> None:
        row = loop.measure(
            html=HTML, source="fixture", catalog=CATALOG, opener=fake_401
        )
        self.assertEqual(
            row["context"]["composed_from"],
            "host/website_people_email_book.py#extract_website",
        )
        self.assertEqual(
            row["context"]["book_url"],
            "https://cal.com/tokenjunkielabs/intro",
        )
        self.assertIn("crash-resume", row["context"]["offer"].lower())

    def test_named_eight_step_functions_run(self) -> None:
        row = loop.measure(
            html=HTML,
            source="fixture",
            catalog=CATALOG,
            asked_autopilot=True,
            opener=fake_401,
        )
        self.assertEqual(row["mode"], "autopilot")
        self.assertEqual(row["status"]["sent"], False)
        self.assertEqual(row["status"]["cash_usd"], 0)
        self.assertEqual(row["status"]["explee"], "FINDER-FAILED")
        self.assertEqual(loop.choose_mode(False), "run_now")
        self.assertEqual(len(loop.search_extract(CATALOG)), len(CATALOG["prospects"]))

    def test_sibling_gtm_doors_link_autogtm(self) -> None:
        wpeb = (ROOT / "website-people-email-book.html").read_text(encoding="utf-8")
        index = (ROOT / "lm-gtm-index.html").read_text(encoding="utf-8")
        self.assertIn('href="./autogtm.html"', wpeb)
        self.assertIn('href="./autogtm.html"', index)


if __name__ == "__main__":
    unittest.main()
