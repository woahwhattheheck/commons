from __future__ import annotations

import copy
import importlib.util
import tempfile
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


if __name__ == "__main__":
    unittest.main()
