from __future__ import annotations

import copy
import importlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

from revenue.human_reply_workshare_kit import core
from revenue.human_reply_workshare_kit import test_core
from revenue.human_reply_workshare_kit.test_core import base_record


ROOT = Path(__file__).resolve().parent

_RELOAD_PREDECESSOR = r'''
import copy
import importlib
import importlib.util
from revenue.human_reply_workshare_kit import core
from revenue.human_reply_workshare_kit.test_core import base_record

if importlib.util.find_spec("revenue.human_reply_workshare_kit._core_legacy") is not None:
    raise SystemExit("duplicate legacy authority module is executable")

ids = (id(core.normalize_offer), id(core.render_offer_markdown), id(core.render_receipt_json))
for _ in range(3):
    if importlib.reload(core) is not core:
        raise SystemExit("core reload changed module identity")
if ids != (id(core.normalize_offer), id(core.render_offer_markdown), id(core.render_receipt_json)):
    raise SystemExit("core reload replaced the guarded authority graph")

def expect_compile_rejected(row, label):
    try:
        core.compile_offer(row)
    except core.WorkshareError:
        return
    raise SystemExit("reload admitted " + label)

smuggled = base_record()
smuggled["opportunity_label"] = "Payment [received] for the pilot"
expect_compile_rejected(smuggled, "punctuation commercial-smuggling compile")

html_cases = []
row = base_record()
row["counterparty_label"] = "Buyer <em>accepted</em> this scope"
html_cases.append(("counterparty HTML tag", row))
row = base_record()
row["opportunity_label"] = "Payment <span>received</span> for the pilot"
html_cases.append(("opportunity HTML tag", row))
row = base_record()
row["scope"]["one_line"] = "Invoice <strong>sent</strong> yesterday"
html_cases.append(("scope HTML tag", row))
row = base_record()
row["scope"]["input_bounds"] = ["one entity", "Customer <i>relationship</i> is confirmed"]
html_cases.append(("input-bound HTML tag", row))
row = base_record()
row["counterparty_label"] = "Buyer&Tab;accepted this scope"
html_cases.append(("counterparty named entity", row))
row = base_record()
row["opportunity_label"] = "Payment&#32;received for the pilot"
html_cases.append(("opportunity numeric entity", row))
row = base_record()
row["scope"]["one_line"] = "Invoice&nbsp;sent yesterday"
html_cases.append(("scope named entity", row))
row = base_record()
row["scope"]["input_bounds"] = ["one entity", "Customer&#32;relationship is confirmed"]
html_cases.append(("input-bound numeric entity", row))
for label, row in html_cases:
    expect_compile_rejected(row, label)

valid = core.compile_offer(base_record())
forged_normalized = copy.deepcopy(dict(valid.normalized))
forged_normalized["scope"] = copy.deepcopy(dict(valid.normalized["scope"]))
forged_normalized["scope"]["one_line"] = "Buyer **accepted** this workshare"
try:
    core.render_offer_markdown(forged_normalized)
except core.WorkshareError:
    pass
else:
    raise SystemExit("reload resurrected direct-render bypass")

forged_html = copy.deepcopy(dict(valid.normalized))
forged_html["scope"] = copy.deepcopy(dict(valid.normalized["scope"]))
forged_html["scope"]["one_line"] = "Payment&#32;received for the pilot"
try:
    core.render_offer_markdown(forged_html)
except core.WorkshareError:
    pass
else:
    raise SystemExit("reload admitted HTML/entity direct-render bypass")

forged = core.CompiledOffer(
    normalized=forged_normalized,
    markdown=valid.markdown,
    receipt_sha256=valid.receipt_sha256,
)
try:
    core.render_receipt_json(forged)
except core.WorkshareError:
    pass
else:
    raise SystemExit("reload resurrected forged-receipt bypass")
'''


class HumanReplyWorkshareAuthorityGuardTests(unittest.TestCase):
    def test_no_duplicate_legacy_authority_module_exists(self):
        self.assertIsNone(
            importlib.util.find_spec("revenue.human_reply_workshare_kit._core_legacy")
        )

    def test_all_rendered_caller_fields_share_the_claim_boundary(self):
        mutations = (
            lambda row: row.__setitem__("counterparty_label", "Buyer **accepted** this scope"),
            lambda row: row.__setitem__("opportunity_label", "Payment [received] for the pilot"),
            lambda row: row["scope"].__setitem__("one_line", "Invoice *sent* yesterday"),
            lambda row: row["scope"].__setitem__(
                "input_bounds", ["one entity", "Customer relationship is confirmed"]
            ),
        )
        for mutate in mutations:
            row = base_record()
            mutate(row)
            with self.subTest(row=row):
                with self.assertRaisesRegex(core.WorkshareError, "unsupported"):
                    core.compile_offer(row)

    def test_nfkc_and_format_control_bypasses_fail_closed(self):
        row = base_record()
        row["opportunity_label"] = "Ｂｕｙｅｒ ａｃｃｅｐｔｅｄ this scope"
        with self.assertRaisesRegex(core.WorkshareError, "unsupported"):
            core.compile_offer(row)

        row = base_record()
        row["scope"]["input_bounds"] = ["one entity", "Buyer acce\u200bpted this scope"]
        with self.assertRaisesRegex(core.WorkshareError, "Unicode control/format"):
            core.compile_offer(row)

    def test_html_markup_render_equivalence_fails_closed_across_all_fields(self):
        mutations = (
            lambda row: row.__setitem__(
                "counterparty_label", "Buyer <em>accepted</em> this scope"
            ),
            lambda row: row.__setitem__(
                "opportunity_label", "Payment <span>received</span> for the pilot"
            ),
            lambda row: row["scope"].__setitem__(
                "one_line", "Invoice <strong>sent</strong> yesterday"
            ),
            lambda row: row["scope"].__setitem__(
                "input_bounds", ["one entity", "Customer <i>relationship</i> is confirmed"]
            ),
        )
        for mutate in mutations:
            row = base_record()
            mutate(row)
            with self.subTest(row=row):
                with self.assertRaisesRegex(core.WorkshareError, "HTML markup"):
                    core.compile_offer(row)

    def test_html_entity_render_equivalence_fails_closed_across_all_fields(self):
        mutations = (
            lambda row: row.__setitem__(
                "counterparty_label", "Buyer&Tab;accepted this scope"
            ),
            lambda row: row.__setitem__(
                "opportunity_label", "Payment&#32;received for the pilot"
            ),
            lambda row: row["scope"].__setitem__(
                "one_line", "Invoice&nbsp;sent yesterday"
            ),
            lambda row: row["scope"].__setitem__(
                "input_bounds", ["one entity", "Customer&#32;relationship is confirmed"]
            ),
        )
        for mutate in mutations:
            row = base_record()
            mutate(row)
            with self.subTest(row=row):
                with self.assertRaisesRegex(core.WorkshareError, "HTML entity"):
                    core.compile_offer(row)

    def test_public_renderer_revalidates_forged_normalized_state(self):
        compiled = core.compile_offer(base_record())
        forged = copy.deepcopy(dict(compiled.normalized))
        forged["scope"] = copy.deepcopy(dict(compiled.normalized["scope"]))
        forged["scope"]["input_bounds"] = ["one entity", "Payment [received] for pilot"]
        with self.assertRaisesRegex(core.WorkshareError, "unsupported"):
            core.render_offer_markdown(forged)

        forged_html = copy.deepcopy(dict(compiled.normalized))
        forged_html["scope"] = copy.deepcopy(dict(compiled.normalized["scope"]))
        forged_html["scope"]["one_line"] = "Buyer <em>accepted</em> this workshare"
        with self.assertRaisesRegex(core.WorkshareError, "HTML markup"):
            core.render_offer_markdown(forged_html)

        forged_entity = copy.deepcopy(dict(compiled.normalized))
        forged_entity["scope"] = copy.deepcopy(dict(compiled.normalized["scope"]))
        forged_entity["scope"]["one_line"] = "Payment&#32;received for the pilot"
        with self.assertRaisesRegex(core.WorkshareError, "HTML entity"):
            core.render_offer_markdown(forged_entity)

        forged = copy.deepcopy(dict(compiled.normalized))
        forged["evidence_state"] = copy.deepcopy(dict(compiled.normalized["evidence_state"]))
        forged["evidence_state"]["payment_settled"] = True
        with self.assertRaisesRegex(core.WorkshareError, "outside this qualification"):
            core.render_offer_markdown(forged)

    def test_receipt_recompiles_and_rejects_forgery_or_staleness(self):
        compiled = core.compile_offer(base_record())
        forged_normalized = copy.deepcopy(dict(compiled.normalized))
        forged_normalized["opportunity_label"] = "Payment [received] for the pilot"
        forged = core.CompiledOffer(
            normalized=forged_normalized,
            markdown=compiled.markdown,
            receipt_sha256=compiled.receipt_sha256,
        )
        with self.assertRaisesRegex(core.WorkshareError, "unsupported"):
            core.render_receipt_json(forged)

        forged_html_normalized = copy.deepcopy(dict(compiled.normalized))
        forged_html_normalized["scope"] = copy.deepcopy(dict(compiled.normalized["scope"]))
        forged_html_normalized["scope"]["one_line"] = (
            "Payment <span>received</span> for the pilot"
        )
        forged_html = core.CompiledOffer(
            normalized=forged_html_normalized,
            markdown=compiled.markdown,
            receipt_sha256=compiled.receipt_sha256,
        )
        with self.assertRaisesRegex(core.WorkshareError, "HTML markup"):
            core.render_receipt_json(forged_html)

        stale_markdown = core.CompiledOffer(
            normalized=compiled.normalized,
            markdown=compiled.markdown + "\nforged",
            receipt_sha256=compiled.receipt_sha256,
        )
        with self.assertRaisesRegex(core.WorkshareError, "markdown does not match"):
            core.render_receipt_json(stale_markdown)

        stale_hash = core.CompiledOffer(
            normalized=compiled.normalized,
            markdown=compiled.markdown,
            receipt_sha256="0" * 64,
        )
        with self.assertRaisesRegex(core.WorkshareError, "receipt hash does not match"):
            core.render_receipt_json(stale_hash)

    def test_core_reload_is_sealed_to_the_guarded_authority_graph(self):
        before = (
            id(core.normalize_offer),
            id(core.render_offer_markdown),
            id(core.render_receipt_json),
        )
        for _ in range(3):
            self.assertIs(importlib.reload(core), core)
        after = (
            id(core.normalize_offer),
            id(core.render_offer_markdown),
            id(core.render_receipt_json),
        )
        self.assertEqual(before, after)

        row = base_record()
        row["opportunity_label"] = "Payment [received] for the pilot"
        with self.assertRaises(core.WorkshareError):
            core.compile_offer(row)

        row = base_record()
        row["counterparty_label"] = "Buyer <em>accepted</em> this scope"
        with self.assertRaisesRegex(core.WorkshareError, "HTML markup"):
            core.compile_offer(row)

    def test_nonassertive_acceptance_evidence_remains_valid(self):
        row = base_record("DATA_MIGRATION_ACCEPTANCE")
        row["scope"]["one_line"] = (
            "Legacy-to-target reconciliation and acceptance evidence for one frozen migration batch."
        )
        self.assertIn("acceptance evidence", core.compile_offer(row).markdown)


class HumanReplyWorkshareOptimizedBridgeTests(unittest.TestCase):
    def test_nested_core_suite_under_python_optimized_mode(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-v",
                "revenue.human_reply_workshare_kit.test_core",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_reload_predecessor_in_fresh_normal_and_optimized_processes(self):
        for optimized in (False, True):
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.extend(["-c", _RELOAD_PREDECESSOR])
            completed = subprocess.run(
                command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            self.assertEqual(
                completed.returncode,
                0,
                f"optimized={optimized}\n{completed.stdout}",
            )


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None
) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_core))
    suite.addTests(loader.loadTestsFromTestCase(HumanReplyWorkshareAuthorityGuardTests))
    suite.addTests(loader.loadTestsFromTestCase(HumanReplyWorkshareOptimizedBridgeTests))
    return suite


if __name__ == "__main__":
    unittest.main()
