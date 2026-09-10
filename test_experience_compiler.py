import json
import tempfile
import unittest
from pathlib import Path

import host.experience_compiler as compiler


class ExperienceCompilerTests(unittest.TestCase):
    def test_seed_record_is_valid_and_evidence_backed(self):
        records = compiler.load_records()
        self.assertEqual(["ai-village-discovery-4945"], [r["id"] for r in records])
        commit = next(item for item in records[0]["evidence"] if item["kind"] == "commit")
        self.assertRegex(commit["value"], r"^[0-9a-f]{40}$")

    def test_compilation_is_deterministic(self):
        records = compiler.load_records()
        self.assertEqual(compiler.compile_outputs(records), compiler.compile_outputs(records))

    def test_layers_remain_separate(self):
        outputs = compiler.compile_outputs(compiler.load_records())
        catalog = json.loads(outputs[compiler.WIKI_DIR / "catalog.json"])
        self.assertEqual("commons-experience-wiki/v1", catalog["schema"])
        self.assertNotIn("skill_content", catalog)
        self.assertTrue((compiler.ROOT / ".agents/skills/experience-compiler/SKILL.md").exists())

    def test_compiled_pattern_keeps_source_receipt(self):
        outputs = compiler.compile_outputs(compiler.load_records())
        page = outputs[compiler.PATTERN_DIR / "publish-discovery-before-interaction.md"]
        self.assertIn("experience/raw/ai-village-discovery-4945.json", page)
        self.assertIn("Success observations: 1", page)

    def test_invalid_commit_evidence_is_rejected(self):
        record = json.loads(
            (compiler.RAW_DIR / "ai-village-discovery-4945.json").read_text(encoding="utf-8")
        )
        record["id"] = "bad-record"
        record["evidence"][1]["value"] = "not-a-sha"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-record.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(compiler.ExperienceError, "full SHA"):
                compiler.validate_record(record, path)

    def test_compiled_markdown_keeps_live_cash_and_titanmcp_cites(self):
        outputs = compiler.compile_outputs(compiler.load_records())
        index = outputs[compiler.WIKI_DIR / "index.md"]
        pattern = outputs[
            compiler.PATTERN_DIR / "publish-discovery-before-interaction.md"
        ]
        self.assertIn("[$29 Autopsy checkout](../../agent-rescue.html)", index)
        self.assertIn("[titanmcp.html](../../titanmcp.html)", index)
        self.assertIn("Cite Latch Pad KEEP", index)
        self.assertIn("[$29 Autopsy checkout](../../../agent-rescue.html)", pattern)
        self.assertIn("[titanmcp.html](../../../titanmcp.html)", pattern)
        catalog = outputs[compiler.WIKI_DIR / "catalog.json"]
        self.assertNotIn("Live cash", catalog)
        self.assertNotIn("buy.stripe.com", index)
        self.assertNotIn("buy.stripe.com", pattern)

    def test_check_is_current_when_live_cash_keep_is_emitted(self):
        outputs = compiler.compile_outputs(compiler.load_records())
        self.assertEqual([], compiler.check_outputs(outputs))
        index_path = compiler.WIKI_DIR / "index.md"
        pattern_path = compiler.PATTERN_DIR / "publish-discovery-before-interaction.md"
        self.assertEqual(index_path.read_text(encoding="utf-8"), outputs[index_path])
        self.assertEqual(pattern_path.read_text(encoding="utf-8"), outputs[pattern_path])


if __name__ == "__main__":
    unittest.main()
