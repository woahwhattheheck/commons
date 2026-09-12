import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
V4 = HERE.parents[3]
sys.path.insert(0, str(V4))
import check_composition_graph as cg  # noqa: E402


class CompositionGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "port_a.py").write_text("# a\n", encoding="utf-8")
        (self.root / "pkg" / "port_b.py").write_text("# b\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def manifest(self, components, *, patterns=None, strict=True):
        return {
            "schema": "titan-v4-composition/v1",
            "mode": "fail_closed",
            "canonical_branch": "main",
            "canonical_root": "revenue/kaggriculture/cloud-execution-lab/candidates/v4",
            "components": components,
            "discovery": {
                "roots": ["pkg"],
                "patterns": patterns or [],
                "strict": strict,
                "ignore": [],
            },
        }

    def comp(self, cid, entry, inp, out, **extra):
        value = {
            "id": cid,
            "state": "compose",
            "package": "pkg",
            "entrypoints": [entry],
            "transforms": [{"surface": "runtime", "input_identity": inp, "output_identity": out}],
            "requires": [],
            "before": [],
            "after": [],
            "conflicts": [],
        }
        value.update(extra)
        return value

    def codes(self, result):
        return {item["code"] for item in result["errors"]}

    def test_valid_chain_is_deterministic(self):
        a = self.comp("a", "pkg/port_a.py", "base", "a-out", before=["b"])
        b = self.comp("b", "pkg/port_b.py", "a-out", "b-out", requires=["a"])
        result = cg.validate_manifest(self.manifest([b, a], patterns=["port_*.py"]), self.root)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["plan"], ["a", "b"])
        self.assertEqual(result["unregistered"], [])

    def test_unordered_overlap_fails(self):
        a = self.comp("a", "pkg/port_a.py", "base", "a-out")
        b = self.comp("b", "pkg/port_b.py", "base", "b-out")
        result = cg.validate_manifest(self.manifest([a, b]), self.root)
        self.assertIn("unordered_surface_overlap", self.codes(result))

    def test_stale_preimage_fails(self):
        a = self.comp("a", "pkg/port_a.py", "base", "a-out", before=["b"])
        b = self.comp("b", "pkg/port_b.py", "WRONG", "b-out")
        result = cg.validate_manifest(self.manifest([a, b]), self.root)
        self.assertIn("stale_preimage", self.codes(result))

    def test_cycle_fails(self):
        a = self.comp("a", "pkg/port_a.py", "base", "a-out", after=["b"])
        b = self.comp("b", "pkg/port_b.py", "a-out", "b-out", after=["a"])
        result = cg.validate_manifest(self.manifest([a, b]), self.root)
        self.assertIn("dependency_cycle", self.codes(result))
        self.assertEqual(result["plan"], [])

    def test_unregistered_entrypoint_fails_closed(self):
        a = self.comp("a", "pkg/port_a.py", "base", "a-out")
        result = cg.validate_manifest(self.manifest([a], patterns=["port_*.py"]), self.root)
        self.assertIn("unregistered_entrypoint", self.codes(result))
        self.assertEqual(result["unregistered"], ["pkg/port_b.py"])

    def test_active_requires_blocked_fails(self):
        blocked = {
            "id": "hold",
            "state": "blocked",
            "reason": "economic gate pending",
            "package": "pkg",
            "entrypoints": [],
            "transforms": [],
            "requires": [],
            "before": [],
            "after": [],
            "conflicts": [],
        }
        a = self.comp("a", "pkg/port_a.py", "base", "a-out", requires=["hold"])
        result = cg.validate_manifest(self.manifest([blocked, a]), self.root)
        self.assertIn("active_requires_noncompose", self.codes(result))

    def test_active_conflict_fails(self):
        a = self.comp("a", "pkg/port_a.py", "base", "a-out", conflicts=["b"])
        b = self.comp("b", "pkg/port_b.py", "a-out", "b-out", after=["a"])
        result = cg.validate_manifest(self.manifest([a, b]), self.root)
        self.assertIn("active_conflict", self.codes(result))

    def test_ignore_requires_reason(self):
        manifest = self.manifest([], patterns=["port_*.py"])
        manifest["discovery"]["ignore"] = ["pkg/port_a.py"]
        result = cg.validate_manifest(manifest, self.root)
        self.assertIn("ignore_without_reason", self.codes(result))

    def test_wrong_canonical_root_fails(self):
        manifest = self.manifest([])
        manifest["canonical_root"] = "revenue/kaggriculture/cloud-execution-lab/candidates/v4-copy"
        result = cg.validate_manifest(manifest, self.root)
        self.assertIn("wrong_canonical_root", self.codes(result))

    def test_symlink_entrypoint_fails_closed(self):
        target = self.root / "outside.py"
        target.write_text("# outside\n", encoding="utf-8")
        link = self.root / "pkg" / "linked.py"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        a = self.comp("a", "pkg/linked.py", "base", "a-out")
        result = cg.validate_manifest(self.manifest([a]), self.root)
        self.assertIn("unsafe_entrypoint_resolution", self.codes(result))


if __name__ == "__main__":
    unittest.main()
