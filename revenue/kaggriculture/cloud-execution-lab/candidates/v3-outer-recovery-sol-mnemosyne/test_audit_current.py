# SPDX-License-Identifier: Apache-2.0
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("_mnemosyne_audit_tested", HERE / "audit_current.py")
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDIT)

MAIN = '''
_INSTANCE = None
def _new_instance(root, feature_data):
    return object()
def agent(observation, configuration=None):
    global _INSTANCE
    instance = _INSTANCE
    if remaining <= 0:
        if instance is not None:
            instance._remember_seller_fallback(obs)
        return fallback
    try:
        output = instance.act(observation, configuration)
    except deadline.DeadlineExceeded as error:
        _INSTANCE = None
        return fallback
    return output
'''
RUNTIME = '''
class TitanAgent:
    def __init__(self):
        self._completed_route = None
        self._completed_seller_state = None
        self._seller_fallback_observations = []
    def _initialize(self):
        if self._completed_route is not None:
            self.controller.cur = self._completed_route
        self._restore_seller_state()
    def _restore_seller_state(self):
        pass
    def _remember_seller_fallback(self, obs):
        pass
'''
ARLENE = '''
DECISIONS = ((226, "a", 1, "A"), (360, "b", 2, "B"), (433, "c", 3, "C"))
class Agent:
    def _switch_ok(self, target, turn):
        return True
    def act(self, obs):
        step = obs["step"]
        for turn, feat, threshold, target in DECISIONS:
            if turn == step and self._switch_ok(target, turn):
                self.cur = target
        return self.cur
'''


def make_tree(root: Path, *, main=MAIN, runtime=RUNTIME, arlene=ARLENE):
    (root / "reference/next-panel/vendor").mkdir(parents=True)
    (root / "main.py").write_text(main, encoding="utf-8")
    (root / "titan_runtime.py").write_text(runtime, encoding="utf-8")
    (root / "reference/next-panel/vendor/arlene.py").write_text(arlene, encoding="utf-8")


class SourceAuditTests(unittest.TestCase):
    def test_valid_current_shape_passes_with_deterministic_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root)
            left = AUDIT.audit(root)
            right = AUDIT.audit(root)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "PASS")
            self.assertEqual(left["arlene"]["decision_turns"], [226, 360, 433])
            self.assertEqual(left["runtime"]["safe_fields"], sorted(AUDIT.SAFE_FIELDS))
            json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def test_outer_handler_record_drift_fails(self):
        broken = MAIN.replace(
            "    except deadline.DeadlineExceeded as error:\n        _INSTANCE = None",
            "    except deadline.DeadlineExceeded as error:\n        instance._remember_seller_fallback(obs)\n        _INSTANCE = None",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, main=broken)
            with self.assertRaisesRegex(AUDIT.AuditError, "outer deadline handler now records"):
                AUDIT.audit(root)

    def test_missing_live_prelude_record_fails(self):
        broken = MAIN.replace("            instance._remember_seller_fallback(obs)\n", "            pass\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, main=broken)
            with self.assertRaisesRegex(AUDIT.AuditError, "live-prelude fallback recorder"):
                AUDIT.audit(root)

    def test_missing_runtime_safe_field_fails(self):
        broken = RUNTIME.replace("        self._completed_seller_state = None\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, runtime=broken)
            with self.assertRaisesRegex(AUDIT.AuditError, "safe fields"):
                AUDIT.audit(root)

    def test_route_restore_drift_fails(self):
        broken = RUNTIME.replace(
            "            self.controller.cur = self._completed_route",
            "            self.controller.cur = 'MAIN'",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, runtime=broken)
            with self.assertRaisesRegex(AUDIT.AuditError, "no longer restores"):
                AUDIT.audit(root)

    def test_non_exact_route_switch_fails(self):
        broken = ARLENE.replace("turn == step", "turn <= step")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, arlene=broken)
            with self.assertRaisesRegex(AUDIT.AuditError, "exact-turn"):
                AUDIT.audit(root)

    def test_decision_turn_drift_fails(self):
        broken = ARLENE.replace("(433,", "(434,")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, arlene=broken)
            with self.assertRaisesRegex(AUDIT.AuditError, "unexpected route decision"):
                AUDIT.audit(root)

    def test_symlink_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            make_tree(root)
            target = root / "main.py"
            target.unlink()
            outside_main = Path(outside) / "main.py"
            outside_main.write_text(MAIN, encoding="utf-8")
            target.symlink_to(outside_main)
            with self.assertRaisesRegex(AUDIT.AuditError, "symlink"):
                AUDIT.audit(root)

    def test_cli_fail_is_machine_readable_and_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root, arlene=ARLENE.replace("turn == step", "turn <= step"))
            output = root / "receipt.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = AUDIT.main(["--root", str(root), "--output", str(output)])
            self.assertEqual(code, 1)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("exact-turn", report["error"])


if __name__ == "__main__":
    unittest.main()
