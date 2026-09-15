from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reply_to_revenue_event_identity",
    ROOT / "host" / "reply_to_revenue.py",
)
assert SPEC and SPEC.loader
r2r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r2r)


def load_direct_core():
    spec = importlib.util.spec_from_file_location(
        "reply_to_revenue_core_direct",
        ROOT / "host" / "reply_to_revenue_core.py",
    )
    assert spec and spec.loader
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


class ReplyToRevenueEventIdentityTests(unittest.TestCase):
    def _write(self, directory: str, observations: dict) -> Path:
        path = Path(directory) / "observations.json"
        path.write_text(json.dumps(observations, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return path

    def _receipt(self, prospect_key: str = "buyer-one") -> dict:
        return {
            "path": "fixture-receipt.json",
            "receipt_id": "fixture-receipt",
            "prospect_key": prospect_key,
            "organization": "Fixture Org",
            "recipient_email": None,
            "provider_reference": None,
            "provider_state": "COMPLETED",
            "response_state": "UNKNOWN",
            "hard_dnr": True,
            "cash_usd": 0,
            "observed_at": "2026-09-14T20:00:00Z",
        }

    def _event(
        self,
        event_ref: str,
        classification: str,
        *,
        received_at: str = "2026-09-14T20:00:00Z",
        prospect_key: str = "buyer-one",
    ) -> dict:
        next_actions = {
            "OPT_OUT": "DNC/CLOSE",
            "NEGATIVE": "CLOSE",
            "QUESTION": "DRAFT_REPLY",
            "POSITIVE_SCOPE": "NEEDS_ACCEPTANCE",
            "NEEDS_HUMAN": "ESCALATE_ONLY_IF_BUYER_REQUESTS_BRYCE",
            "AUTO_RESPONSE": "WAIT_FOR_HUMAN_REPLY",
            "DELIVERY_FAILURE": "RECOVER_ROUTE_OWNER_REVIEW",
        }
        return {
            "event_ref": event_ref,
            "received_at": received_at,
            "prospect_key": prospect_key,
            "payload_sha256": ("b" if classification == "AUTO_RESPONSE" else "a") * 64,
            "provider": "fixture-provider",
            "matched_receipt_id": "fixture-receipt",
            "classification": classification,
            "next_action": next_actions[classification],
            "buyer_interest": classification == "POSITIVE_SCOPE",
            "auto_ack": classification == "AUTO_RESPONSE",
            "delivery_failure": classification == "DELIVERY_FAILURE",
            "matched_markers": [],
            "reason": "fixture classification",
        }

    def _observations(self, events: list[dict]) -> dict:
        return {
            "schema_version": "commons-reply-to-revenue-observations/v1",
            "kind": "REPLY_TO_REVENUE_OBSERVATIONS",
            "measured_at": "2026-09-14T20:10:00Z",
            "monitor": {
                "connector": "fixture",
                "status": "complete",
                "mailbox_claim": "fixture",
                "sends": 0,
                "queries": 1,
                "attributed_inbound": len(events),
            },
            "events": events,
        }

    def test_identical_full_envelope_retry_is_ingested_once(self) -> None:
        observations = r2r.read_object(r2r.OBSERVATIONS_PATH)
        observations["events"].append(copy.deepcopy(observations["events"][0]))
        observations["monitor"]["attributed_inbound"] = len(observations["events"]) - 1
        with tempfile.TemporaryDirectory() as directory:
            loaded = r2r.load_observations(self._write(directory, observations))
        self.assertEqual(len(loaded["events"]), 4)

    def test_same_ref_and_payload_with_changed_envelope_collides(self) -> None:
        original = r2r.read_object(r2r.OBSERVATIONS_PATH)
        mutations = {
            "received_at": "2026-08-26T14:08:11Z",
            "prospect_key": "different-buyer",
            "markers": ["operator note only"],
            "provider": "different-provider",
            "matched_receipt_id": "different-receipt",
            "requested_classification": "NEGATIVE",
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                observations = copy.deepcopy(original)
                duplicate = copy.deepcopy(observations["events"][0])
                duplicate[field] = value
                observations["events"].append(duplicate)
                observations["monitor"]["attributed_inbound"] = len(original["events"])
                with self.assertRaisesRegex(
                    r2r.CollisionError,
                    "different observation envelope",
                ):
                    r2r.load_observations(self._write(directory, observations))

    def test_direct_core_import_enforces_full_envelope_identity(self) -> None:
        core = load_direct_core()
        observations = core.read_object(core.OBSERVATIONS_PATH)
        duplicate = copy.deepcopy(observations["events"][0])
        duplicate["provider"] = "different-provider"
        observations["events"].append(duplicate)
        observations["monitor"]["attributed_inbound"] = len(observations["events"]) - 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.json"
            path.write_text(json.dumps(observations), encoding="utf-8")
            with self.assertRaisesRegex(
                core.CollisionError,
                "different observation envelope",
            ):
                core.load_observations(path)

    def test_core_reads_exactly_one_observation_generation(self) -> None:
        core = load_direct_core()
        generation_a = core.read_object(core.OBSERVATIONS_PATH)
        generation_b = copy.deepcopy(generation_a)
        duplicate = copy.deepcopy(generation_b["events"][0])
        duplicate["requested_classification"] = "NEGATIVE"
        generation_b["events"].append(duplicate)
        generation_b["monitor"]["attributed_inbound"] = len(generation_a["events"])
        generations = [generation_a, generation_b]

        class SwappingPath:
            def __init__(self) -> None:
                self.calls = 0

            def read_text(self, *, encoding: str) -> str:
                self.assert_encoding(encoding)
                value = generations[min(self.calls, len(generations) - 1)]
                self.calls += 1
                return json.dumps(value, sort_keys=True, indent=2) + "\n"

            @staticmethod
            def assert_encoding(encoding: str) -> None:
                if encoding != "utf-8":
                    raise AssertionError(f"unexpected encoding: {encoding}")

            def __str__(self) -> str:
                return "swapping-observations.json"

        path = SwappingPath()
        loaded = core.load_observations(path)
        self.assertEqual(path.calls, 1)
        self.assertEqual(len(loaded["events"]), len(generation_a["events"]))
        self.assertEqual(
            [event["event_ref"] for event in loaded["events"]],
            [event["event_ref"] for event in generation_a["events"]],
        )

    def test_observation_loader_survives_public_and_retained_helper_poisoning(self) -> None:
        core = load_direct_core()
        original = core.read_object(core.OBSERVATIONS_PATH)
        with tempfile.TemporaryDirectory() as directory:
            clean_path = self._write(directory, original)
            baseline = core.load_observations(clean_path)

            poison_classification = lambda _markers, _requested=None: {
                "classification": "POSITIVE_SCOPE",
                "next_action": "NEEDS_ACCEPTANCE",
                "buyer_interest": True,
                "auto_ack": False,
                "delivery_failure": False,
                "matched_markers": [],
                "reason": "POISONED",
            }
            for target in (core, core._impl):
                target.sha256_text = lambda _value: "0" * 64
                target.canonical_text = lambda _value: "POISONED\n"
                target.classify_signals = poison_classification
                target.parse_time = lambda _value: 0
                target._assert_observation_window = lambda _measured, _events: None
                target.DELIVERY_FAILURE_MARKERS = ("everything",)
                target.AUTO_ACK_MARKERS = ("everything",)
                target.POSITIVE_MARKERS = ("everything",)
                target.CLASS_TO_NEXT = {"POSITIVE_SCOPE": "POISONED"}

            loaded = core.load_observations(clean_path)
            self.assertEqual(loaded, baseline)
            self.assertNotIn("POISONED", json.dumps(loaded, sort_keys=True))

            collision = copy.deepcopy(original)
            duplicate = copy.deepcopy(collision["events"][0])
            duplicate["provider"] = "different-provider"
            collision["events"].append(duplicate)
            collision["monitor"]["attributed_inbound"] = len(original["events"])
            collision_path = Path(directory) / "collision.json"
            collision_path.write_text(json.dumps(collision), encoding="utf-8")
            with self.assertRaisesRegex(core.CollisionError, "different observation envelope"):
                core.load_observations(collision_path)

    def test_wrapper_and_direct_core_share_authoritative_policy_bindings(self) -> None:
        self.assertIs(r2r._core._impl._reduce_contact_state, r2r._reduce_contact_state)
        self.assertIs(r2r._core._impl.surface_positives, r2r.surface_positives)
        core = load_direct_core()
        self.assertIs(core._impl._reduce_contact_state, core._reduce_contact_state)
        self.assertIs(core._impl.surface_positives, core.surface_positives)

    def test_build_funnel_preserves_equal_time_opt_out(self) -> None:
        events = [
            self._event("opaque:opt-out-0001", "OPT_OUT"),
            self._event("opaque:question-0001", "QUESTION"),
        ]
        funnel = r2r.build_funnel(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        contact = next(item for item in funnel["contacts"] if item["prospect_key"] == "buyer-one")
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")
        self.assertEqual(funnel["truth"]["human_question"], 0)
        self.assertEqual(funnel["truth"]["human_positive"], 0)

    def test_direct_core_build_funnel_preserves_equal_time_opt_out(self) -> None:
        core = load_direct_core()
        events = [
            self._event("opaque:direct-opt-out-0001", "OPT_OUT"),
            self._event("opaque:direct-question-0001", "QUESTION"),
        ]
        funnel = core.build_funnel(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        contact = next(item for item in funnel["contacts"] if item["prospect_key"] == "buyer-one")
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")
        self.assertEqual(funnel["truth"]["human_question"], 0)
        self.assertEqual(funnel["truth"]["human_positive"], 0)

    def test_direct_core_reducer_ignores_poisoned_retained_chronology(self) -> None:
        core = load_direct_core()
        events = [
            self._event("opaque:older-positive-0001", "POSITIVE_SCOPE", received_at="2026-09-14T20:00:00Z"),
            self._event("opaque:newer-negative-0001", "NEGATIVE", received_at="2026-09-14T20:01:00Z"),
        ]

        def poisoned_impl_time(value: str) -> int:
            if value.endswith("20:10:00Z"):
                return 3
            if value.endswith("20:00:00Z"):
                return 2
            if value.endswith("20:01:00Z"):
                return 1
            return 0

        core._impl.parse_time = poisoned_impl_time
        funnel = core.build_funnel(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        contact = next(item for item in funnel["contacts"] if item["prospect_key"] == "buyer-one")
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "CLOSE")
        self.assertEqual(funnel["truth"]["human_positive"], 0)
        self.assertEqual(funnel["surfaces"], [])

    def test_direct_core_policy_survives_post_import_public_global_poisoning(self) -> None:
        core = load_direct_core()
        installed_reducer = core._impl._reduce_contact_state
        core._frozen_parse_time = lambda _value: (_ for _ in ()).throw(AssertionError("poisoned frozen alias"))
        core._latest_human_bucket = lambda _events: []
        core.parse_time = lambda _value: (_ for _ in ()).throw(AssertionError("poisoned parse_time"))
        core._reduce_contact_state = lambda _events: {
            "classification": "QUESTION",
            "lane": "NEEDS_HUMAN",
            "next_action": "DRAFT_REPLY",
            "handoff": None,
            "effective_event": None,
        }
        core.ACCEPTANCE_TOOL = "POISONED_ACCEPTANCE_TOOL"
        core.REPLY_INTAKE_TOOL = "POISONED_REPLY_TOOL"
        core.ROUTE_RECOVERY_TOOL = "POISONED_ROUTE_TOOL"
        self.assertIs(core._impl._reduce_contact_state, installed_reducer)
        events = [
            self._event("opaque:poison-opt-out-0001", "OPT_OUT"),
            self._event("opaque:poison-question-0001", "QUESTION"),
        ]
        funnel = core.build_funnel(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        contact = next(item for item in funnel["contacts"] if item["prospect_key"] == "buyer-one")
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")
        self.assertEqual(funnel["truth"]["human_question"], 0)
        self.assertEqual(funnel["truth"]["human_positive"], 0)

    def test_cli_surface_reports_recorded_machine_observation_truthfully(self) -> None:
        events = [
            self._event("opaque:positive-0001", "POSITIVE_SCOPE", received_at="2026-09-14T20:00:00Z"),
            self._event("opaque:auto-ack-0001", "AUTO_RESPONSE", received_at="2026-09-14T20:01:00Z"),
        ]
        receipts = [self._receipt()]
        observations = self._observations(events)
        impl = r2r._core._impl
        original_load_receipts = impl.load_receipts
        original_load_observations = impl.load_observations
        impl.load_receipts = lambda: copy.deepcopy(receipts)
        impl.load_observations = lambda: copy.deepcopy(observations)
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                result = r2r._core.main(["surface"])
        finally:
            impl.load_receipts = original_load_receipts
            impl.load_observations = original_load_observations
        self.assertEqual(result, 0)
        surfaces = json.loads(output.getvalue())
        self.assertEqual(len(surfaces), 1)
        context = surfaces[0]["context"]
        self.assertIn("recorded machine observations (AUTO_RESPONSE)", context)
        self.assertNotIn("were absent", context)

    def test_direct_core_surface_survives_post_import_public_global_poisoning(self) -> None:
        core = load_direct_core()
        events = [
            self._event("opaque:poison-positive-0001", "POSITIVE_SCOPE", received_at="2026-09-14T20:00:00Z"),
            self._event("opaque:poison-auto-ack-0001", "AUTO_RESPONSE", received_at="2026-09-14T20:01:00Z"),
        ]
        receipts = [self._receipt()]
        observations = self._observations(events)
        impl = core._impl
        installed_surface = impl.surface_positives
        core._MACHINE_CLASSIFICATIONS = frozenset()
        core._positive_context = lambda _events: "POISONED PUBLIC CONTEXT"
        core.surface_positives = lambda _contacts, _inbound: []
        core.ACCEPTANCE_TOOL = "POISONED_ACCEPTANCE_TOOL"
        core.ReplyRevenueError = AssertionError
        self.assertIs(impl.surface_positives, installed_surface)
        original_load_receipts = impl.load_receipts
        original_load_observations = impl.load_observations
        impl.load_receipts = lambda: copy.deepcopy(receipts)
        impl.load_observations = lambda: copy.deepcopy(observations)
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                result = impl.main(["surface"])
        finally:
            impl.load_receipts = original_load_receipts
            impl.load_observations = original_load_observations
        self.assertEqual(result, 0)
        surfaces = json.loads(output.getvalue())
        self.assertEqual(len(surfaces), 1)
        context = surfaces[0]["context"]
        self.assertIn("recorded machine observations (AUTO_RESPONSE)", context)
        self.assertNotIn("POISONED PUBLIC CONTEXT", context)
        self.assertNotEqual(surfaces[0]["handoff"], "POISONED_ACCEPTANCE_TOOL")

    def test_fresh_process_direct_core_cli_uses_authoritative_surface_policy(self) -> None:
        events = [
            self._event("opaque:process-positive-0001", "POSITIVE_SCOPE", received_at="2026-09-14T20:00:00Z"),
            self._event("opaque:process-auto-ack-0001", "AUTO_RESPONSE", received_at="2026-09-14T20:01:00Z"),
        ]
        receipts = [self._receipt()]
        observations = self._observations(events)
        core_path = ROOT / "host" / "reply_to_revenue_core.py"
        script = textwrap.dedent(
            f"""
            import importlib.util
            import json
            from pathlib import Path

            core_path = Path({str(core_path)!r})
            spec = importlib.util.spec_from_file_location("fresh_direct_core_cli", core_path)
            assert spec and spec.loader
            core = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(core)
            receipts = {receipts!r}
            observations = {observations!r}
            core._impl.load_receipts = lambda: receipts
            core._impl.load_observations = lambda: observations
            raise SystemExit(core._impl.main(["surface"]))
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        surfaces = json.loads(completed.stdout)
        self.assertEqual(len(surfaces), 1)
        context = surfaces[0]["context"]
        self.assertIn("recorded machine observations (AUTO_RESPONSE)", context)
        self.assertNotIn("were absent", context)


if __name__ == "__main__":
    unittest.main()
