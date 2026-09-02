#!/usr/bin/env python3
"""Living templates/rules/memories/skills must not carry the invented 337 NO signature.

Historical p/ receipts stay untouched and are excluded. The two EOF whitespace
tests must keep their POSIX / extra-blank / CR / git-diff-check purpose without
pinning the invented closer as a living convention.
"""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
SIGNATURE = "337 NO"

LIVING_ROOT_FILES = (
    "AGENTS.md",
    "skills.html",
)
LIVING_DIRS = (
    "ground",
    "memory",
    "skills",
    ".cursor",
    ".agents",
    ".github",
)
SKIP_DIR_NAMES = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
TEXT_SUFFIXES = {
    ".md",
    ".mdc",
    ".html",
    ".json",
    ".txt",
    ".yml",
    ".yaml",
    ".py",
    ".js",
    ".css",
}


def living_paths() -> list[Path]:
    out: list[Path] = []
    for name in LIVING_ROOT_FILES:
        path = ROOT / name
        if path.is_file():
            out.append(path)
    for path in ROOT.glob("_sd_*"):
        if path.is_file():
            out.append(path)
    for dirname in LIVING_DIRS:
        base = ROOT / dirname
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith("_sd_"):
                out.append(path)
    out.sort()
    return out


class Invented337SignatureAbsentFromLivingSources(unittest.TestCase):
    def test_living_templates_rules_memories_skills_exclude_historical_posts(self) -> None:
        paths = living_paths()
        self.assertTrue(paths, "living source set must be nonempty")
        for path in paths:
            rel = path.relative_to(ROOT).as_posix()
            self.assertFalse(rel.startswith("p/"), rel)
            self.assertNotEqual(rel.split("/", 1)[0], "p")

    def test_living_sources_do_not_carry_invented_signature(self) -> None:
        hits: list[str] = []
        for path in living_paths():
            raw = path.read_bytes()
            if SIGNATURE.encode("utf-8") in raw:
                hits.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(hits, [], f"invented signature still in living sources: {hits}")

    def test_named_20260902_living_cards_do_not_carry_invented_signature(self) -> None:
        """Regression for the 2026-09-02 battery: these three living cards reintroduced 337 NO."""
        for rel in (
            ".cursor/rules/github-already-logged-in.mdc",
            "ground/BUSINESS_PACK_KEEP_SELL.md",
            "ground/HARNESS_ALREADY_LOGGED_IN.md",
        ):
            raw = (ROOT / rel).read_bytes()
            self.assertNotIn(SIGNATURE.encode("utf-8"), raw, rel)

    def test_player2_projection_does_not_reintroduce_invented_closer(self) -> None:
        """memory/PLAYER2 is a living projection; the historical p/ receipt stays untouched."""
        for rel in ("memory/PLAYER2.json", "memory/PLAYER2.html"):
            raw = (ROOT / rel).read_bytes()
            self.assertNotIn(SIGNATURE.encode("utf-8"), raw, rel)
        receipt = ROOT / "p/p2-memory-create-20260821-01.md"
        self.assertTrue(receipt.is_file(), receipt)
        self.assertIn(SIGNATURE, receipt.read_text(encoding="utf-8"))

    def test_historical_chargeable_checkout_receipt_blob_is_untouched(self) -> None:
        import subprocess

        receipt = "p/grok-build-chargeable-checkout-20260828-01.md"
        blob = subprocess.check_output(
            ["git", "-C", str(ROOT), "hash-object", receipt],
            text=True,
        ).strip()
        self.assertEqual(blob, "12c3c15c3b819f61494b454a0d35181fc80006c7")
        raw = (ROOT / receipt).read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\n\n"))

    def test_rewritten_eof_tests_no_longer_pin_the_invented_signature(self) -> None:
        capability = (ROOT / "test_capability_entrypoints.py").read_text(encoding="utf-8")
        eof = (ROOT / "test_chargeable_checkout_eof.py").read_text(encoding="utf-8")
        self.assertNotIn('endswith("No auth. Open door stays. 337 NO.")', capability)
        self.assertNotIn('LAST_LINE = "No auth. Open door stays. 337 NO."', eof)
        self.assertNotIn(SIGNATURE, capability)
        self.assertNotIn(SIGNATURE, eof)
        self.assertIn("git diff --check HEAD^", capability)
        self.assertIn("test_chargeable_checkout_eof.py", (ROOT / ".github" / "workflows" / "capability-entrypoints.yml").read_text(encoding="utf-8"))

    def test_negative_retired_string_guards_are_preserved(self) -> None:
        guards = (
            "test_active_instruction_drift.py",
            "test_standalone_open_doors.py",
            "test_record_append_open_roads.py",
            "test_issue_template_open_door.py",
            "test_court_open_door.py",
        )
        for name in guards:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('assertNotIn', text, name)
            self.assertIn(SIGNATURE, text, name)


if __name__ == "__main__":
    unittest.main()
