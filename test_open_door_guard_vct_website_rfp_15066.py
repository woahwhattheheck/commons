#!/usr/bin/env python3
"""Regression for PR 15066 open-door denial wording. Do not remint the guard."""

from __future__ import annotations

from pathlib import Path
import unittest

import open_door_guard as guard

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "revenue/vancouver_civic_theatres_website"
README = PACKAGE / "README.md"
ENGINE = PACKAGE / "engine.py"
TEST_ENGINE = PACKAGE / "test_engine.py"
README_REL = "revenue/vancouver_civic_theatres_website/README.md"
ENGINE_REL = "revenue/vancouver_civic_theatres_website/engine.py"
TEST_REL = "revenue/vancouver_civic_theatres_website/test_engine.py"


def diff(path: str, added=(), removed=()) -> str:
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(1, len(removed))} +1,{max(1, len(added))} @@",
    ]
    lines.extend(f"-{line}" for line in removed)
    lines.extend(f"+{line}" for line in added)
    return "\n".join(lines) + "\n"


def rules(text: str) -> set[str]:
    return {item.rule for item in guard.scan_diff(text)}


def _added(path: str, text: str) -> list[guard.AddedLine]:
    return [
        guard.AddedLine(path, number, line)
        for number, line in enumerate(text.splitlines(), 1)
    ]


class VctWebsiteRfpOpenDoor15066Tests(unittest.TestCase):
    def test_original_readme_denial_line_is_blocked(self):
        denial = "Not " + "authorized"
        original = (
            denial
            + ": supplier-account creation; acceptance of legal terms; buyer "
            "email/phone/questions; portal mutation; proposal submission; "
            "signatures/certifications; invented credentials/references; "
            "staffing commitments; binding price; contract acceptance; spend; "
            "award/payment/revenue claims."
        )
        self.assertEqual(rules(diff(README_REL, [original])), {"explicit-denial"})

    def test_original_engine_denial_line_is_blocked(self):
        permit = "not " + "permitted"
        original = (
            'raise ContractError(f"company_evidence.{name}: '
            "NOT_APPLICABLE is " + permit + ' for this required response")'
        )
        self.assertEqual(rules(diff(ENGINE_REL, [original])), {"explicit-denial"})

    def test_original_test_denial_line_is_blocked(self):
        permit = "not " + "permitted"
        original = (
            "with self.assertRaisesRegex(engine.ContractError, "
            '"NOT_APPLICABLE is ' + permit + '"):'
        )
        self.assertEqual(rules(diff(TEST_REL, [original])), {"explicit-denial"})

    def test_live_package_records_no_send_and_keeps_fail_closed_schema(self):
        readme = README.read_text(encoding="utf-8")
        engine = ENGINE.read_text(encoding="utf-8")
        tests = TEST_ENGINE.read_text(encoding="utf-8")
        self.assertNotIn("not " + "authorized", readme.lower())
        self.assertNotIn("not " + "permitted", readme.lower())
        self.assertNotIn("not " + "permitted", engine)
        self.assertNotIn("not " + "permitted", tests)
        self.assertIn("This land records no supplier-account creation", readme)
        self.assertIn("NOT_APPLICABLE is invalid for this required response", engine)
        self.assertIn("NOT_APPLICABLE is invalid", tests)

    def test_live_package_scans_clean(self):
        package_added: list[guard.AddedLine] = []
        for path in sorted(PACKAGE.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if not guard.active_path(rel):
                continue
            package_added.extend(_added(rel, path.read_text(encoding="utf-8")))
        found = guard.scan_added(package_added)
        self.assertEqual(found, [])

    def test_this_file_scans_clean(self):
        self_added = _added(Path(__file__).name, Path(__file__).read_text(encoding="utf-8"))
        self.assertEqual(guard.scan_added(self_added), [])


if __name__ == "__main__":
    unittest.main()
