from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

_ROOT = Path(__file__).resolve().parent
_NESTED = _ROOT / "tests" / "test_invest_appalachia_attachment_recovery.py"
_spec = importlib.util.spec_from_file_location("invest_appalachia_attachment_recovery_nested", _NESTED)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load retained nested suite: {_NESTED}")
_nested = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nested)

# Re-export the exact nested TestCase so the retained root battery executes the
# full ordinary suite from this source-linked root bridge.
AttachmentRecoveryTests = _nested.AttachmentRecoveryTests


class AttachmentRecoveryOptimizedBridgeTests(unittest.TestCase):
    def test_nested_suite_passes_under_python_optimized(self):
        env = os.environ.copy()
        inherited = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(_ROOT) if not inherited else str(_ROOT) + os.pathsep + inherited
        completed = subprocess.run(
            [sys.executable, "-O", str(_NESTED)],
            cwd=_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Ran 14 tests", completed.stdout)
        self.assertRegex(completed.stdout, r"(?m)^OK$")


if __name__ == "__main__":
    unittest.main()
