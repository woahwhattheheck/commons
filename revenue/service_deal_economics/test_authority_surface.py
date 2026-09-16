import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.current_readiness_guard.guard import analyze_source

from . import authority as a
from .test_authority import HostAuthority, NOW, packet


class CurrentSurfaceTests(unittest.TestCase):
    def test_current_helper_has_no_registry_injection_parameter(self):
        with tempfile.TemporaryDirectory() as td:
            host = HostAuthority(Path(td)); p = packet(); reg = host.sign(p)
            with patch.object(a, "_host_paths", return_value=host.paths):
                with self.assertRaises(TypeError):
                    a._compile_current_at(p, NOW, registry=reg)

    def test_public_current_surfaces_own_process_clock_and_authority_parameter(self):
        compile_params = inspect.signature(a.compile_current).parameters
        verify_params = inspect.signature(a.verify_current_authority).parameters
        self.assertEqual(list(compile_params), ["packet"])
        self.assertIn("authority", verify_params)
        self.assertNotIn("as_of", verify_params)
        self.assertNotIn("trusted_as_of", verify_params)
        self.assertNotIn("now", verify_params)

    def test_current_readiness_guard_accepts_authority_modules(self):
        root = Path(__file__).resolve().parent
        for name in ("authority.py", "authority_history.py"):
            path = root / name
            findings = analyze_source(
                path.read_text(encoding="utf-8"),
                path=f"revenue/service_deal_economics/{name}",
            )
            self.assertEqual([finding.rule for finding in findings], [], name)


if __name__ == "__main__":
    unittest.main()
