#!/usr/bin/env python3
"""Fail-closed tests for the CCC snapshot toolchain.

Synthetic fixtures only. Never touch ~/.claude or real CCC bytes.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "host"))
import ccc_snapshot_toolchain as ccc


ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "host" / "ccc_snapshot_toolchain.py"
PROTOCOL = ROOT / "inventory" / "ccc_snapshot_protocol.json"
CARD = ROOT / "ground" / "CCC_VAULT_HARVEST.md"
DOOR = ROOT / "ccc-snapshot-toolchain.html"
RECEIPT = ROOT / "p" / "ccc-snapshot-toolchain-working-20260901-01.md"
PRIOR = ROOT / "p" / "ship-ccc-vault-harvest-toolchain-20260901-01.md"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class CccSnapshotToolchainTests(unittest.TestCase):
    def test_leftover_and_protocol_pins(self) -> None:
        self.assertEqual(ccc.LEFTOVER_ID, "ccc-snapshot-toolchain-working-20260901-01")
        self.assertEqual(ccc.PRIOR_FALSE_COMPLETE_ID, "ship-ccc-vault-harvest-toolchain-20260901-01")
        self.assertEqual(ccc.ISSUE, 7238)
        self.assertTrue(TOOL.is_file())
        self.assertTrue(PROTOCOL.is_file())
        self.assertTrue(CARD.is_file())
        self.assertTrue(DOOR.is_file())
        self.assertTrue(RECEIPT.is_file())
        self.assertTrue(PRIOR.is_file())
        pins = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(pins["schema"], ccc.SCHEMA)
        self.assertEqual(pins["class"], "D")
        self.assertEqual(pins["box_kind"], "DEAD_END")
        self.assertEqual(pins["direction"], "GOLD_OUT_ONLY")
        self.assertFalse(pins["write_back"])
        self.assertFalse(pins["peer_read"])
        self.assertFalse(pins["egress"])
        self.assertFalse(pins["shared_claude"])
        self.assertFalse(pins["claude_on_laptop"])
        card = CARD.read_text(encoding="utf-8")
        self.assertIn("Class D", card)
        self.assertIn("dead-end", card.lower())
        self.assertIn("No Claude on the laptop", card)
        self.assertIn("No write-back", card)
        self.assertIn("No peer remint of secrets", card)
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: ccc-snapshot-toolchain-working-20260901-01", receipt)
        self.assertIn("ship-ccc-vault-harvest-toolchain-20260901-01", receipt)
        self.assertIn("#7238", receipt)
        self.assertIn("cash_usd=0", receipt)
        self.assertIn("HOLD / BUILD-AND-VERIFY", receipt)
        self.assertNotIn("id: ship-ccc-vault-harvest-toolchain-20260901-01", receipt.split("---", 2)[-1][:80])
        door = DOOR.read_text(encoding="utf-8")
        self.assertIn("Open door", door)
        self.assertIn("No login", door)
        self.assertIn("action.html", door)

    def test_windows_and_posix_rel_round_trip(self) -> None:
        self.assertEqual(ccc.split_rel(r"gold\nest\item-b.bin"), ("gold", "nest", "item-b.bin"))
        self.assertEqual(ccc.split_rel("gold/nest/item-b.bin"), ("gold", "nest", "item-b.bin"))
        self.assertEqual(ccc.windows_rel("gold/nest/item-b.bin"), r"gold\nest\item-b.bin")
        self.assertEqual(ccc.posix_rel(r"C:\deadend\box\gold\a.txt"), "C:/deadend/box/gold/a.txt")
        with self.assertRaises(ccc.ToolchainError) as caught:
            ccc.split_rel("../escape")
        self.assertEqual(caught.exception.code, "LINK_ESCAPE")

    def test_plan_snapshot_verify_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-round-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            planned = ccc.plan(vault)
            self.assertTrue(planned["ok"])
            self.assertEqual(planned["source"]["file_count"], 3)
            self.assertFalse(planned["writes_source"])
            box = root / "dead-end"
            captured = ccc.snapshot(vault, box)
            self.assertEqual(captured["state"], "PASS")
            self.assertEqual(captured["copied"], 3)
            self.assertTrue((box / "protocol.json").is_file())
            for name in ccc.RECEIPT_NAMES:
                self.assertTrue((box / "receipts" / name).is_file())
            checked = ccc.verify(vault, box)
            self.assertEqual(checked["state"], "PASS")
            self.assertEqual(checked["sha256_tree"], planned["source"]["sha256_tree"])
            gold_a = (box / "gold" / "gold" / "item-a.txt").read_text(encoding="utf-8")
            self.assertEqual(gold_a, "synthetic gold a\n")
            source_a = (vault / "gold" / "item-a.txt").read_text(encoding="utf-8")
            self.assertEqual(source_a, "synthetic gold a\n")

    def test_cli_self_test_and_commands(self) -> None:
        probe = run_cli("self-test")
        self.assertEqual(probe.returncode, 0, probe.stderr + probe.stdout)
        payload = json.loads(probe.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["adversarial_fail_closed"], 14)
        self.assertEqual(payload["cash_usd"], 0)
        self.assertEqual(payload["happy_path"]["file_count"], 3)
        with tempfile.TemporaryDirectory(prefix="ccc-cli-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            planned = run_cli("plan", "--source", str(vault))
            self.assertEqual(planned.returncode, 0, planned.stderr)
            plan_json = json.loads(planned.stdout)
            self.assertEqual(plan_json["command"], "plan")
            box = root / "box"
            snapped = run_cli("snapshot", "--source", str(vault), "--dest", str(box))
            self.assertEqual(snapped.returncode, 0, snapped.stderr)
            verified = run_cli("verify", "--source", str(vault), "--dest", str(box))
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(json.loads(verified.stdout)["state"], "PASS")

    def test_fail_closed_manifest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-mm-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            box = root / "box"
            ccc.snapshot(vault, box)
            (box / "gold" / "gold" / "item-a.txt").write_text("nope\n", encoding="utf-8")
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.verify(vault, box)
            self.assertEqual(caught.exception.code, "MANIFEST_MISMATCH")

    def test_fail_closed_link_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-link-") as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            (src / "ok.txt").write_text("ok\n", encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("escape\n", encoding="utf-8")
            (src / "link.txt").symlink_to(outside)
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.plan(src)
            self.assertEqual(caught.exception.code, "LINK_ESCAPE")

    def test_fail_closed_isolation_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-iso-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            box = root / "box"
            ccc.snapshot(vault, box)
            os.chmod(box, 0o755)
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.verify(vault, box)
            self.assertEqual(caught.exception.code, "PEER_READ")

    def test_fail_closed_source_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-mut-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            box = root / "box"

            def hook() -> None:
                (vault / "gold" / "item-a.txt").write_text("changed\n", encoding="utf-8")

            ccc._mutation_hook = hook
            try:
                with self.assertRaises(ccc.ToolchainError) as caught:
                    ccc.snapshot(vault, box)
                self.assertEqual(caught.exception.code, "SOURCE_MUTATION")
            finally:
                ccc._mutation_hook = None

    def test_fail_closed_write_back_peer_read_egress(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-flags-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            for code, name, payload in (
                ("WRITE_BACK", "write_back.json", {"write_back": True}),
                ("PEER_READ", "peer_read.json", {"peer_read": True}),
                ("EGRESS", "egress.json", {"egress": True}),
            ):
                box = root / code.lower()
                ccc.snapshot(vault, box)
                ccc.write_exclusive_json(box / name, payload)
                with self.assertRaises(ccc.ToolchainError) as caught:
                    ccc.verify(vault, box)
                self.assertEqual(caught.exception.code, code, code)

    def test_fail_closed_leakage_and_crosstalk(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-leak-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            (vault / "gold" / "leak.txt").write_text(
                f"{ccc.PROMPT_LEAK_MARKER}\n",
                encoding="utf-8",
            )
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.snapshot(vault, root / "leak-box")
            self.assertEqual(caught.exception.code, "LEAKAGE")
            clean = ccc.make_synthetic_vault(root / "clean")
            box = root / "talk-box"
            ccc.snapshot(clean, box)
            (box / "gold" / "cross").symlink_to(root / "clean")
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.verify(clean, box)
            self.assertEqual(caught.exception.code, "CAGE_CROSSTALK")

    def test_fail_closed_false_completion_and_claude(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-fake-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            fake = root / "fake"
            fake.mkdir()
            os.chmod(fake, 0o700)
            (fake / "gold").mkdir()
            receipts = fake / "receipts"
            receipts.mkdir()
            ccc.write_exclusive_json(
                receipts / "result.json",
                {"state": "PASS", "token_burn": True},
            )
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.verify(vault, fake)
            self.assertEqual(caught.exception.code, "FALSE_COMPLETION")
            claude = root / ".claude"
            claude.mkdir()
            (claude / "x.txt").write_text("no\n", encoding="utf-8")
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.plan(claude)
            self.assertEqual(caught.exception.code, "SHARED_CLAUDE")

    def test_fail_closed_reuse_and_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-alias-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            box = root / "box"
            ccc.snapshot(vault, box)
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.snapshot(vault, box)
            self.assertEqual(caught.exception.code, "DEST_REUSE")
            with self.assertRaises(ccc.ToolchainError) as caught:
                ccc.snapshot(vault, vault)
            self.assertEqual(caught.exception.code, "ALIAS")

    def test_source_is_never_opened_for_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-ro-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            writes: list[str] = []
            real_open = os.open

            def wrapped(path, flags, *args, **kwargs):
                text = os.fspath(path)
                if Path(text).resolve() == vault.resolve() or vault.resolve() in Path(text).resolve().parents:
                    if flags & os.O_WRONLY or flags & os.O_RDWR or flags & os.O_APPEND:
                        writes.append(text)
                return real_open(path, flags, *args, **kwargs)

            os.open = wrapped  # type: ignore[method-assign]
            try:
                ccc.snapshot(vault, root / "box")
            finally:
                os.open = real_open  # type: ignore[method-assign]
            self.assertEqual(writes, [])

    def test_dead_end_mode_is_0700(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ccc-mode-") as tmp:
            root = Path(tmp)
            vault = ccc.make_synthetic_vault(root)
            box = root / "box"
            ccc.snapshot(vault, box)
            mode = stat.S_IMODE(box.stat().st_mode)
            self.assertEqual(mode, 0o700)
            gold_mode = stat.S_IMODE((box / "gold").stat().st_mode)
            self.assertEqual(gold_mode, 0o700)

    def test_self_test_named_counts(self) -> None:
        result = ccc.self_test()
        self.assertTrue(result["ok"])
        self.assertEqual(result["happy_path"]["copied"], 3)
        self.assertEqual(result["adversarial_fail_closed"], 14)
        self.assertEqual(result["adversarial_codes"]["shared_claude"], "SHARED_CLAUDE")
        self.assertEqual(result["adversarial_codes"]["false_completion_token_burn"], "FALSE_COMPLETION")
        self.assertEqual(result["cash_usd"], 0)


if __name__ == "__main__":
    unittest.main()
