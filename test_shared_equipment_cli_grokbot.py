#!/usr/bin/env python3
"""CLI shared_equipment catalog includes GrokBot lifecycle tools."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class TestCliGrokBotCatalog(unittest.TestCase):
    def test_build_cli_catalog_lists_grokbot_tools(self):
        from integrations.shared_equipment.services import build_cli_catalog

        names = {t["name"] for t in build_cli_catalog().tools()}
        for name in (
            "grokbot_submit",
            "grokbot_inspect",
            "grokbot_follow_up",
            "grokbot_cancel",
            "grokbot_session",
            "grokbot_events",
            "grokbot_pools",
            "slack_read_channel",
            "github_read_file",
        ):
            self.assertIn(name, names)

    def test_module_catalog_subprocess_includes_grokbot(self):
        env = dict(**{k: v for k, v in __import__("os").environ.items()})
        env["PYTHONPATH"] = str(ROOT)
        proc = subprocess.run(
            [sys.executable, "-m", "integrations.shared_equipment.services", "catalog"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        names = {t["name"] for t in payload["tools"]}
        self.assertIn("grokbot_submit", names)
        self.assertIn("github_read_file", names)

    def test_cli_call_grokbot_pools_against_local_control(self):
        from integrations.grokbot_control.gateway import build_server
        from integrations.shared_equipment.services import build_cli_catalog

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "runs.sqlite3"
            server = build_server(
                host="127.0.0.1",
                port=0,
                db_path=db,
                mode="echo",
                min_free_mb=0,
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for _ in range(50):
                    try:
                        cat = build_cli_catalog(
                            grokbot_base_url="http://127.0.0.1:%d" % port
                        )
                        out = cat.call("grokbot_pools", {})
                        if out.get("ok") or "pools" in out:
                            break
                    except Exception:
                        time.sleep(0.05)
                self.assertIn("grokbot", out.get("pools", []))
                submitted = cat.call(
                    "grokbot_submit",
                    {
                        "prompt": "cli equipment",
                        "pool_id": "grokbot",
                        "seat": "SPARK",
                        "async": False,
                    },
                )
                self.assertEqual(submitted.get("status"), "completed")
                self.assertEqual(submitted["attribution"]["harness"], "grokbot")
            finally:
                server.shutdown()
                server.server_close()
                server.controller.store.close()


if __name__ == "__main__":
    unittest.main()