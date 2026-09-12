#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_control_plane as guard


def _dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _base_composition() -> dict[str, object]:
    return {
        "schema": "titan-v4-composition/v1",
        "mode": "fail_closed",
        "canonical_branch": "main",
        "canonical_root": "revenue/kaggriculture/cloud-execution-lab/candidates/v4",
        "components": [
            {
                "id": "alpha",
                "state": "compose",
                "package": "repairs/alpha",
                "entrypoints": ["repairs/alpha/apply.py"],
                "receipt": "repairs/alpha/RECEIPT.json",
                "transforms": [
                    {
                        "surface": "x.py",
                        "input_identity": "git-blob:" + "a" * 40,
                        "output_identity": "git-blob:" + "b" * 40,
                    }
                ],
                "requires": [],
                "before": [],
                "after": [],
                "conflicts": [],
            }
        ],
        "discovery": {"roots": ["repairs"], "patterns": ["apply.py"], "strict": True, "ignore": []},
    }


def _base_integration() -> dict[str, object]:
    return {
        "schema": "titan-v4-integration-ledger/v1",
        "canonical_branch": "main",
        "workspace": "revenue/kaggriculture/cloud-execution-lab/candidates/v4",
        "landed": [],
        "recovered_not_yet_composed": [],
        "custody_blocked": [],
        "negative_or_parked": [],
    }


def _make_root(root: Path) -> None:
    _dump(
        root / "CANONICAL.json",
        {
            "canonical_branch": "main",
            "workspace": "revenue/kaggriculture/cloud-execution-lab/candidates/v4",
        },
    )
    _dump(root / "INTEGRATION.json", _base_integration())
    _dump(root / "COMPOSITION.json", _base_composition())
    (root / "repairs" / "alpha").mkdir(parents=True)
    (root / "repairs" / "alpha" / "apply.py").write_text("pass\n", encoding="utf-8")
    _dump(root / "repairs" / "alpha" / "RECEIPT.json", {"ok": True})


def _write_graph_stub(root: Path) -> None:
    (root / "check_composition_graph.py").write_text(
        "def validate_manifest(manifest, root):\n    return {'errors': []}\n",
        encoding="utf-8",
    )


class ControlPlaneHardeningTests(unittest.TestCase):
    def test_valid_minimal_control_plane_passes_hardening(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            result = guard.validate_control_plane(root, delegate=False)
        self.assertTrue(result["ok"], result)

    def test_duplicate_json_member_is_rejected_at_any_depth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            (root / "COMPOSITION.json").write_text(
                '{"schema":"titan-v4-composition/v1","components":[{"id":"a","id":"b"}]}\n',
                encoding="utf-8",
            )
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicate object key 'id'" in e for e in result["errors"]), result)

    def test_nonfinite_json_constant_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            (root / "CANONICAL.json").write_text('{"x":NaN}\n', encoding="utf-8")
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("non-finite JSON constant 'NaN'" in e for e in result["errors"]), result)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_root_control_files_cannot_be_symlinked_outside_root(self):
        for name in guard.EXPECTED_FILES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                base = Path(td)
                root = base / "root"
                _make_root(root)
                external = base / "external"
                external.mkdir()
                source = root / name
                target = external / name
                source.replace(target)
                os.symlink(target, source)
                result = guard.validate_control_plane(root, delegate=False)
            self.assertFalse(result["ok"], result)
            self.assertTrue(
                any(f"{name} must not be a symlink" in e for e in result["errors"]),
                result,
            )

    def test_non_object_manifest_fails_without_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            (root / "COMPOSITION.json").write_text("[]\n", encoding="utf-8")
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertIn("COMPOSITION.json must contain one JSON object", result["errors"])

    def test_duplicate_relation_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            composition = _base_composition()
            composition["components"][0]["requires"] = ["beta", "beta"]  # type: ignore[index]
            _dump(root / "COMPOSITION.json", composition)
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertIn("component alpha requires: duplicate relation target 'beta'", result["errors"])

    def test_all_input_output_identity_fields_use_exact_git_blob_grammar(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            composition = _base_composition()
            composition["components"][0]["standalone_receipt_edges"] = [  # type: ignore[index]
                {
                    "surface": "y.py",
                    "input_identity": "git-blob:" + "A" * 40,
                    "output_identity": "sha256:" + "b" * 64,
                }
            ]
            _dump(root / "COMPOSITION.json", composition)
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertEqual(2, sum("COMPOSITION identity" in e for e in result["errors"]), result)

    def test_declared_receipt_must_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            (root / "repairs" / "alpha" / "RECEIPT.json").unlink()
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("declared file is missing" in e for e in result["errors"]), result)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_symlink_ancestor_inside_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            real = root / "real"
            (real / "alpha").mkdir(parents=True)
            (real / "alpha" / "apply.py").write_text("pass\n", encoding="utf-8")
            _dump(real / "alpha" / "RECEIPT.json", {"ok": True})
            (root / "repairs" / "alpha" / "apply.py").unlink()
            (root / "repairs" / "alpha" / "RECEIPT.json").unlink()
            (root / "repairs" / "alpha").rmdir()
            os.symlink(real, root / "repairs" / "link")
            composition = _base_composition()
            component = composition["components"][0]  # type: ignore[index]
            component["package"] = "repairs/link/alpha"
            component["entrypoints"] = ["repairs/link/alpha/apply.py"]
            component["receipt"] = "repairs/link/alpha/RECEIPT.json"
            _dump(root / "COMPOSITION.json", composition)
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("symlink ancestry is forbidden" in e for e in result["errors"]), result)

    def test_live_blocker_manifest_is_strict_loaded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            integration = _base_integration()
            integration["custody_blocked"] = [
                {
                    "lane": "raw",
                    "custody_path": "repairs/raw",
                    "status": "awaiting_raw_payload",
                }
            ]
            _dump(root / "INTEGRATION.json", integration)
            (root / "repairs" / "raw").mkdir()
            (root / "repairs" / "raw" / "MANIFEST.json").write_text(
                '{"lane":"raw","lane":"rewritten","status":"awaiting_raw_payload"}\n',
                encoding="utf-8",
            )
            result = guard.validate_control_plane(root, delegate=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("manifest:" in e and "duplicate object key 'lane'" in e for e in result["errors"]), result)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_blocker_manifest_parent_swap_after_trust_check_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "root"
            _make_root(root)
            integration = _base_integration()
            integration["custody_blocked"] = [
                {
                    "lane": "raw",
                    "custody_path": "repairs/raw",
                    "status": "awaiting_raw_payload",
                }
            ]
            _dump(root / "INTEGRATION.json", integration)
            raw = root / "repairs" / "raw"
            raw.mkdir()
            _dump(raw / "MANIFEST.json", {"lane": "raw", "status": "awaiting_raw_payload"})
            external = base / "external"
            external.mkdir()
            _dump(external / "MANIFEST.json", {"lane": "external", "status": "awaiting_raw_payload"})

            original_check = guard._check_trust_path
            swapped = False

            def swap_after_check(root_arg, rel, label, errors, *, require_file=False):
                nonlocal swapped
                original_check(
                    root_arg,
                    rel,
                    label,
                    errors,
                    require_file=require_file,
                )
                if label == "custody raw manifest" and not errors and not swapped:
                    raw.rename(root / "repairs" / "raw-before-swap")
                    os.symlink(external, raw, target_is_directory=True)
                    swapped = True

            with mock.patch.object(guard, "_check_trust_path", side_effect=swap_after_check):
                result = guard.validate_control_plane(root, delegate=False)

        self.assertTrue(swapped)
        self.assertFalse(result["ok"], result)
        self.assertTrue(any("custody raw manifest:" in e for e in result["errors"]), result)

    def test_delegate_failures_are_data_not_tracebacks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            (root / "check_integration_ledger.py").write_text(
                "def validate(root):\n    raise RuntimeError('boom')\n",
                encoding="utf-8",
            )
            _write_graph_stub(root)
            result = guard.validate_control_plane(root, delegate=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("integration delegate failure: RuntimeError: boom" in e for e in result["errors"]), result)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_symlink_delegate_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            real = root / "ledger-real.py"
            real.write_text("def validate(root):\n    return []\n", encoding="utf-8")
            os.symlink(real, root / "check_integration_ledger.py")
            _write_graph_stub(root)
            result = guard.validate_control_plane(root, delegate=True)
        self.assertFalse(result["ok"])
        self.assertTrue(any("must not be a symlink" in e for e in result["errors"]), result)

    def test_integration_delegate_reads_preflight_snapshot_after_live_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            (root / "check_integration_ledger.py").write_text(
                "from pathlib import Path\n"
                "import json\n"
                "def validate(root):\n"
                "    live = Path(__file__).resolve().parent / 'INTEGRATION.json'\n"
                "    poisoned = json.loads(live.read_text(encoding='utf-8'))\n"
                "    poisoned['canonical_branch'] = 'poisoned-after-preflight'\n"
                "    live.write_text(json.dumps(poisoned) + '\\n', encoding='utf-8')\n"
                "    snap = json.loads((Path(root) / 'INTEGRATION.json').read_text(encoding='utf-8'))\n"
                "    return [] if snap.get('canonical_branch') == 'main' else ['snapshot poisoned']\n",
                encoding="utf-8",
            )
            _write_graph_stub(root)
            result = guard.validate_control_plane(root, delegate=True)
            live = json.loads((root / "INTEGRATION.json").read_text(encoding="utf-8"))
        self.assertTrue(result["ok"], result)
        self.assertEqual("poisoned-after-preflight", live["canonical_branch"])

    def test_blocker_manifest_delegate_reads_preflight_snapshot_after_live_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            integration = _base_integration()
            integration["custody_blocked"] = [
                {
                    "lane": "raw",
                    "custody_path": "repairs/raw",
                    "status": "awaiting_raw_payload",
                }
            ]
            _dump(root / "INTEGRATION.json", integration)
            (root / "repairs" / "raw").mkdir()
            _dump(
                root / "repairs" / "raw" / "MANIFEST.json",
                {
                    "lane": "raw",
                    "status": "awaiting_raw_payload",
                    "required_next_step": "provide exact raw payload",
                },
            )
            (root / "check_integration_ledger.py").write_text(
                "from pathlib import Path\n"
                "import json\n"
                "def validate(root):\n"
                "    live = Path(__file__).resolve().parent / 'repairs/raw/MANIFEST.json'\n"
                "    poisoned = json.loads(live.read_text(encoding='utf-8'))\n"
                "    poisoned['lane'] = 'poisoned-after-preflight'\n"
                "    live.write_text(json.dumps(poisoned) + '\\n', encoding='utf-8')\n"
                "    snap = json.loads((Path(root) / 'repairs/raw/MANIFEST.json').read_text(encoding='utf-8'))\n"
                "    return [] if snap.get('lane') == 'raw' else ['manifest snapshot poisoned']\n",
                encoding="utf-8",
            )
            _write_graph_stub(root)
            result = guard.validate_control_plane(root, delegate=True)
            live = json.loads((root / "repairs" / "raw" / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertTrue(result["ok"], result)
        self.assertEqual("poisoned-after-preflight", live["lane"])

    def test_error_order_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_root(root)
            composition = _base_composition()
            component = composition["components"][0]  # type: ignore[index]
            component["before"] = ["z", "z"]
            component["after"] = ["a", "a"]
            _dump(root / "COMPOSITION.json", composition)
            first = guard.validate_control_plane(root, delegate=False)
            second = guard.validate_control_plane(root, delegate=False)
        self.assertEqual(first, second)
        self.assertEqual(first["errors"], sorted(first["errors"]))


if __name__ == "__main__":
    unittest.main()
