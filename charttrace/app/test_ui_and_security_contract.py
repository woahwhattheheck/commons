import ast
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from charttrace.app import ChartTraceController
from charttrace.app.ipc import LocalIpcServer, local_ipc_address, local_ipc_family
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
    def test_ipc_has_no_public_tcp_code_path(self):
        source = Path(__file__).with_name("ipc.py").read_text(encoding="utf-8")
        self.assertNotIn("AF_INET", source)
        self.assertNotIn("0.0.0.0", source)
        self.assertNotIn("AF_INET6", source)
        self.assertIn("AF_UNIX", source)
        self.assertIn(local_ipc_family(), {"AF_PIPE", "AF_UNIX"})
        address = local_ipc_address("unit-test")
        if os.name == "nt":
            self.assertTrue(address.startswith("\\\\.\\pipe\\charttrace-"))
        else:
            self.assertTrue(address.endswith("charttrace-unit-test.sock"))

    @unittest.skipIf(os.name == "nt", "Named-pipe creation is covered on Windows.")
    def test_local_server_binds_only_filesystem_domain_socket(self):
        server = LocalIpcServer("listener-proof")
        try:
            server.start()
            self.assertTrue(server.is_running)
            self.assertEqual("AF_UNIX", server.family)
            self.assertTrue(Path(server.address).exists())
        finally:
            server.close()
        self.assertFalse(Path(server.address).exists())

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
        self.assertEqual("local_ipc_only", manifest["transport"])
        self.assertFalse(manifest["telemetry"])

    def test_exclusive_sources_have_no_network_or_browser_path(self):
        roots = [
            Path(__file__).resolve().parents[1] / "app",
            Path(__file__).resolve().parents[1] / "ui",
            Path(__file__).resolve().parents[1] / "legal",
            Path(__file__).resolve().parents[1] / "launcher.py",
        ]
        forbidden = (
            "webbrowser",
            "http.server",
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "AF_INET",
        )
        scanned = 0
        for root in roots:
            paths = [root] if root.is_file() else sorted(root.glob("*.py"))
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
        self.assertGreaterEqual(scanned, 15)

    def test_launcher_headless_startup_needs_no_display(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--headless", "--data-dir", directory])
        self.assertEqual(0, exit_code)
        startup = json.loads(output.getvalue())
        self.assertEqual("UNSIGNED_SYNTHETIC", startup["build_label"])
        self.assertEqual("unlock", startup["startup_screen"]["screen_id"])
        self.assertTrue(startup["startup_screen"]["has_legal_button"])


if __name__ == "__main__":
    unittest.main()
