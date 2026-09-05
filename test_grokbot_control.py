#!/usr/bin/env python3
"""Hermetic tests for integrations/grokbot_control (Astra G2)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "integrations" / "grokbot_control"


def _load():
    # Load package modules by path so tests run without install.
    names = [
        "pools",
        "store",
        "runner",
        "gateway",
        "client",
    ]
    package_name = "grokbot_control_under_test"
    if package_name not in sys.modules:
        pkg = type(sys)(package_name)
        pkg.__path__ = [str(PKG)]
        sys.modules[package_name] = pkg
    mods = {}
    for name in names:
        full = "%s.%s" % (package_name, name)
        spec = importlib.util.spec_from_file_location(full, PKG / ("%s.py" % name))
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[full] = mod
        # Ensure relative imports see the package.
        mod.__package__ = package_name
        spec.loader.exec_module(mod)
        mods[name] = mod
        setattr(sys.modules[package_name], name, mod)
    return mods


MODS = _load()
gateway = MODS["gateway"]
client_mod = MODS["client"]
pools = MODS["pools"]


class GatewayFixture:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "runs.sqlite3"
        self.server = gateway.build_server(
            host="127.0.0.1",
            port=0,
            db_path=db,
            mode="echo",
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.port
        self.client = client_mod.GrokBotControlClient(self.base)
        # Wait for listen.
        for _ in range(50):
            try:
                self.client.health()
                break
            except Exception:
                time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.server.controller.store.close()
        self.tmp.cleanup()


class TestGrokBotControl(unittest.TestCase):
    def test_health_and_pools(self):
        with GatewayFixture() as fx:
            health = fx.client.health()
            self.assertTrue(health["ok"])
            self.assertEqual(health["service"], "commons-grokbot-control")
            self.assertEqual(health["harness"], "grokbot")
            self.assertIn("grokbot", health["pools"])
            pools_resp = fx.client.pools()
            self.assertEqual(pools_resp["pools"], ["grokbot"])

    def test_submit_inspect_attribution_round_trip(self):
        with GatewayFixture() as fx:
            submitted = fx.client.submit(
                "ping from peer coordinator",
                pool_id="grokbot",
                seat="SPARK",
                async_mode=True,
            )
            self.assertTrue(submitted["ok"])
            run_id = submitted["run_id"]
            session_id = submitted["session_id"]
            self.assertTrue(run_id)
            self.assertTrue(session_id)

            done = fx.client.inspect(run_id, wait_ms=5000)
            self.assertEqual(done["status"], "completed")
            self.assertIn("ping from peer coordinator", done["result_text"])
            attr = done["attribution"]
            self.assertEqual(attr["pool_id"], "grokbot")
            self.assertEqual(attr["seat"], "SPARK")
            self.assertEqual(attr["harness"], "grokbot")
            self.assertEqual(attr["model"], "Grok")

            session = fx.client.session(session_id)
            self.assertEqual(session["latest"]["run_id"], run_id)

    def test_follow_up_same_session(self):
        with GatewayFixture() as fx:
            first = fx.client.submit("turn-one", seat="SPARK", async_mode=False)
            self.assertEqual(first["status"], "completed")
            second = fx.client.follow_up(
                first["run_id"], "turn-two", async_mode=False
            )
            self.assertEqual(second["status"], "completed")
            self.assertEqual(second["session_id"], first["session_id"])
            self.assertNotEqual(second["run_id"], first["run_id"])
            self.assertIn("turn=2", second["result_text"])
            self.assertEqual(second["attribution"]["pool_id"], "grokbot")

    def test_cancel_run(self):
        with GatewayFixture() as fx:
            # Slow runner via blocking handler replaced: use echo + immediate cancel
            # by submitting async then cancelling before wait completes.
            submitted = fx.client.submit("cancel-me", async_mode=True)
            cancelled = fx.client.cancel(submitted["run_id"])
            self.assertTrue(cancelled["ok"])
            # May already be completed (echo is fast) or cancelled.
            self.assertIn(cancelled["status"], ("cancelled", "completed", "queued", "running"))
            final = fx.client.inspect(submitted["run_id"], wait_ms=2000)
            self.assertIn(final["status"], ("cancelled", "completed"))

    def test_events_cursor(self):
        with GatewayFixture() as fx:
            before = fx.client.events(after=0)
            self.assertTrue(before["ok"])
            cursor = before["next_cursor"]
            fx.client.submit("event-probe", async_mode=False)
            after = fx.client.events(after=cursor, pool_id="grokbot")
            self.assertGreaterEqual(len(after["events"]), 1)
            statuses = {e["status"] for e in after["events"]}
            self.assertTrue(statuses & {"queued", "running", "completed"})

    def test_unknown_pool_rejected(self):
        with GatewayFixture() as fx:
            raw = json.dumps(
                {"pool_id": "invented-kebab", "prompt": "no", "async": False}
            ).encode()
            req = urllib.request.Request(
                fx.base + "/v1/runs",
                data=raw,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req)
                self.fail("expected HTTP error")
            except Exception as exc:
                self.assertIn("400", str(exc) + getattr(exc, "msg", ""))

    def test_second_pool_via_env_only(self):
        import os

        os.environ["GROKBOT_CONTROL_POOLS"] = "grokbot,owner-named-second"
        try:
            self.assertEqual(
                pools.list_pools(), ["grokbot", "owner-named-second"]
            )
        finally:
            os.environ.pop("GROKBOT_CONTROL_POOLS", None)


class TestInProcessRoundTrip(unittest.TestCase):
    def test_inprocess_seat_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "runs.sqlite3"
            server = gateway.build_server(
                host="127.0.0.1",
                port=0,
                db_path=db,
                mode="inprocess",
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                cli = client_mod.GrokBotControlClient(
                    "http://127.0.0.1:%d" % port
                )
                for _ in range(50):
                    try:
                        cli.health()
                        break
                    except Exception:
                        time.sleep(0.05)
                result = cli.submit(
                    "live seat proof",
                    seat="SPARK",
                    async_mode=False,
                )
                self.assertEqual(result["status"], "completed")
                self.assertIn("GrokBot in-process seat execution", result["result_text"])
                self.assertIn("seat=SPARK", result["result_text"])
                self.assertEqual(result["attribution"]["harness"], "grokbot")
                self.assertEqual(result["attribution"]["pool_id"], "grokbot")
                self.assertEqual(result["attribution"]["seat"], "SPARK")
            finally:
                server.shutdown()
                server.server_close()
                server.controller.store.close()



class TestMemoryGuard(unittest.TestCase):
    def test_health_reports_memory_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "runs.sqlite3"
            server = gateway.build_server(
                host="127.0.0.1",
                port=0,
                db_path=db,
                mode="echo",
                min_free_mb=1024,
                free_mb_fn=lambda: 200,
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                cli = client_mod.GrokBotControlClient("http://127.0.0.1:%d" % port)
                for _ in range(50):
                    try:
                        health = cli.health()
                        break
                    except Exception:
                        time.sleep(0.05)
                guard = health["memory_guard"]
                self.assertEqual(guard["min_free_mb"], 1024)
                self.assertEqual(guard["free_physical_mb"], 200)
                self.assertTrue(guard["holding"])
            finally:
                server.shutdown()
                server.server_close()
                server.controller.store.close()

    def test_submit_refused_under_floor_no_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "runs.sqlite3"
            server = gateway.build_server(
                host="127.0.0.1",
                port=0,
                db_path=db,
                mode="echo",
                min_free_mb=1024,
                free_mb_fn=lambda: 64,
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                import json, urllib.error, urllib.request
                raw = json.dumps(
                    {"pool_id": "grokbot", "prompt": "should-not-run", "async": False}
                ).encode()
                req = urllib.request.Request(
                    "http://127.0.0.1:%d/v1/runs" % port,
                    data=raw,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    urllib.request.urlopen(req)
                    self.fail("expected 503")
                except urllib.error.HTTPError as exc:
                    self.assertEqual(exc.code, 503)
                    body = json.loads(exc.read().decode())
                    self.assertEqual(body["error"], "memory_guard")
                    self.assertEqual(body["free_physical_mb"], 64)
                    self.assertEqual(body["min_free_mb"], 1024)
                # No run persisted
                self.assertEqual(server.controller.store.cursor, 0)
                self.assertEqual(server.controller.memory_guard()["held_refused"], 1)
            finally:
                server.shutdown()
                server.server_close()
                server.controller.store.close()

    def test_unreadable_free_never_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "runs.sqlite3"
            server = gateway.build_server(
                host="127.0.0.1",
                port=0,
                db_path=db,
                mode="echo",
                min_free_mb=1024,
                free_mb_fn=lambda: None,
            )
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                cli = client_mod.GrokBotControlClient("http://127.0.0.1:%d" % port)
                for _ in range(50):
                    try:
                        cli.health()
                        break
                    except Exception:
                        time.sleep(0.05)
                result = cli.submit("ok-when-unreadable", async_mode=False)
                self.assertEqual(result["status"], "completed")
                self.assertFalse(cli.health()["memory_guard"]["holding"])
            finally:
                server.shutdown()
                server.server_close()
                server.controller.store.close()

if __name__ == "__main__":
    unittest.main()