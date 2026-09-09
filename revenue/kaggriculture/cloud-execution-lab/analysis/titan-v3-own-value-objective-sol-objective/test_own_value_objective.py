# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

import own_value_objective as objective


def _source_path(root: Path, content: bytes = b"fixture selected sell core\n") -> tuple[Path, str]:
    path = root / "selected_sell_core.py"
    path.write_bytes(content)
    return path, objective.git_blob_sha1(path)


def bound_module(root: Path):
    path, blob = _source_path(root)

    class MarketPath:
        def score(self, plan, quantity, rival, alignment, terminal=False):
            own_cash, carry, other_cash, remaining = plan
            return own_cash+carry-other_cash, own_cash,other_cash,remaining

    return SimpleNamespace(MarketPath=MarketPath, __file__=str(path)), blob


def drifted_module(root: Path):
    path, blob = _source_path(root)

    class MarketPath:
        def score(self, plan, quantity, rival, alignment, terminal=False):
            own_cash, carry, other_cash, remaining = plan
            return own_cash+carry, own_cash,other_cash,remaining

    return SimpleNamespace(MarketPath=MarketPath, __file__=str(path)), blob


def wrong_signature_module(root: Path):
    path, blob = _source_path(root)

    class MarketPath:
        def score(self, plan, quantity, rival, alignment):
            own_cash, carry, other_cash, remaining = plan
            return own_cash+carry-other_cash, own_cash,other_cash,remaining

    return SimpleNamespace(MarketPath=MarketPath, __file__=str(path)), blob


class OwnValueTupleTests(unittest.TestCase):
    def test_recovers_realized_plus_carry(self):
        transformed = objective.own_value_tuple((82.0, 112, 30, 7))
        self.assertEqual(transformed, (112.0, 112, 30, 7))

    def test_rival_receipts_do_not_change_own_objective(self):
        a = objective.own_value_tuple((100.0, 100, 0, 0))
        b = objective.own_value_tuple((70.0, 100, 30, 0))
        self.assertEqual(a[0], b[0])

    def test_only_first_tuple_field_changes(self):
        original = (82.0, 112, 30, 7)
        transformed = objective.own_value_tuple(original)
        self.assertEqual(transformed[1:], original[1:])

    def test_rejects_malformed_tuple(self):
        with self.assertRaisesRegex(objective.ObjectiveScoreError, "four-tuple"):
            objective.own_value_tuple([1, 2, 3, 4])
        with self.assertRaisesRegex(objective.ObjectiveScoreError, "four-tuple"):
            objective.own_value_tuple((1, 2, 3))

    def test_rejects_nonfinite_and_boolean_values(self):
        for value in (math.nan, math.inf, True):
            with self.subTest(value=value):
                with self.assertRaises(objective.ObjectiveScoreError):
                    objective.own_value_tuple((value, 1, 0, 0))

    def test_rejects_negative_implied_carry(self):
        with self.assertRaisesRegex(objective.ObjectiveScoreError, "below realized"):
            objective.own_value_tuple((50.0, 100, 20, 0))


class InstallTests(unittest.TestCase):
    def test_install_is_one_factor_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = bound_module(root)
            before = module.MarketPath.score
            receipt = objective.install(
                module=module, expected_root=root, expected_blob=blob
            )
            after = module.MarketPath.score
            self.assertIsNot(before, after)
            self.assertEqual(
                after(module.MarketPath(), (112, 0, 30, 7), 0, 0, "paired"),
                (112.0, 112, 30, 7),
            )
            self.assertEqual(
                objective.install(
                    module=module, expected_root=root, expected_blob=blob
                ),
                receipt,
            )
            self.assertIs(module.MarketPath.score, after)
            self.assertEqual(receipt["source_git_blob"], blob)
            self.assertEqual(receipt["expected_git_blob"], blob)
            self.assertFalse(receipt["canonical_files_modified"])

    def test_install_rejects_source_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = drifted_module(root)
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "source drift"):
                objective.install(module=module, expected_root=root, expected_blob=blob)

    def test_install_rejects_signature_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = wrong_signature_module(root)
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "signature drift"):
                objective.install(module=module, expected_root=root, expected_blob=blob)

    def test_install_rejects_wrong_source_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = bound_module(root)
            wrong = root / "not_the_core.py"
            wrong.write_bytes((root / "selected_sell_core.py").read_bytes())
            module.__file__ = str(wrong)
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "selected_sell_core.py"):
                objective.install(module=module, expected_blob=blob)

    def test_install_rejects_wrong_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = bound_module(root)
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "path mismatch"):
                objective.install(
                    module=module,
                    expected_root=root / "wrong",
                    expected_blob=blob,
                )

    def test_install_rejects_wrong_git_blob(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = bound_module(root)
            wrong = "0" * 40 if blob != "0" * 40 else "1" * 40
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "Git blob drift"):
                objective.install(
                    module=module, expected_root=root, expected_blob=wrong
                )

    def test_idempotent_install_revalidates_source_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = bound_module(root)
            objective.install(module=module, expected_root=root, expected_blob=blob)
            (root / "selected_sell_core.py").write_bytes(b"drift after install\n")
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "Git blob drift"):
                objective.install(module=module, expected_root=root, expected_blob=blob)

    def test_conflicting_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module, blob = bound_module(root)
            setattr(
                module.MarketPath.score,
                "__titan_own_value_objective_version__",
                "other",
            )
            with self.assertRaisesRegex(objective.ObjectiveBindingError, "conflicting"):
                objective.install(module=module, expected_root=root, expected_blob=blob)


class CandidateBindingTests(unittest.TestCase):
    def test_candidate_binds_exact_lab_core_and_main_in_fresh_process(self):
        case = Path(__file__).resolve().parent
        script = r'''
import importlib.util
import json
from pathlib import Path
import sys
candidate = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("_candidate_binding_contract", candidate)
if spec is None or spec.loader is None:
    raise SystemExit("candidate spec unavailable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps(module.INSTALL_RECEIPT, sort_keys=True))
'''
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "-c", script, str(case / "candidate.py")],
            cwd=case,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        lab = case.parent.parent.resolve()
        self.assertEqual(Path(receipt["lab_root"]), lab)
        self.assertEqual(
            Path(receipt["source_path"]), lab / "selected_sell_core.py"
        )
        self.assertEqual(
            receipt["source_git_blob"],
            objective.EXPECTED_SELECTED_SELL_CORE_BLOB,
        )
        self.assertEqual(Path(receipt["canonical_main_path"]), lab / "main.py")
        self.assertEqual(
            receipt["canonical_main_git_blob"],
            "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
        )


if __name__ == "__main__":
    unittest.main()
