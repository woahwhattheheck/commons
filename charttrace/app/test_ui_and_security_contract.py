import ast
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from charttrace.app import ChartTraceController
from charttrace.app.ipc import (
    IpcDisabledError,
    LocalIpcServer,
    PRODUCT_IPC_ENABLED,
    local_ipc_address,
    local_ipc_family,
    local_ipc_transport,
)
from charttrace.launcher import main
from charttrace.ui import LEGAL_ACTION_ID, SCREEN_CATALOG, ChartTraceWindow, ScreenId


class ScreenContractTests(unittest.TestCase):
    def setUp(self):
        self.window = ChartTraceWindow(
            controller=ChartTraceController(persist=False),
            headless=True,
        )

    def test_headless_mode_never_creates_tk_root(self):
        self.assertTrue(self.window.headless)
        self.assertIsNone(self.window.root)

    def test_every_screen_has_persistent_legal_button(self):
        self.assertGreaterEqual(len(SCREEN_CATALOG), 13)
        for screen_id in SCREEN_CATALOG:
            with self.subTest(screen=screen_id.value):
                snapshot = self.window.screen_snapshot(screen_id)
                self.assertTrue(snapshot["has_legal_button"])
                self.assertIn(LEGAL_ACTION_ID, snapshot["persistent_actions"])
                self.assertIn(
                    "DEADLINE_COUNSEL_REVIEW_REQUIRED",
                    snapshot["deadline_banner"],
                )

    def test_required_native_screens_are_present(self):
        self.assertEqual(
            {
                "unlock",
                "case_library",
                "new_case_preflight",
                "secure_ingest",
                "peer_run",
                "evidence_studio",
                "hypothesis_lab",
                "review_console",
                "release_builder",
                "audit_receipts",
                "legal_data_terms",
                "counsel_review_import",
                "commercial_console",
            },
            {screen_id.value for screen_id in SCREEN_CATALOG},
        )

    def test_legal_screen_is_reachable_while_locked_and_unchecked(self):
        self.window.navigate(ScreenId.LEGAL_DATA_TERMS)
        snapshot = self.window.screen_snapshot(ScreenId.LEGAL_DATA_TERMS)
        self.assertTrue(snapshot["locked"])
        self.assertEqual("NOT_ACCEPTED", snapshot["legal_state"])
        self.assertEqual(7, len(snapshot["acknowledgements"]))
        self.assertTrue(
            all(value is False for value in snapshot["acknowledgements"].values())
        )
        with self.assertRaises(PermissionError):
            self.window.navigate(ScreenId.CASE_LIBRARY)


class LocalSecurityContractTests(unittest.TestCase):
    def test_unused_ipc_is_disabled_and_has_no_public_tcp_code_path(self):
        source = Path(__file__).with_name("ipc.py").read_text(encoding="utf-8")
        self.assertNotIn("AF_INET", source)
        self.assertNotIn("0.0.0.0", source)
        self.assertNotIn("AF_INET6", source)
        self.assertNotIn("import socket", source)
        self.assertFalse(PRODUCT_IPC_ENABLED)
        self.assertEqual("DISABLED_NOT_PRODUCT", local_ipc_family())
        self.assertEqual("DISABLED_NOT_PRODUCT", local_ipc_transport())
        with self.assertRaises(IpcDisabledError):
            local_ipc_address("unit-test")

    def test_frozen_product_excludes_retired_ipc_module(self):
        with self.assertRaises(IpcDisabledError):
            LocalIpcServer("listener-proof")
        spec = (
            Path(__file__).parents[1] / "packaging" / "ChartTrace.spec"
        ).read_text(encoding="utf-8")
        self.assertIn('"charttrace.app.ipc"', spec)

    def test_commercial_console_has_no_domain_service_imports(self):
        commercial_path = Path(__file__).with_name("commercial.py")
        tree = ast.parse(commercial_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse(
            any(
                name.startswith("charttrace") or name.startswith(".")
                for name in imported
            )
        )

    def test_packaging_manifest_is_unsigned_local_only(self):
        manifest_path = (
            Path(__file__).parents[1] / "packaging" / "build_manifest.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual("UNSIGNED_SYNTHETIC", manifest["artifact_label"])
        self.assertEqual("unsigned", manifest["signing_state"])
        self.assertEqual("none", manifest["network_listener"])
        self.assertEqual("none", manifest["transport"])
        self.assertFalse(manifest["ipc_enabled"])
        self.assertEqual("6.22.2", manifest["pyinstaller_version"])
        self.assertFalse(manifest.get("synthetic_released", False))
        self.assertFalse(manifest["telemetry"])
        ui_source = (
            Path(__file__).parents[1] / "ui" / "tk_app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("NON-PRODUCTION VALIDATION BUILD", ui_source)

    def test_exclusive_sources_have_no_network_or_browser_path(self):
        roots = [
            Path(__file__).resolve().parents[1] / "app",
            Path(__file__).resolve().parents[1] / "ui",
            Path(__file__).resolve().parents[1] / "legal",
            Path(__file__).resolve().parents[1] / "packaging",
            Path(__file__).resolve().parents[1] / "launcher.py",
        ]
        forbidden = (
            "webbrowser",
            "http.server",
            "http.client",
            "urllib.request",
            "import requests",
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "AF_INET",
            "import socket",
            "multiprocessing",
        )
        scanned = 0
        for root in roots:
            if root.is_file():
                paths = [root]
            else:
                paths = sorted(root.glob("*.py"))
            for path in paths:
                if path.name.startswith("test_"):
                    continue
                scanned += 1
                text = path.read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(
                        token,
                        text,
                        f"{path} must not contain {token}",
                    )
        self.assertGreaterEqual(scanned, 18)

    def test_launcher_headless_startup_needs_no_display(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--headless", "--data-dir", directory])
        self.assertEqual(0, exit_code)
        startup = json.loads(output.getvalue())
        self.assertEqual("UNSIGNED_SYNTHETIC", startup["build_label"])
        self.assertEqual("none", startup["transport"])
        self.assertFalse(startup["ipc_enabled"])
        self.assertFalse(startup["frozen"])
        self.assertEqual("unlock", startup["startup_screen"]["screen_id"])
        self.assertTrue(startup["startup_screen"]["has_legal_button"])


if __name__ == "__main__":
    unittest.main()

