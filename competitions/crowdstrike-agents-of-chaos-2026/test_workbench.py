from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("aoc_workbench", HERE / "workbench.py")
wb = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(wb)


def flags():
    return {
        "automated_tools_or_bots": False,
        "scoring_system_attack": False,
        "backend_exploit": False,
        "multiple_accounts_or_account_manipulation": False,
        "network_interception": False,
        "other_player_access": False,
    }


def attest():
    return {
        "registered_account": True,
        "original_work": True,
        "english_gameplay": True,
        "standard_gameplay_mechanics": True,
    }


def attempt(attempt_id="a1", puzzle_id="p1", prompt="hello", tokens=12, success=True, when="2026-09-15T07:00:00Z"):
    return {
        "attempt_id": attempt_id,
        "puzzle_id": puzzle_id,
        "prompt": prompt,
        "observed_tokens": tokens,
        "success": success,
        "observed_at_utc": when,
        "self_attested": attest(),
        "prohibited_actions": flags(),
    }


def ledger(attempts=None):
    return {"schema": wb.LEDGER_SCHEMA, "contest": wb.CONTEST, "attempts": attempts or []}


class WorkbenchTests(unittest.TestCase):
    def test_empty_ledger_is_valid_and_deterministic(self):
        one = wb.compile_ledger(ledger())
        two = wb.compile_ledger(ledger())
        self.assertEqual(one, two)
        self.assertEqual(one["puzzles"], [])
        self.assertEqual(one["authority"], "SELF_ATTESTED_ONLY")

    def test_successes_rank_by_operator_entered_tokens_only(self):
        packet = wb.compile_ledger(ledger([
            attempt("slow", prompt="x", tokens=99, success=True),
            attempt("fail", prompt="z", tokens=1, success=False),
            attempt("fast", prompt="y", tokens=7, success=True),
        ]))
        frontier = packet["puzzles"][0]["frontier"]
        self.assertEqual([r["attempt_id"] for r in frontier], ["fast", "slow"])
        self.assertEqual([r["delta_from_best"] for r in frontier], [0, 92])
        self.assertEqual(packet["scoring_semantics"]["tokenizer"], "NOT_INFERRED")
        self.assertFalse(packet["scoring_semantics"]["sponsor_score_equivalence"])

    def test_attempt_order_does_not_change_packet(self):
        rows = [attempt("b", prompt="beta", tokens=9), attempt("a", prompt="alpha", tokens=8)]
        self.assertEqual(wb.compile_ledger(ledger(rows)), wb.compile_ledger(ledger(list(reversed(rows)))))

    def test_duplicate_prompt_observations_are_reported(self):
        packet = wb.compile_ledger(ledger([
            attempt("a", prompt="same", tokens=8),
            attempt("b", prompt="same", tokens=7),
        ]))
        duplicates = packet["puzzles"][0]["duplicate_prompts"]
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["attempt_ids"], ["a", "b"])

    def test_same_prompt_in_different_puzzles_is_not_cross_flagged(self):
        packet = wb.compile_ledger(ledger([
            attempt("a", puzzle_id="p1", prompt="same"),
            attempt("b", puzzle_id="p2", prompt="same"),
        ]))
        self.assertTrue(all(not p["duplicate_prompts"] for p in packet["puzzles"]))

    def test_duplicate_attempt_id_rejected(self):
        with self.assertRaisesRegex(wb.ValidationError, "duplicate attempt_id"):
            wb.compile_ledger(ledger([attempt("a"), attempt("a", prompt="other")]))

    def test_unknown_attempt_field_rejected(self):
        row = attempt()
        row["mystery"] = 1
        with self.assertRaisesRegex(wb.ValidationError, "fields mismatch"):
            wb.compile_ledger(ledger([row]))

    def test_boolean_token_count_rejected(self):
        row = attempt(tokens=True)
        with self.assertRaisesRegex(wb.ValidationError, "JSON integer"):
            wb.compile_ledger(ledger([row]))

    def test_nonpositive_token_count_rejected(self):
        with self.assertRaisesRegex(wb.ValidationError, "out of range"):
            wb.compile_ledger(ledger([attempt(tokens=0)]))

    def test_noncanonical_timestamp_rejected(self):
        with self.assertRaisesRegex(wb.ValidationError, "YYYY-MM-DD"):
            wb.compile_ledger(ledger([attempt(when="2026-09-15T07:00:00+00:00")]))

    def test_blank_prompt_rejected(self):
        with self.assertRaisesRegex(wb.ValidationError, "byte length"):
            wb.compile_ledger(ledger([attempt(prompt="")]))

    def test_false_self_attestation_rejected(self):
        row = attempt()
        row["self_attested"]["original_work"] = False
        with self.assertRaisesRegex(wb.ValidationError, "original_work must be true"):
            wb.compile_ledger(ledger([row]))

    def test_each_prohibited_action_is_rejected(self):
        for key in wb.PROHIBITED_KEYS:
            with self.subTest(key=key):
                row = attempt()
                row["prohibited_actions"][key] = True
                with self.assertRaisesRegex(wb.ValidationError, "prohibited action declared"):
                    wb.compile_ledger(ledger([row]))

    def test_missing_prohibited_flag_rejected(self):
        row = attempt()
        del row["prohibited_actions"]["network_interception"]
        with self.assertRaisesRegex(wb.ValidationError, "fields mismatch"):
            wb.compile_ledger(ledger([row]))

    def test_duplicate_json_keys_rejected(self):
        raw = '{"schema":"x","schema":"y"}'
        with self.assertRaisesRegex(wb.ValidationError, "duplicate JSON object key"):
            wb.strict_json_loads(raw)

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(wb.ValidationError, "non-finite"):
            wb.strict_json_loads('{"x":NaN}')

    def test_packet_tamper_fails_exact_verification(self):
        source = ledger([attempt()])
        packet = wb.compile_ledger(source)
        self.assertTrue(wb.verify_packet(source, packet))
        tampered = copy.deepcopy(packet)
        tampered["attempt_count"] = 999
        self.assertFalse(wb.verify_packet(source, tampered))

    def test_source_tamper_fails_packet_verification(self):
        source = ledger([attempt()])
        packet = wb.compile_ledger(source)
        changed = ledger([attempt(prompt="changed")])
        self.assertFalse(wb.verify_packet(changed, packet))

    def test_markdown_states_authority_and_no_tokenizer_claim(self):
        packet = wb.compile_ledger(ledger([attempt()]))
        text = wb.render_markdown(packet)
        self.assertIn("SELF_ATTESTED_ONLY", text)
        self.assertIn("does not contact the contest", text)
        self.assertIn(packet["packet_sha256"], text)

    def test_publish_bundle_is_create_exclusive(self):
        packet = wb.compile_ledger(ledger([attempt()]))
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "bundle"
            paths = wb.publish_bundle(packet, out)
            self.assertEqual(set(paths), {"frontier.json", "frontier.md", "receipt.sha256"})
            with self.assertRaisesRegex(wb.ValidationError, "already exists"):
                wb.publish_bundle(packet, out)

    def test_published_packet_roundtrips(self):
        source = ledger([attempt("a", prompt="one", tokens=5), attempt("b", prompt="two", tokens=4)])
        packet = wb.compile_ledger(source)
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "bundle"
            wb.publish_bundle(packet, out)
            disk = wb.load_json_file(out / "frontier.json")
            self.assertTrue(wb.verify_packet(source, disk))
            self.assertEqual((out / "receipt.sha256").read_text().strip(), packet["packet_sha256"])

    def test_example_ledger_compiles(self):
        example = wb.load_json_file(HERE / "example-ledger.json")
        packet = wb.compile_ledger(example)
        self.assertEqual(packet["attempt_count"], 1)
        self.assertEqual(packet["successful_attempt_count"], 1)

    def test_cli_compile_and_verify(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "bundle"
            compile_run = subprocess.run(
                [sys.executable, str(HERE / "cli.py"), "compile", str(HERE / "example-ledger.json"), "--out-dir", str(out)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            verify_run = subprocess.run(
                [sys.executable, str(HERE / "cli.py"), "verify", str(HERE / "example-ledger.json"), str(out / "frontier.json")],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verify_run.returncode, 0, verify_run.stderr)
            self.assertEqual(json.loads(verify_run.stdout), {"valid": True})

    def test_cli_refuses_existing_bundle_directory(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "bundle"
            out.mkdir()
            run = subprocess.run(
                [sys.executable, str(HERE / "cli.py"), "compile", str(HERE / "example-ledger.json"), "--out-dir", str(out)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(run.returncode, 2)
            self.assertIn("refusing overwrite", run.stderr)


if __name__ == "__main__":
    unittest.main()
