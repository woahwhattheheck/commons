# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import unittest

from .clear_reply import (
    REASON_BOUND_MISMATCH,
    REASON_KEY_MISMATCH,
    REASON_KEY_TRUNCATED,
    REASON_OK,
    REASON_UNDERBOUND_PROSE,
    parse_clear_reply,
)
from .deepseek_fallback_arbiter import clear_or_fallback, mint_decision_from_request

H = lambda text: hashlib.sha256(text.encode()).hexdigest()

REQUEST = {
    "request_key": "OUTBOUND-EMAIL-CLAIM-ABCDEF0123456789FULLKEY",
    "seat_id": "Z-A",
    "counterparty_key": "OPP-1",
    "route_sha256": H("route"),
    "purpose_sha256": H("purpose"),
    "retry_policy_generation": "v1",
}


def _wire(decision="SELECTED", key=None, seat=None, **extra):
    key = REQUEST["request_key"] if key is None else key
    seat = REQUEST["seat_id"] if seat is None else seat
    base = (
        f"{decision} key={key} seat={seat} "
        f"counterparty={REQUEST['counterparty_key']} "
        f"route={REQUEST['route_sha256']} purpose={REQUEST['purpose_sha256']} "
        f"retry={REQUEST['retry_policy_generation']}"
    )
    if decision == "SELECTED":
        base += f" writer={extra.get('writer', 'writer-1')}"
    elif decision == "HOLD":
        base += f" reason={extra.get('reason', 'wait')}"
    elif decision == "COLLISION":
        base += f" holders={extra.get('holders', 'a,b')}"
    return base


class ClearReplyParserTests(unittest.TestCase):
    def test_prose_cleared_reject(self):
        text = (
            "Cleared: you are the one sending/publishing email: "
            "MUSE ARBITRATION REQUEST · key=OUTBOUND-EMAIL-CLAIM-ABCDEF0123456789FULLKEY. "
            "Go. If this goes unanswered..."
        )
        got = parse_clear_reply(text, REQUEST)
        self.assertFalse(got["ok"])
        self.assertEqual(got["reason"], REASON_UNDERBOUND_PROSE)

    def test_truncated_key_reject(self):
        short = REQUEST["request_key"][:20]
        text = _wire(key=short)
        got = parse_clear_reply(text, REQUEST)
        self.assertFalse(got["ok"])
        self.assertEqual(got["reason"], REASON_KEY_TRUNCATED)

        prose = f"Cleared: key={short}… you are the one sending"
        got2 = parse_clear_reply(prose, REQUEST)
        self.assertFalse(got2["ok"])
        self.assertEqual(got2["reason"], REASON_KEY_TRUNCATED)

    def test_exact_selected_accept(self):
        text = _wire("SELECTED")
        got = parse_clear_reply(text, REQUEST)
        self.assertTrue(got["ok"])
        self.assertEqual(got["reason"], REASON_OK)
        self.assertEqual(got["decision"], "SELECTED")
        self.assertEqual(got["bound"]["bound_request_key"], REQUEST["request_key"])
        self.assertEqual(got["bound"]["bound_seat_id"], REQUEST["seat_id"])
        self.assertEqual(got["bound"]["bound_route_sha256"], REQUEST["route_sha256"])

    def test_key_mismatch_reject(self):
        text = _wire(key="TOTALLY-OTHER-KEY-NOT-A-PREFIX")
        got = parse_clear_reply(text, REQUEST)
        self.assertFalse(got["ok"])
        self.assertEqual(got["reason"], REASON_KEY_MISMATCH)

    def test_bound_mismatch_reject(self):
        text = _wire(seat="Z-OTHER")
        got = parse_clear_reply(text, REQUEST)
        self.assertFalse(got["ok"])
        self.assertEqual(got["reason"], REASON_BOUND_MISMATCH)

    def test_hold_and_collision_accept(self):
        for decision in ("HOLD", "COLLISION"):
            got = parse_clear_reply(_wire(decision), REQUEST)
            self.assertTrue(got["ok"], decision)
            self.assertEqual(got["decision"], decision)


class DeepSeekFallbackTests(unittest.TestCase):
    def test_mint_from_request(self):
        minted = mint_decision_from_request(REQUEST, decision="SELECTED", writer_id="w1")
        event = minted["decision_event"]
        self.assertEqual(event["type"], "DECISION")
        self.assertEqual(event["decision"], "SELECTED")
        self.assertEqual(event["bound_request_key"], REQUEST["request_key"])
        self.assertEqual(event["bound_purpose_sha256"], REQUEST["purpose_sha256"])
        self.assertFalse(minted["meta"]["sends_email"])

    def test_clear_or_fallback_uses_muse_when_ok(self):
        result = clear_or_fallback(_wire("SELECTED"), REQUEST)
        self.assertEqual(result["source"], "muse")
        self.assertEqual(result["parse"]["reason"], REASON_OK)
        self.assertEqual(result["decision_event"]["decision"], "SELECTED")
        self.assertFalse(result["sends_email"])

    def test_clear_or_fallback_mints_on_prose(self):
        prose = "Cleared: you are the one sending/publishing email: key=WRONG"
        result = clear_or_fallback(prose, REQUEST, writer_id="fallback-writer")
        self.assertEqual(result["source"], "deepseek_fallback")
        self.assertNotEqual(result["parse"]["reason"], REASON_OK)
        self.assertEqual(result["decision_event"]["bound_request_key"], REQUEST["request_key"])
        self.assertFalse(result["sends_email"])


if __name__ == "__main__":
    unittest.main()
