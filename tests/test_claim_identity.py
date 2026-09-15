import json
import unittest
from unittest import mock

from host import claim_identity as ci


class IdentityNormalizationTests(unittest.TestCase):
    def test_nfkc_case_and_space_equivalence(self):
        self.assertEqual(
            ci.normalize_display_name("  Ｚ-NeonAnchor   1948-C3V7  "),
            "z-neonanchor 1948-c3v7",
        )
        self.assertEqual(
            ci.identity_operation(" Z-NEONANCHOR  1948-C3V7 "),
            "swarm-display-name:z-neonanchor 1948-c3v7",
        )

    def test_equivalent_spellings_share_existing_work_key(self):
        a = ci.cw.work_key(ci.identity_operation(" Ａgent   One "))
        b = ci.cw.work_key(ci.identity_operation("agent one"))
        self.assertEqual(a, b)

    def test_different_display_names_do_not_alias(self):
        a = ci.cw.work_key(ci.identity_operation("agent one"))
        b = ci.cw.work_key(ci.identity_operation("agent two"))
        self.assertNotEqual(a, b)

    def test_display_name_rejects_empty_controls_and_oversize(self):
        for bad in ("", "   ", "abc\nxyz", "abc\n", "\tabc", "x" * 121):
            with self.subTest(bad=repr(bad)[:30]):
                with self.assertRaises(ValueError):
                    ci.normalize_display_name(bad)


class SessionTagTests(unittest.TestCase):
    def test_same_tag_is_stable_different_tag_is_distinct(self):
        self.assertEqual(ci.session_holder("session-A1"), ci.session_holder("session-A1"))
        self.assertNotEqual(ci.session_holder("session-A1"), ci.session_holder("session-A2"))

    def test_raw_tag_is_not_embedded_in_holder(self):
        raw = "opaque-session-ABC123"
        holder = ci.session_holder(raw)
        self.assertNotIn(raw, holder)
        self.assertRegex(holder, r"^session-[0-9a-f]{32}$")
        self.assertEqual(len(ci.session_tag_sha256(raw)), 64)

    def test_session_tag_rejects_whitespace_unicode_controls_and_oversize(self):
        for bad in ("", " bad", "bad tag", "ågent", "bad\n", "x" * 129, "_starts-bad"):
            with self.subTest(bad=repr(bad)[:30]):
                with self.assertRaises(ValueError):
                    ci.normalize_session_tag(bad)


class AdapterTests(unittest.TestCase):
    def test_take_delegates_only_to_existing_work_claim_rail(self):
        upstream = {"ok": True, "key": "work-x-deadbeef"}
        with mock.patch.object(ci.cw, "write_claim", return_value=upstream) as call:
            out = ci.write_identity_claim(
                object(), "tag-A1", "take", display_name=" Z-Alpha ",
                ttl_s=900, note="chat bind", push=False, attempts=5,
            )
        self.assertTrue(out["ok"])
        self.assertEqual(out["verdict"], "NAME_CLEAR_FOR_COORDINATION")
        args, kwargs = call.call_args
        self.assertEqual(args[1], ci.session_holder("tag-A1"))
        self.assertEqual(args[2], "take")
        self.assertEqual(kwargs["work"], "swarm-display-name:z-alpha")
        self.assertEqual(kwargs["ttl_s"], 900)
        self.assertFalse(kwargs["push"])
        self.assertEqual(kwargs["attempts"], 5)
        self.assertIn("non-auth", kwargs["note"])

    def test_collision_recommends_rename_and_grants_zero_authority(self):
        upstream = {"ok": False, "held_by": "session-deadbeef"}
        with mock.patch.object(ci.cw, "write_claim", return_value=upstream):
            out = ci.write_identity_claim(
                object(), "tag-B2", "take", display_name="Z-Alpha"
            )
        self.assertFalse(out["ok"])
        self.assertEqual(out["verdict"], "NAME_COLLISION_RENAME_RECOMMENDED")
        for key in (
            "authenticated", "posting_authority", "source_authority", "merge_authority",
            "provider_authority", "payment_authority",
        ):
            self.assertIs(out[key], False)
        self.assertTrue(out["coordination_only"])

    def test_raw_session_tag_never_returns_or_reaches_underlying_holder(self):
        raw = "very-specific-session-tag-991"
        with mock.patch.object(ci.cw, "write_claim", return_value={"ok": True}) as call:
            out = ci.write_identity_claim(object(), raw, "take", display_name="Z-Alpha")
        self.assertNotIn(raw, json.dumps(out, sort_keys=True))
        self.assertNotIn(raw, call.call_args.args[1])
        self.assertEqual(out["session_tag_sha256"], ci.session_tag_sha256(raw))

    def test_renew_and_release_are_advisory_and_preserve_failure(self):
        for action, ok, verdict in (
            ("renew", True, "NAME_RENEWED"),
            ("renew", False, "NAME_RENEW_RECONCILE"),
            ("release", True, "NAME_RELEASED"),
            ("release", False, "NAME_RELEASE_RECONCILE"),
        ):
            with self.subTest(action=action, ok=ok):
                with mock.patch.object(ci.cw, "write_claim", return_value={"ok": ok}):
                    out = ci.write_identity_claim(object(), "tag-C3", action, display_name="Z-C")
                self.assertEqual(out["verdict"], verdict)
                self.assertIs(out["merge_authority"], False)

    def test_status_observes_adapter_claim_without_free_name_claim(self):
        with mock.patch.object(ci.cw, "claim_status", return_value={"ok": True, "held": True}) as call:
            live = ci.identity_status(object(), display_name=" Z-Alpha ")
        self.assertEqual(live["verdict"], "NAME_LIVE_ADAPTER_CLAIM_OBSERVED")
        self.assertEqual(call.call_args.kwargs["work"], "swarm-display-name:z-alpha")
        self.assertIs(live["authenticated"], False)

        with mock.patch.object(ci.cw, "claim_status", return_value={"ok": True, "held": False}):
            absent = ci.identity_status(object(), display_name="Z-Alpha")
        self.assertEqual(absent["verdict"], "NO_LIVE_ADAPTER_CLAIM_OBSERVED")
        self.assertNotIn("free", absent["verdict"].casefold())

    def test_invalid_inputs_fail_before_ledger_mutation(self):
        with mock.patch.object(ci.cw, "write_claim") as call:
            with self.assertRaises(ValueError):
                ci.write_identity_claim(object(), "bad tag", "take", display_name="Z-A")
            with self.assertRaises(ValueError):
                ci.write_identity_claim(object(), "tag-A", "take", display_name="bad\nname")
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
