from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from host.titan_hands.mcp_one import TOOL, dispatch
from host.titan_hands.one_tool import TitanHandsOne, contains_pixel_payload, default_factories
from host.titan_hands.pay import (
    DEFAULT_SKU,
    PayServer,
    mint_session_token,
    require_paid_session,
    session_token_matches,
)
from host.titan_hands.wireless import WirelessHandsServer, apk_status
from host.titan_hands_windows.protocol import PROTOCOL_VERSION


class FakeStripe:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.sessions: dict[str, dict] = {}
        self.next_id = 1

    def __call__(self, method, path, secret, fields=None):
        self.calls.append((method, path, dict(fields) if fields else None))
        if method == "POST" and path == "/checkout/sessions":
            environment = "live" if secret.startswith(("sk_live_", "rk_live_")) else "test"
            session_id = f"cs_{environment}_{self.next_id}"
            self.next_id += 1
            row = {
                "id": session_id,
                "url": f"https://checkout.stripe.com/c/pay/{session_id}",
                "payment_status": "unpaid",
                "livemode": environment == "live",
                "mode": (fields or {}).get("mode"),
                "client_reference_id": (fields or {}).get("client_reference_id"),
                "metadata": {
                    "titan_hands": (fields or {}).get("metadata[titan_hands]"),
                    "commons_sku": (fields or {}).get("metadata[commons_sku]"),
                },
            }
            self.sessions[session_id] = row
            return dict(row)
        if method == "GET" and path.startswith("/checkout/sessions/"):
            session_id = path.rsplit("/", 1)[-1]
            if session_id not in self.sessions:
                from host.titan_hands.lanes import LaneError

                raise LaneError("PAY_PROVIDER_ERROR", f"missing session {session_id}", path=path)
            return dict(self.sessions[session_id])
        raise AssertionError(f"unexpected Stripe call {method} {path}")

    def mark_paid(self, session_id: str) -> None:
        self.sessions[session_id]["payment_status"] = "paid"


class PayLaneTests(unittest.TestCase):
    def setUp(self):
        self.stripe = FakeStripe()
        self.pay = PayServer(environ={}, stripe=self.stripe)
        self.paid = PayServer(environ={"STRIPE_SECRET_KEY": "sk_live_not_a_real_key"}, stripe=self.stripe)

    def test_observe_lists_live_payment_links_without_secret(self):
        observed = self.pay.handle({"op": "observe"})
        self.assertTrue(observed["ok"])
        self.assertFalse(contains_pixel_payload(observed))
        slugs = {node["name"] for node in observed["added"] if node["role"] == "Link"}
        self.assertIn("unlock", slugs)
        self.assertIn("muhlnickel-titan", slugs)
        self.assertFalse(observed["meta"]["probe"]["stripe_secret_key"])
        self.assertEqual(observed["meta"]["probe"]["live_sku_count"], 7)

    def test_link_returns_landed_buy_url(self):
        linked = self.pay.handle(
            {"op": "act", "action": {"type": "link", "sku": "unlock"}, "observe_after": False}
        )
        self.assertTrue(linked["ok"])
        self.assertEqual(linked["checkout_url"], "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04")
        self.assertEqual(linked["charge"], "payment_link")
        self.assertFalse(self.stripe.calls)

    def test_checkout_without_key_is_pay_unconfigured(self):
        result = self.pay.handle({"op": "act", "action": {"type": "checkout", "sku": "unlock"}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_reason"], "PAY_UNCONFIGURED")
        self.assertEqual(result["evidence"]["payment_link"], "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04")
        self.assertFalse(result["evidence"]["stripe_secret_key"])
        self.assertFalse(self.stripe.calls)

    def test_checkout_with_key_creates_stripe_session(self):
        created = self.paid.handle(
            {"op": "act", "action": {"type": "checkout", "sku": "unlock"}, "observe_after": False}
        )
        self.assertTrue(created["ok"])
        self.assertEqual(created["charge"], "checkout_session")
        self.assertTrue(created["checkout_url"].startswith("https://checkout.stripe.com/"))
        self.assertEqual(created["checkout_session_id"], "cs_test_1")
        method, path, fields = self.stripe.calls[0]
        self.assertEqual((method, path), ("POST", "/checkout/sessions"))
        self.assertEqual(fields["line_items[0][price]"], "price_1U8lflATH4EDE7XD6xNapRSL")
        self.assertEqual(fields["mode"], "payment")
        self.assertNotIn("sk_live_not_a_real_key", json.dumps(created))

    def test_verify_paid_mints_session_handle(self):
        created = self.paid.handle(
            {"op": "act", "action": {"type": "checkout", "sku": DEFAULT_SKU}, "observe_after": False}
        )
        self.stripe.mark_paid(created["checkout_session_id"])
        verified = self.paid.handle(
            {
                "op": "act",
                "action": {"type": "verify", "checkout_session_id": created["checkout_session_id"]},
                "observe_after": False,
            }
        )
        self.assertTrue(verified["ok"])
        self.assertTrue(verified["paid"])
        self.assertEqual(
            verified["paid_session"],
            mint_session_token("sk_live_not_a_real_key", created["checkout_session_id"]),
        )
        again = self.paid.handle(
            {
                "op": "act",
                "action": {"type": "verify", "paid_session": verified["paid_session"]},
                "observe_after": False,
            }
        )
        self.assertTrue(again["ok"])

    def test_paid_testmode_does_not_mint_session_handle(self):
        sandbox = PayServer(environ={"STRIPE_SECRET_KEY": "sk_test_not_a_real_key"}, stripe=self.stripe)
        created = sandbox.handle(
            {"op": "act", "action": {"type": "checkout", "sku": DEFAULT_SKU}, "observe_after": False}
        )
        self.stripe.mark_paid(created["checkout_session_id"])
        verified = sandbox.handle(
            {
                "op": "act",
                "action": {"type": "verify", "checkout_session_id": created["checkout_session_id"]},
                "observe_after": False,
            }
        )
        self.assertFalse(verified["ok"])
        self.assertEqual(verified["failure_reason"], "PAY_TESTMODE")
        self.assertTrue(verified["provider_paid"])
        self.assertNotIn("paid_session", verified)

    def test_paid_unbound_session_does_not_mint_handle(self):
        self.stripe.sessions["cs_live_unrelated"] = {
            "id": "cs_live_unrelated",
            "payment_status": "paid",
            "livemode": True,
            "client_reference_id": "some-other-product",
            "metadata": {},
        }
        verified = self.paid.handle(
            {
                "op": "act",
                "action": {"type": "verify", "checkout_session_id": "cs_live_unrelated"},
                "observe_after": False,
            }
        )
        self.assertFalse(verified["ok"])
        self.assertEqual(verified["failure_reason"], "PAY_UNBOUND")
        self.assertNotIn("paid_session", verified)

    def test_verify_unpaid_is_typed(self):
        created = self.paid.handle(
            {"op": "act", "action": {"type": "checkout"}, "observe_after": False}
        )
        unpaid = self.paid.handle(
            {
                "op": "act",
                "action": {"type": "verify", "checkout_session_id": created["checkout_session_id"]},
                "observe_after": False,
            }
        )
        self.assertFalse(unpaid["ok"])
        self.assertEqual(unpaid["failure_reason"], "PAY_UNPAID")

    def test_verify_without_key_is_pay_unconfigured(self):
        result = self.pay.handle({"op": "act", "action": {"type": "verify", "checkout_session_id": "cs_x"}})
        self.assertEqual(result["failure_reason"], "PAY_UNCONFIGURED")

    def test_session_token_rejects_wrong_secret(self):
        token = mint_session_token("sk_a", "cs_live_1")
        with self.assertRaises(Exception):
            session_token_matches("sk_b", token)

    def test_one_tool_default_includes_pay_and_stays_one_mcp_tool(self):
        names = sorted(default_factories(None))
        self.assertIn("pay", names)
        self.assertIn("wireless", names)
        self.assertEqual(TOOL["name"], "titan_hands")
        router = TitanHandsOne(
            factories={"pay": lambda: PayServer(environ={}, stripe=self.stripe)},
            default_target="pay",
        )
        self.addCleanup(router.close)
        listed = dispatch(router, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual([tool["name"] for tool in listed["result"]["tools"]], ["titan_hands"])
        catalog = router.handle({"op": "targets"})
        self.assertEqual(catalog["next_adapter"], "linux-at-spi")
        self.assertEqual(catalog["model_facing_tools"], 1)
        captured = router.handle({"op": "capture", "target": "pay"})
        self.assertEqual(captured["failure_reason"], "PIXEL_UNSUPPORTED")


class WirelessLaneTests(unittest.TestCase):
    def setUp(self):
        self.stripe = FakeStripe()
        self.pay = PayServer(environ={"STRIPE_SECRET_KEY": "sk_live_not_a_real_key"}, stripe=self.stripe)

    def test_bind_without_key_is_pay_unconfigured(self):
        wireless = WirelessHandsServer(environ={}, pay=PayServer(environ={}, stripe=self.stripe))
        self.addCleanup(wireless.close)
        result = wireless.handle({"op": "act", "action": {"type": "bind"}})
        self.assertEqual(result["failure_reason"], "PAY_UNCONFIGURED")
        self.assertFalse(result["evidence"]["stripe_secret_key"])
        self.assertGreaterEqual(result["evidence"]["live_sku_count"], 1)

    def test_bind_unpaid_is_pay_unpaid(self):
        created = self.pay.handle({"op": "act", "action": {"type": "checkout"}, "observe_after": False})
        wireless = WirelessHandsServer(environ={"STRIPE_SECRET_KEY": "sk_live_not_a_real_key"}, pay=self.pay)
        self.addCleanup(wireless.close)
        result = wireless.handle(
            {
                "op": "act",
                "action": {"type": "bind", "checkout_session_id": created["checkout_session_id"]},
            }
        )
        self.assertEqual(result["failure_reason"], "PAY_UNPAID")

    def test_paid_bind_serves_status_and_forwards_hands(self):
        created = self.pay.handle({"op": "act", "action": {"type": "checkout"}, "observe_after": False})
        self.stripe.mark_paid(created["checkout_session_id"])
        verified = self.pay.handle(
            {
                "op": "act",
                "action": {"type": "verify", "checkout_session_id": created["checkout_session_id"]},
                "observe_after": False,
            }
        )

        class FilesOnly:
            def handle(self, request):
                return {
                    "ok": True,
                    "protocol": PROTOCOL_VERSION,
                    "kind": "action_outcome",
                    "target": request.get("target"),
                    "op": request.get("op"),
                    "echo": request.get("text") or "ok",
                }

            def close(self):
                return None

        wireless = WirelessHandsServer(
            environ={"STRIPE_SECRET_KEY": "sk_live_not_a_real_key"},
            pay=self.pay,
            router_factory=lambda: FilesOnly(),
            host="127.0.0.1",
            port=0,
        )
        self.addCleanup(wireless.close)
        bound = wireless.handle(
            {
                "op": "act",
                "action": {"type": "bind", "paid_session": verified["paid_session"]},
                "observe_after": False,
            }
        )
        self.assertTrue(bound["ok"], msg=bound)
        self.assertTrue(bound["url"].startswith("http://127.0.0.1:"))
        status = json.loads(urlopen(bound["url"], timeout=5).read().decode("utf-8"))
        self.assertTrue(status["ok"])
        self.assertEqual(status["recipe"], "host/titan_hands/build_lda_apk.sh")
        missing = json.loads(urlopen(bound["apk_url"], timeout=5).read().decode("utf-8"))
        self.assertEqual(missing["failure_reason"], "APK_MISS")

        payload = json.dumps(
            {
                "op": "act",
                "target": "files",
                "text": "hello",
                "paid_session": verified["paid_session"],
            }
        ).encode("utf-8")
        request = Request(
            bound["hands_url"],
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        forwarded = json.loads(urlopen(request, timeout=5).read().decode("utf-8"))
        self.assertTrue(forwarded["ok"])
        self.assertEqual(forwarded["echo"], "hello")

        nested = json.dumps({"op": "act", "target": "wireless", "paid_session": verified["paid_session"]}).encode()
        nested_req = Request(
            bound["hands_url"],
            data=nested,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        nested_body = json.loads(urlopen(nested_req, timeout=5).read().decode("utf-8"))
        self.assertEqual(nested_body["failure_reason"], "INVALID_REQUEST")

    def test_apk_status_names_existing_lda_path(self):
        info = apk_status()
        self.assertEqual(info["apk_rel"], "lda/app/build/outputs/apk/debug/app-debug.apk")
        self.assertTrue(Path(info["recipe"]).is_file() or info["recipe_present"])
        self.assertEqual(info["gradle"], "lda/app/build.gradle")

    def test_require_paid_session_without_key(self):
        result = require_paid_session({}, pay=PayServer(environ={}))
        self.assertEqual(result["failure_reason"], "PAY_UNCONFIGURED")


if __name__ == "__main__":
    unittest.main()
