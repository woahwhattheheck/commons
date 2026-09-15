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
        path.write_text(r2r.canonical_text(observations), encoding="utf-8")
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
            "QUESTION": "DRAFT_REPLY",
            "POSITIVE_SCOPE": "NEEDS_ACCEPTANCE",
            "AUTO_RESPONSE": "WAIT_FOR_HUMAN_REPLY",
            "DELIVERY_FAILURE": "RECOVER_ROUTE_OWNER_REVIEW",
        }
        return {
            "event_ref": event_ref,
            "received_at": received_at,
            "prospect_key": prospect_key,
            "payload_sha256": ("a" if classification != "AUTO_RESPONSE" else "b") * 64,
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
            path.write_text(core.canonical_text(observations), encoding="utf-8")
            with self.assertRaisesRegex(
                core.CollisionError,
                "different observation envelope",
            ):
                core.load_observations(path)

    def test_core_reduces_the_single_generation_it_reads(self) -> None:
        core = load_direct_core()
        generation_a = core.read_object(core.OBSERVATIONS_PATH)
        generation_b = copy.deepcopy(generation_a)
        duplicate = copy.deepcopy(generation_b["events"][0])
        duplicate["requested_classification"] = "NEGATIVE"
        generation_b["events"].append(duplicate)
        generation_b["monitor"]["attributed_inbound"] = len(generation_a["events"])
        generations = [generation_a, generation_b]
        calls = 0

        def swapping_reader(_path: Path) -> dict:
            nonlocal calls
            value = generations[min(calls, len(generations) - 1)]
            calls += 1
            return copy.deepcopy(value)

        core.read_object = swapping_reader
        loaded = core.load_observations(Path("ignored.json"))
        self.assertEqual(calls, 1)
        self.assertEqual(len(loaded["events"]), len(generation_a["events"]))
        self.assertEqual(
            [event["event_ref"] for event in loaded["events"]],
            [event["event_ref"] for event in generation_a["events"]],
        )

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
