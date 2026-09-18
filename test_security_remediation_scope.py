"""Root retained-CI bridge for the security-remediation scope battery."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

TEST_FILE = Path(__file__).resolve().parent / "tests" / "test_security_remediation_scope.py"
SPEC = importlib.util.spec_from_file_location("security_remediation_scope_tests", TEST_FILE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load {TEST_FILE}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TestSecurityRemediationScope = MODULE.SecurityRemediationScopeTests

if __name__ == "__main__":
    unittest.main(module=MODULE)
