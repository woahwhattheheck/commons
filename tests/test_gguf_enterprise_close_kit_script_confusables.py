from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "close_kit.py"
INTAKE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "sample_intake.json"
EVIDENCE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "sample_evidence.json"

spec = importlib.util.spec_from_file_location("gguf_close_kit_confusable_test", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class GgufScriptConfusablePrivacyTests(unittest.TestCase):
    def test_nfkc_stable_script_confusable_contacts_are_rejected(self) -> None:
        for value in (
            "contact jane@exаmple.test for the harness",  # U+0430 CYRILLIC SMALL A
            "contact jоhn@example.test for the harness",  # U+043E CYRILLIC SMALL O
        ):
            with self.subTest(value=value):
                intake = load(INTAKE)
                intake["scope"]["objective"] = value
                with self.assertRaisesRegex(mod.InputError, "sensitive/private"):
                    mod.compile_packet(intake, load(EVIDENCE))

    def test_every_public_scope_text_field_rejects_non_ascii_script_confusables(self) -> None:
        cases = (
            ("model_label", "mоdel_demo"),       # Cyrillic o
            ("objective", "public evaluatiоn"),  # Cyrillic o
            ("harness_label", "hаrness_demo"),   # Cyrillic a
            ("start_window", "WІNDOW_DEMO"),     # Cyrillic capital Byelorussian-Ukrainian I
        )
        for field, value in cases:
            with self.subTest(field=field):
                intake = load(INTAKE)
                intake["scope"][field] = value
                with self.assertRaisesRegex(mod.InputError, "sensitive/private"):
                    mod.compile_packet(intake, load(EVIDENCE))


if __name__ == "__main__":
    unittest.main()
