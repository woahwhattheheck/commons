from __future__ import annotations

import copy
import importlib
from pathlib import Path
import subprocess
import sys
import unittest

from revenue.human_reply_workshare_kit import core
from revenue.human_reply_workshare_kit.test_core import base_record


ROOT = Path(__file__).resolve().parent

_RELOAD_MARKDOWN_PREDECESSOR = r'''
import importlib
from revenue.human_reply_workshare_kit import core
from revenue.human_reply_workshare_kit.test_core import base_record

for _ in range(3):
    if importlib.reload(core) is not core:
        raise SystemExit("core reload changed module identity")

cases = []
row = base_record()
row["counterparty_label"] = "Buyer [](https://example.invalid) accepted this scope"
cases.append(row)
row = base_record()
row["opportunity_label"] = "Payment ![](https://example.invalid/pixel) received for the pilot"
cases.append(row)
row = base_record()
row["scope"]["one_line"] = "Invoice [noise][destination] sent yesterday"
cases.append(row)
row = base_record()
row["scope"]["input_bounds"] = ["one entity", "Customer [](https://example.invalid) relationship is confirmed"]
cases.append(row)

for row in cases:
    try:
        core.compile_offer(row)
    except core.WorkshareError as exc:
        if "Markdown link/image/reference" not in str(exc):
            raise SystemExit("wrong rejection after reload: " + str(exc))
    else:
        raise SystemExit("reload admitted hidden Markdown destination")
'''


class HumanReplyWorkshareMarkdownDestinationTests(unittest.TestCase):
    def test_destination_syntax_fails_closed_across_every_rendered_field(self):
        mutations = (
            lambda row: row.__setitem__(
                "counterparty_label",
                "Buyer [](https://example.invalid) accepted this scope",
            ),
            lambda row: row.__setitem__(
                "opportunity_label",
                "Payment ![](https://example.invalid/pixel) received for the pilot",
            ),
            lambda row: row["scope"].__setitem__(
                "one_line",
                "Invoice [noise][destination] sent yesterday",
            ),
            lambda row: row["scope"].__setitem__(
                "input_bounds",
                [
                    "one entity",
                    "Customer [](https://example.invalid) relationship is confirmed",
                ],
            ),
        )
        for mutate in mutations:
            row = base_record()
            mutate(row)
            with self.subTest(row=row):
                with self.assertRaisesRegex(
                    core.WorkshareError, "Markdown link/image/reference"
                ):
                    core.compile_offer(row)

    def test_inline_full_collapsed_image_and_reference_definition_forms_reject(self):
        values = (
            "Buyer [](https://example.invalid) accepted this scope",
            "Payment [noise][destination] received for pilot",
            "Invoice [noise][] sent yesterday",
            "Customer ![hidden](https://example.invalid/pixel) relationship is confirmed",
            "[destination]: https://example.invalid Buyer accepted this scope",
        )
        for value in values:
            row = base_record()
            row["scope"]["one_line"] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    core.WorkshareError, "Markdown link/image/reference"
                ):
                    core.compile_offer(row)

    def test_plain_bracket_text_without_destination_remains_admissible(self):
        row = base_record("DATA_MIGRATION_ACCEPTANCE")
        row["scope"]["one_line"] = (
            "Legacy reconciliation and acceptance evidence [owner note] for one frozen batch."
        )
        compiled = core.compile_offer(row)
        self.assertIn("acceptance evidence [owner note]", compiled.markdown)

    def test_public_renderer_and_receipt_reenter_destination_guard(self):
        compiled = core.compile_offer(base_record())
        forged_normalized = copy.deepcopy(dict(compiled.normalized))
        forged_normalized["scope"] = copy.deepcopy(dict(compiled.normalized["scope"]))
        forged_normalized["scope"]["one_line"] = (
            "Buyer [](https://example.invalid) accepted this workshare"
        )
        with self.assertRaisesRegex(
            core.WorkshareError, "Markdown link/image/reference"
        ):
            core.render_offer_markdown(forged_normalized)

        forged = core.CompiledOffer(
            normalized=forged_normalized,
            markdown=compiled.markdown,
            receipt_sha256=compiled.receipt_sha256,
        )
        with self.assertRaisesRegex(
            core.WorkshareError, "Markdown link/image/reference"
        ):
            core.render_receipt_json(forged)

    def test_reload_seal_retains_destination_guard_normal_and_optimized(self):
        for optimized in (False, True):
            command = [sys.executable]
            if optimized:
                command.append("-O")
            command.extend(["-c", _RELOAD_MARKDOWN_PREDECESSOR])
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
