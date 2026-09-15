from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WRAPPER_PATH = ROOT / "host" / "reply_to_revenue.py"
CORE_PATH = ROOT / "host" / "reply_to_revenue_core.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r2r = load_module(WRAPPER_PATH, "reply_to_revenue_event_identity_wrapper")


def load_direct_core():
    return load_module(CORE_PATH, "reply_to_revenue_event_identity_core")


class ReplyToRevenueEventIdentityTests(unittest.TestCase):
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
        payload_char: str = "a",
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
            "payload_sha256": payload_char * 64,
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

    def _raw_event(
        self,
        event_ref: str,
        requested: str | None,
        *,
        markers: list[str] | None = None,
        received_at: str = "2026-09-14T20:00:00Z",
        payload_char: str = "a",
    ) -> dict:
        return {
            "event_ref": event_ref,
            "received_at": received_at,
            "prospect_key": "buyer-one",
            "payload_sha256": payload_char * 64,
            "markers": [] if markers is None else markers,
            "provider": "fixture-provider",
            "matched_receipt_id": "fixture-receipt",
            "requested_classification": requested,
        }

    def _raw_observations(self, events: list[dict]) -> dict:
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

    def _write_json(self, directory: str, name: str, value: dict) -> Path:
        path = Path(directory) / name
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return path

    def test_core_exposes_no_retained_dispatch_namespace(self) -> None:
        core = load_direct_core()
        self.assertFalse(hasattr(core, "_impl"))
        self.assertFalse(hasattr(core, "_RUNTIME"))
        self.assertFalse(hasattr(core, "_make_runtime"))
        self.assertIn("arbitrary trusted same-process Python reflection", core.AUTHORITY_BOUNDARY)

    def test_wrapper_drops_private_loaded_core_handle(self) -> None:
        wrapper = load_module(WRAPPER_PATH, "reply_to_revenue_wrapper_no_dispatch")
        self.assertFalse(hasattr(wrapper, "_loaded_core"))
        self.assertFalse(hasattr(wrapper, "_core"))
        self.assertFalse(hasattr(wrapper, "_cli_entrypoint"))
        self.assertTrue(callable(wrapper.build_funnel))
        self.assertTrue(callable(wrapper._run_cli))

    def test_identical_full_envelope_retry_is_ingested_once(self) -> None:
        core = load_direct_core()
        event = self._raw_event("opaque:retry-event-0001", "QUESTION")
        observations = self._raw_observations([event, copy.deepcopy(event)])
        observations["monitor"]["attributed_inbound"] = 1
        with tempfile.TemporaryDirectory() as directory:
            loaded = core.load_observations(
                self._write_json(directory, "observations.json", observations)
            )
        self.assertEqual(len(loaded["events"]), 1)
        self.assertEqual(loaded["events"][0]["classification"], "QUESTION")

    def test_same_ref_and_payload_with_changed_envelope_collides(self) -> None:
        core = load_direct_core()
        original = self._raw_event("opaque:collision-event-0001", "QUESTION")
        mutations = {
            "received_at": "2026-09-14T19:59:59Z",
            "prospect_key": "different-buyer",
            "markers": ["operator note only"],
            "provider": "different-provider",
            "matched_receipt_id": "different-receipt",
            "requested_classification": "NEGATIVE",
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                duplicate = copy.deepcopy(original)
                duplicate[field] = value
                observations = self._raw_observations([original, duplicate])
                observations["monitor"]["attributed_inbound"] = 1
                path = self._write_json(directory, "observations.json", observations)
                with self.assertRaisesRegex(
                    core.CollisionError,
                    "different observation envelope",
                ):
                    core.load_observations(path)

    def test_loader_reads_one_generation(self) -> None:
        core = load_direct_core()
        first = self._raw_observations(
            [self._raw_event("opaque:generation-a-0001", "QUESTION")]
        )
        second = copy.deepcopy(first)
        second_event = copy.deepcopy(second["events"][0])
        second_event["requested_classification"] = "NEGATIVE"
        second["events"].append(second_event)
        second["monitor"]["attributed_inbound"] = 1

        class SwappingPath:
            def __init__(self) -> None:
                self.calls = 0

            def read_text(self, *, encoding: str) -> str:
                if encoding != "utf-8":
                    raise AssertionError(f"unexpected encoding: {encoding}")
                generations = [first, second]
                value = generations[min(self.calls, len(generations) - 1)]
                self.calls += 1
                return json.dumps(value, sort_keys=True, indent=2) + "\n"

            def __str__(self) -> str:
                return "swapping-observations.json"

        path = SwappingPath()
        loaded = core.load_observations(path)
        self.assertEqual(path.calls, 1)
        self.assertEqual(len(loaded["events"]), 1)
        self.assertEqual(loaded["events"][0]["classification"], "QUESTION")

    def test_captured_loader_ignores_public_helper_and_constant_rebinding(self) -> None:
        core = load_direct_core()
        loader = core.load_observations
        raw = self._raw_observations(
            [
                self._raw_event(
                    "opaque:loader-authority-0001",
                    "POSITIVE_SCOPE",
                    markers=["please invoice"],
                )
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_json(directory, "observations.json", raw)
            baseline = loader(path)

            core.load_observations = lambda _path=path: {"POISONED": True}
            core.read_object = lambda _path: {"POISONED": True}
            core.sha256_text = lambda _value: "0" * 64
            core.canonical_text = lambda _value: "POISONED\n"
            core.classify_signals = lambda *_args, **_kwargs: {
                "classification": "NEGATIVE",
                "next_action": "CLOSE",
                "buyer_interest": False,
                "auto_ack": False,
                "delivery_failure": False,
                "matched_markers": [],
                "reason": "POISONED",
            }
            core.parse_time = lambda _value: 0
            core._assert_observation_window = lambda _measured, _events: None
            core.DELIVERY_FAILURE_MARKERS = ("everything",)
            core.AUTO_ACK_MARKERS = ("everything",)
            core.POSITIVE_MARKERS = ("everything",)
            core.CLASS_TO_NEXT = {"POSITIVE_SCOPE": "POISONED"}
            core.OPAQUE_RE = None
            core.PROSPECT_RE = None
            core.SHA256_RE = None
            core.json = None
            core.hashlib = None
            core.dt = None

            loaded = loader(path)
            self.assertEqual(loaded, baseline)
            self.assertEqual(loaded["events"][0]["classification"], "POSITIVE_SCOPE")
            self.assertNotIn("POISONED", json.dumps(loaded, sort_keys=True))

            changed = copy.deepcopy(raw)
            duplicate = copy.deepcopy(changed["events"][0])
            duplicate["provider"] = "different-provider"
            changed["events"].append(duplicate)
            changed["monitor"]["attributed_inbound"] = 1
            changed_path = self._write_json(directory, "collision.json", changed)
            with self.assertRaisesRegex(
                core.CollisionError,
                "different observation envelope",
            ):
                loader(changed_path)

    def test_equal_time_opt_out_remains_dnc(self) -> None:
        core = load_direct_core()
        events = [
            self._event("opaque:opt-out-0001", "OPT_OUT", payload_char="a"),
            self._event("opaque:question-0001", "QUESTION", payload_char="b"),
        ]
        funnel = core.build_funnel(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        contact = funnel["contacts"][0]
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")
        self.assertEqual(funnel["truth"]["human_question"], 0)
        self.assertEqual(funnel["truth"]["human_positive"], 0)
        self.assertEqual(funnel["surfaces"], [])

    def test_captured_build_ignores_wholesale_public_authority_replacement(self) -> None:
        core = load_direct_core()
        build = core.build_funnel
        events = [
            self._event("opaque:dispatch-opt-out-0001", "OPT_OUT", payload_char="a"),
            self._event("opaque:dispatch-question-0001", "QUESTION", payload_char="b"),
        ]
        receipts = [self._receipt()]
        observations = self._observations(events)

        def poisoned_reducer(_events):
            return {
                "classification": "POSITIVE_SCOPE",
                "lane": "HUMAN_POSITIVE",
                "next_action": "NEEDS_ACCEPTANCE",
                "handoff": "POISONED",
                "effective_event": _events[0] if _events else None,
            }

        core._reduce_contact_state = poisoned_reducer
        core._contact_rows = lambda *_args: [
            {
                "prospect_key": "buyer-one",
                "organization": "POISONED",
                "hard_dnr": True,
                "lane": "HUMAN_POSITIVE",
                "next_action": "NEEDS_ACCEPTANCE",
                "handoff": "POISONED",
                "receipt_count": 1,
                "inbound_count": 2,
                "cash_usd": 0,
                "resend": False,
            }
        ]
        core.surface_positives = lambda *_args: [{"POISONED": True}]
        core.load_observations = lambda *_args, **_kwargs: {"POISONED": True}
        core.load_receipts = lambda *_args, **_kwargs: [{"POISONED": True}]
        core._assert_observation_window = lambda *_args: None
        core.parse_time = lambda _value: 0
        core.ACCEPTANCE_TOOL = "POISONED"
        core.REPLY_INTAKE_TOOL = "POISONED"
        core.ROUTE_RECOVERY_TOOL = "POISONED"
        core.PUBLIC_LIMITS[:] = ["POISONED"]

        funnel = build(receipts=receipts, observations=observations)
        contact = funnel["contacts"][0]
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "DNC/CLOSE")
        self.assertEqual(funnel["surfaces"], [])
        self.assertNotEqual(funnel["limits"], ["POISONED"])

    def test_captured_build_uses_true_chronology_after_public_time_poisoning(self) -> None:
        core = load_direct_core()
        build = core.build_funnel
        events = [
            self._event(
                "opaque:older-positive-0001",
                "POSITIVE_SCOPE",
                received_at="2026-09-14T20:00:00Z",
                payload_char="a",
            ),
            self._event(
                "opaque:newer-negative-0001",
                "NEGATIVE",
                received_at="2026-09-14T20:01:00Z",
                payload_char="b",
            ),
        ]

        core.parse_time = lambda value: (
            3 if value.endswith("20:10:00Z")
            else 2 if value.endswith("20:00:00Z")
            else 1
        )
        core._latest_event = lambda events: events[0]
        core._latest_human_bucket = lambda events: events[:1]

        funnel = build(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        contact = funnel["contacts"][0]
        self.assertEqual(contact["lane"], "CLOSED")
        self.assertEqual(contact["next_action"], "CLOSE")
        self.assertEqual(funnel["truth"]["human_positive"], 0)
        self.assertEqual(funnel["surfaces"], [])

    def test_positive_surface_truthfully_keeps_machine_provenance(self) -> None:
        core = load_direct_core()
        events = [
            self._event(
                "opaque:positive-0001",
                "POSITIVE_SCOPE",
                received_at="2026-09-14T20:00:00Z",
                payload_char="a",
            ),
            self._event(
                "opaque:auto-ack-0001",
                "AUTO_RESPONSE",
                received_at="2026-09-14T20:01:00Z",
                payload_char="b",
            ),
        ]
        funnel = core.build_funnel(
            receipts=[self._receipt()],
            observations=self._observations(events),
        )
        self.assertEqual(len(funnel["surfaces"]), 1)
        context = funnel["surfaces"][0]["context"]
        self.assertIn("recorded machine observations (AUTO_RESPONSE)", context)
        self.assertNotIn("were absent", context)

    def test_captured_surface_ignores_public_surface_replacement(self) -> None:
        core = load_direct_core()
        surface = core.surface_positives
        reducer = core._reduce_contact_state
        events = [
            self._event(
                "opaque:surface-positive-0001",
                "POSITIVE_SCOPE",
                received_at="2026-09-14T20:00:00Z",
                payload_char="a",
            ),
            self._event(
                "opaque:surface-auto-0001",
                "AUTO_RESPONSE",
                received_at="2026-09-14T20:01:00Z",
                payload_char="b",
            ),
        ]
        state = reducer(events)
        contacts = [
            {
                "prospect_key": "buyer-one",
                "organization": "Fixture Org",
                "lane": state["lane"],
            }
        ]

        core._reduce_contact_state = lambda _events: {
            "classification": "NEGATIVE",
            "lane": "CLOSED",
            "next_action": "CLOSE",
            "handoff": None,
            "effective_event": None,
        }
        core._positive_context = lambda _events: "POISONED"
        core.surface_positives = lambda *_args: []
        core.ACCEPTANCE_TOOL = "POISONED"

        surfaces = surface(contacts, events)
        self.assertEqual(len(surfaces), 1)
        self.assertIn(
            "recorded machine observations (AUTO_RESPONSE)",
            surfaces[0]["context"],
        )
        self.assertNotEqual(surfaces[0]["handoff"], "POISONED")

    def test_route_recovery_uses_captured_chronology_and_handoff(self) -> None:
        core = load_direct_core()
        recover = core.surface_route_recovery
        contacts = [
            {
                "prospect_key": "buyer-one",
                "organization": "Fixture Org",
                "lane": "DELIVERY_FAILURE",
            }
        ]
        events = [
            self._event(
                "opaque:failure-older-0001",
                "DELIVERY_FAILURE",
                received_at="2026-09-14T20:00:00Z",
                payload_char="a",
            ),
            self._event(
                "opaque:failure-newer-0001",
                "DELIVERY_FAILURE",
                received_at="2026-09-14T20:01:00Z",
                payload_char="b",
            ),
        ]
        core.parse_time = lambda _value: 0
        core._latest_event = lambda rows: rows[0]
        core.ROUTE_RECOVERY_TOOL = "POISONED"

        result = recover(contacts, events)
        self.assertEqual(result["items"][0]["event_ref"], "opaque:failure-newer-0001")
        self.assertNotEqual(result["items"][0]["handoff"], "POISONED")

    def test_wrapper_and_direct_core_produce_same_policy_result(self) -> None:
        core = load_direct_core()
        events = [
            self._event("opaque:parity-opt-out-0001", "OPT_OUT", payload_char="a"),
            self._event("opaque:parity-question-0001", "QUESTION", payload_char="b"),
        ]
        receipts = [self._receipt()]
        observations = self._observations(events)
        self.assertEqual(
            r2r.build_funnel(receipts=copy.deepcopy(receipts), observations=copy.deepcopy(observations)),
            core.build_funnel(receipts=copy.deepcopy(receipts), observations=copy.deepcopy(observations)),
        )

    def test_fresh_process_direct_core_has_no_impl_and_preserves_dnc(self) -> None:
        receipt = self._receipt()
        observations = self._observations(
            [
                self._event("opaque:process-opt-out-0001", "OPT_OUT", payload_char="a"),
                self._event("opaque:process-question-0001", "QUESTION", payload_char="b"),
            ]
        )
        script = textwrap.dedent(
            f"""
            import importlib.util
            from pathlib import Path

            path = Path({str(CORE_PATH)!r})
            spec = importlib.util.spec_from_file_location("fresh_reply_core", path)
            assert spec and spec.loader
            core = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(core)
            assert not hasattr(core, "_impl")
            build = core.build_funnel
            core._reduce_contact_state = lambda _events: {{
                "classification": "POSITIVE_SCOPE",
                "lane": "HUMAN_POSITIVE",
                "next_action": "NEEDS_ACCEPTANCE",
                "handoff": "POISONED",
                "effective_event": _events[0],
            }}
            core.surface_positives = lambda *_args: [{{"POISONED": True}}]
            core.parse_time = lambda _value: 0
            result = build(receipts={[receipt]!r}, observations={observations!r})
            contact = result["contacts"][0]
            assert contact["lane"] == "CLOSED", result
            assert contact["next_action"] == "DNC/CLOSE", result
            assert result["surfaces"] == [], result
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

    def test_direct_core_cli_classify_runs_without_historical_dispatch(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(CORE_PATH),
                "classify",
                "--markers",
                "thank you for reaching out",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["classification"], "AUTO_RESPONSE")
        self.assertTrue(payload["auto_ack"])
        self.assertFalse(payload["buyer_interest"])

    def test_wrapper_cli_classify_matches_direct_core(self) -> None:
        direct = subprocess.run(
            [
                sys.executable,
                str(CORE_PATH),
                "classify",
                "--markers",
                "please invoice",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        wrapper = subprocess.run(
            [
                sys.executable,
                str(WRAPPER_PATH),
                "classify",
                "--markers",
                "please invoice",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
        self.assertEqual(json.loads(wrapper.stdout), json.loads(direct.stdout))
        self.assertEqual(json.loads(wrapper.stdout)["classification"], "POSITIVE_SCOPE")


if __name__ == "__main__":
    unittest.main()
