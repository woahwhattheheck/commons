from __future__ import annotations

import inspect
import os
from pathlib import Path

from revenue.organization_contact_pressure import compiler, gate, receipts, verifier
from .test_support import *  # noqa: F401,F403


class MonotonicFloorTests(GateTestCase):
    def _install_floor_from_head(self, generation: int) -> Path:
        head_dir = self.root / "ledger-heads" / self.fx.organization
        chosen = None
        for path in head_dir.iterdir():
            document = gate.strict_json_loads(path.read_bytes())
            if document["ledger_generation"] == generation:
                chosen = path
                break
        self.assertIsNotNone(chosen)
        floor_dir = self.root / "ledger-floors"
        floor_dir.mkdir(parents=True, exist_ok=True)
        floor = floor_dir / f"{self.fx.organization}.json"
        floor.write_bytes(chosen.read_bytes())
        if os.name != "nt":
            floor.chmod(0o600)
        return chosen

    def test_delete_newer_journal_head_cannot_revive_old_authentic_ledger(self):
        ledger_path = self.root / "ledgers" / f"{self.fx.organization}.json"
        generation_zero = gate.strict_json_loads(ledger_path.read_bytes())
        self.fx.write_ledger([self.fx.event("sent-1", gate.EVENT_SENT)])
        generation_one_head = self._install_floor_from_head(1)

        generation_one_head.unlink()
        self.fx.write_ledger([], raw_document=generation_zero, write_head=False)

        with self.assertRaisesRegex(gate.VerificationError, "monotonic floor"):
            self.fx.compile()

    def test_floor_file_is_mandatory_on_production_custody_path(self):
        from revenue.organization_contact_pressure import ledger_head

        with mock.patch.object(ledger_head, "_authority_root", return_value=self.root), \
             mock.patch.object(ledger_head, "_ledger_floor_root", return_value=self.root / "missing-floor-root"):
            ledger_path = self.root / "ledgers" / f"{self.fx.organization}.json"
            generation_zero = gate.strict_json_loads(ledger_path.read_bytes())
            self.fx.write_ledger([], raw_document=generation_zero, write_head=False)
            with self.assertRaisesRegex(gate.VerificationError, "monotonic ledger floor"):
                self.fx.compile()

    def test_supported_modules_expose_no_injected_root_or_clock_helpers(self):
        self.assertEqual(
            ["compile_current", "verify_receipt_current", "verify_receipt_integrity"],
            receipts.__all__,
        )
        injected = {
            name: getattr(gate, name)
            for name in (
                "_compile_at",
                "_verify_receipt_current_at",
                "_verify_receipt_integrity_at",
            )
        }
        try:
            for name in injected:
                delattr(gate, name)
            for module in (gate, receipts):
                for name in injected:
                    self.assertFalse(hasattr(module, name), f"{module.__name__}.{name}")
        finally:
            for name, value in injected.items():
                setattr(gate, name, value)
        self.assertEqual(("request_data",), tuple(inspect.signature(compiler.compile_current).parameters))
        self.assertEqual(("receipt_data",), tuple(inspect.signature(verifier.verify_receipt_current).parameters))
        self.assertEqual(("receipt_data",), tuple(inspect.signature(verifier.verify_receipt_integrity).parameters))


if __name__ == "__main__":
    unittest.main()
