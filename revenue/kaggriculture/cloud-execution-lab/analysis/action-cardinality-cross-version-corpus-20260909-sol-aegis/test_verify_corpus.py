from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import verify_corpus as corpus

HERE = Path(__file__).resolve().parent


def seal(value: dict) -> dict:
    value = copy.deepcopy(value)
    value.pop("corpus_sha256", None)
    value["corpus_sha256"] = corpus.sha256(corpus.canonical_bytes(value))
    return value


def observation(hands: int, player: int) -> dict:
    farms = [{"hands": []}, {"hands": []}]
    farms[player] = {"hands": [{"x": i, "y": 0} for i in range(hands)]}
    return {"player": player, "farms": farms}


def action(hands: int) -> dict:
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}


class ManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = corpus.strict_loads((HERE / "CORPUS.json").read_bytes())

    def test_committed_manifest_verifies(self) -> None:
        self.assertEqual(corpus.verify_manifest(self.manifest), (True, "verified"))
        self.assertEqual(self.manifest["corpus_sha256"], "ef320c17e787f8e8e8821e61aefda118980e152fe0f69b6a37f58eba3fa597fc")

    def test_digest_tamper_is_rejected(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["summary"]["unreachable_rows"] = 999
        self.assertFalse(corpus.verify_manifest(changed)[0])

    def test_rehashed_bad_aggregate_is_rejected(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["summary"]["unreachable_rows"] = 999
        changed = seal(changed)
        valid, detail = corpus.verify_manifest(changed)
        self.assertFalse(valid)
        self.assertIn("does not re-derive", detail)

    def test_rehashed_interpretation_escalation_is_rejected(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["interpretation"] = "PASS means release-ready."
        changed = seal(changed)
        valid, detail = corpus.verify_manifest(changed)
        self.assertFalse(valid)
        self.assertIn("interpretation contract", detail)

    def test_bool_is_not_an_integer(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["sources"][0]["seat"] = True
        changed = seal(changed)
        self.assertFalse(corpus.verify_manifest(changed)[0])

    def test_day5_divergence_is_rejected_after_rehash(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["sources"][0]["blocks"][0]["unreachable_opcodes"][0] = "EAST"
        changed["summary"]["opcode_counts"]["EAST"] += 1
        changed["summary"]["opcode_counts"]["WEST"] -= 1
        changed = seal(changed)
        valid, detail = corpus.verify_manifest(changed)
        self.assertFalse(valid)
        self.assertIn("day-5 sequence", detail)

    def test_strict_json_rejects_duplicate_and_nonfinite_values(self) -> None:
        with self.assertRaises(corpus.CorpusError):
            corpus.strict_loads(b'{"x": 1, "x": 2}')
        with self.assertRaises(corpus.CorpusError):
            corpus.strict_loads(b'{"x": NaN}')


class ReplayOrientationTest(unittest.TestCase):
    def test_action_k_uses_observation_k_minus_one(self) -> None:
        document = {
            "steps": [
                [
                    {"observation": observation(1, 0), "action": action(1)},
                    {"observation": observation(0, 1), "action": action(0)},
                ],
                [
                    # Post-state grew to two hands, but the action was chosen
                    # from the prior one-hand state and is therefore excess.
                    {"observation": observation(2, 0), "action": action(2)},
                    {"observation": observation(0, 1), "action": action(0)},
                ],
            ]
        }
        decisions, findings = corpus.derive_replay(document, "fixture")
        self.assertEqual(decisions, 2)
        self.assertEqual(
            findings,
            [{
                "seat": 0,
                "step": 1,
                "observable_hands": 1,
                "submitted_hand_rows": 2,
                "unreachable_opcodes": ["PASS"],
            }],
        )

    def test_post_state_shrink_does_not_invent_a_violation(self) -> None:
        document = {
            "steps": [
                [{"observation": observation(2, 0), "action": action(2)}],
                [{"observation": observation(1, 0), "action": action(2)}],
            ]
        }
        self.assertEqual(corpus.derive_replay(document, "fixture"), (1, []))

    def test_optional_raw_replay_verification_checks_both_hash_layers(self) -> None:
        document = {
            "steps": [
                [{"observation": observation(1, 0), "action": action(1)}],
                [{"observation": observation(1, 0), "action": action(2)}],
            ]
        }
        decoded = json.dumps(document, sort_keys=True).encode()
        raw = gzip.compress(decoded, mtime=0)
        source = {
            "episode": 1,
            "filename": "1.json.gz",
            "slack_file_id": "F0TEST",
            "transport_bytes": len(raw),
            "transport_sha256": corpus.sha256(raw),
            "json_bytes": len(decoded),
            "json_sha256": corpus.sha256(decoded),
            "decisions_audited": 1,
            "seat": 0,
            "blocks": [{
                "start_step": 1,
                "end_step": 1,
                "observable_hands": 1,
                "submitted_hand_rows": 2,
                "unreachable_opcodes": ["PASS"],
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / source["filename"]
            path.write_bytes(raw)
            corpus.verify_replay_files({"sources": [source]}, Path(directory))
            path.write_bytes(raw + b"x")
            with self.assertRaisesRegex(corpus.CorpusError, "transport identity"):
                corpus.verify_replay_files({"sources": [source]}, Path(directory))


if __name__ == "__main__":
    unittest.main()
