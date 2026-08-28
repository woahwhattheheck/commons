#!/usr/bin/env python3
"""Focused proof for Grok Slack DPAPI/current-user token handoff."""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from integrations.grok_slack import bridge
from integrations.grok_slack import handoff


def _bot() -> str:
    return "xoxb" + "-handoff-test-bot-aaaaaaaa"


def _app() -> str:
    return "xapp" + "-handoff-test-app-bbbbbbbb"


def _post(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "Host": "127.0.0.1"})
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _get(url: str, host: str = "127.0.0.1") -> tuple[int, bytes]:
    request = Request(url, headers={"Host": host, "Accept": "application/json, text/html"})
    with urlopen(request, timeout=5) as response:
        return response.status, response.read()


class GrokSlackHandoffTests(unittest.TestCase):
    def test_vault_roundtrip_is_encrypted_and_user_bound(self) -> None:
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grok_slack.vault"
            protector = handoff.PosixUserProtector(material=b"user-a")
            written = handoff.write_vault(path, bot, app, protector=protector)
            raw = path.read_bytes()
            self.assertTrue(written["encrypted"])
            self.assertFalse(written["plaintext_disk"])
            self.assertNotIn(bot.encode(), raw)
            self.assertNotIn(app.encode(), raw)
            self.assertTrue(raw.startswith(handoff.MAGIC))
            mode = path.stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)
            loaded = handoff.read_vault(path, protector=protector)
            self.assertTrue(hmac.compare_digest(loaded["bot_token"], bot))
            self.assertTrue(hmac.compare_digest(loaded["app_token"], app))
            self.assertEqual(loaded["slack_app_id"], "A0BTJMFPTT6")
            other = handoff.PosixUserProtector(material=b"user-b")
            with self.assertRaises(handoff.VaultError):
                handoff.read_vault(path, protector=other)

    def test_inject_and_status_never_return_values(self) -> None:
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault"
            protector = handoff.PosixUserProtector(material=b"user-a")
            handoff.write_vault(path, bot, app, protector=protector)
            env: dict[str, str] = {}
            injected = handoff.inject_vault_into(env, vault_path=path, protector=protector)
            blob = json.dumps(injected)
            self.assertNotIn(bot, blob)
            self.assertNotIn(app, blob)
            self.assertEqual(injected["vault"], "present")
            self.assertTrue(hmac.compare_digest(env["SLACK_BOT_TOKEN"], bot))
            env_wins = {"SLACK_BOT_TOKEN": "already", "SLACK_APP_TOKEN": "already"}
            handoff.inject_vault_into(env_wins, vault_path=path, protector=protector)
            self.assertEqual(env_wins["SLACK_BOT_TOKEN"], "already")
            status = handoff.redacted_status(env={}, vault_path=path, protector=protector)
            encoded = json.dumps(status)
            self.assertNotIn(bot, encoded)
            self.assertNotIn(app, encoded)
            self.assertEqual(status["slack_bot_token"], "present")
            self.assertEqual(status["slack_app_token"], "present")
            self.assertEqual(status["slack_app_id"], "A0BTJMFPTT6")
            self.assertFalse(status["live"])
            self.assertFalse(status["plaintext_disk"])
            self.assertTrue(status["gemini_isolated"])

    def test_browser_activate_is_loopback_and_redacted(self) -> None:
        bot, app = _bot(), _app()
        started: list[tuple[str, str]] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault"
            protector = handoff.PosixUserProtector(material=b"user-a")
            app_obj = handoff.HandoffApp(
                bind="127.0.0.1:0",
                vault_path=path,
                protector=protector,
                starter=lambda b, a: started.append((b, a)),
                live_probe=lambda: False,
                health_bind="127.0.0.1:8788",
                env={},
            )
            app_obj.start()
            self.addCleanup(app_obj.stop)
            page_status, page = _get(app_obj.url)
            self.assertEqual(page_status, 200)
            html = page.decode("utf-8")
            self.assertIn("Activate", html)
            self.assertIn("A0BTJMFPTT6", html)
            self.assertIn("127.0.0.1:8780", html)
            self.assertNotIn(bot, html)
            code, payload = _post(app_obj.url + "activate", {"bot_token": bot, "app_token": app})
            self.assertEqual(code, 200)
            encoded = json.dumps(payload)
            self.assertNotIn(bot, encoded)
            self.assertNotIn(app, encoded)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["slack_app_id"], "A0BTJMFPTT6")
            self.assertEqual(payload["status"]["slack_bot_token"], "present")
            self.assertFalse(payload["status"]["live"])
            self.assertTrue(hmac.compare_digest(started[0][0], bot))
            status_code, status_body = _get(app_obj.url + "status")
            self.assertEqual(status_code, 200)
            status = json.loads(status_body.decode("utf-8"))
            self.assertNotIn(bot, status_body.decode("utf-8"))
            self.assertEqual(status["vault"], "present")
            self.assertFalse(status["live"])
            self.assertEqual(status["auth"], "none")

    def test_restart_reloads_vault_without_plaintext(self) -> None:
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault"
            protector = handoff.PosixUserProtector(material=b"user-a")
            first = handoff.HandoffApp(
                bind="127.0.0.1:0",
                vault_path=path,
                protector=protector,
                starter=lambda _b, _a: None,
                live_probe=lambda: False,
                env={},
            )
            first.activate(bot, app)
            second_env: dict[str, str] = {}
            second = handoff.HandoffApp(
                bind="127.0.0.1:0",
                vault_path=path,
                protector=protector,
                starter=lambda _b, _a: None,
                live_probe=lambda: False,
                env=second_env,
            )
            second.load_and_maybe_start()
            self.assertTrue(hmac.compare_digest(second_env["SLACK_BOT_TOKEN"], bot))
            self.assertTrue(hmac.compare_digest(second_env["SLACK_APP_TOKEN"], app))
            self.assertNotIn(bot, json.dumps(second.status()))

    def test_gemini_port_and_home_are_refused(self) -> None:
        with self.assertRaises(handoff.VaultError):
            handoff.parse_loopback_bind("127.0.0.1:8780")
        with self.assertRaises(handoff.VaultError):
            handoff.parse_loopback_bind("0.0.0.0:8789")
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            gemini = Path(directory) / ".gemini"
            gemini.mkdir()
            original = handoff.gemini_home
            handoff.gemini_home = lambda: gemini  # type: ignore[method-assign]
            self.addCleanup(lambda: setattr(handoff, "gemini_home", original))
            with self.assertRaises(handoff.VaultError):
                handoff.write_vault(gemini / "grok_slack.vault", bot, app, protector=handoff.PosixUserProtector(material=b"x"))

    def test_source_does_not_import_or_write_gemini_bridge(self) -> None:
        text = (handoff.integration_root() / "handoff.py").read_text(encoding="utf-8")
        self.assertNotIn("integrations.gemini_slack", text)
        self.assertNotIn("gemini_slack", text)
        self.assertIn("A0BTJMFPTT6", text)
        self.assertIn("127.0.0.1:8789", text)
        self.assertIn("win_dpapi", text)
        gemini_bridge = Path("integrations/gemini_slack/bridge.py").read_bytes()
        self.assertTrue(gemini_bridge)
        self.assertNotIn(b"A0BTJMFPTT6", gemini_bridge)
        self.assertIsNone(bridge.TOKEN_VALUE_RE.search(text))
        self.assertIsNone(bridge.TOKEN_VALUE_RE.search((handoff.integration_root() / "run-handoff.ps1").read_text(encoding="utf-8")))

    def test_host_header_must_be_loopback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app_obj = handoff.HandoffApp(
                bind="127.0.0.1:0",
                vault_path=Path(directory) / "vault",
                protector=handoff.PosixUserProtector(material=b"user-a"),
                starter=lambda _b, _a: None,
                live_probe=lambda: False,
                env={},
            )
            app_obj.start()
            self.addCleanup(app_obj.stop)
            parsed = urlparse(app_obj.url)
            conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
            conn.request("GET", "/status", headers={"Host": "evil.example"})
            resp = conn.getresponse()
            body = resp.read()
            self.assertEqual(resp.status, 404)
            self.assertNotIn(_bot().encode(), body)
            conn.close()

    def test_bridge_loads_vault_and_health_stays_honest(self) -> None:
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault"
            protector = handoff.PosixUserProtector(material=b"user-a")
            handoff.write_vault(path, bot, app, protector=protector)
            env: dict[str, str] = {}
            report = handoff.inject_vault_into(env, vault_path=path, protector=protector)
            args = type("Args", (), {
                "state_db": Path(directory) / "db.sqlite3",
                "probe": "",
                "health_bind": "127.0.0.1:8788",
            })()
            code, health = bridge.health(args, env=env, root=bridge.integration_root())
            encoded = json.dumps(health) + json.dumps(report)
            self.assertNotIn(bot, encoded)
            self.assertNotIn(app, encoded)
            self.assertEqual(health["slack_bot_token"], "present")
            self.assertEqual(health["state"], "NOT_READY")
            self.assertFalse(health.get("live"))
            self.assertEqual(code, 2)

    def test_windows_bridge_spawn_and_launcher_never_allocate_a_console(self) -> None:
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault"
            protector = handoff.PosixUserProtector(material=b"user-a")
            handoff.write_vault(path, bot, app, protector=protector)
            app_obj = handoff.HandoffApp(
                bind="127.0.0.1:0",
                vault_path=path,
                protector=protector,
                live_probe=lambda: False,
                env={},
            )
            with patch.object(handoff, "probe_live", return_value=False), \
                    patch.object(handoff.sys, "platform", "win32"), \
                    patch.object(handoff.subprocess, "Popen") as popen:
                popen.return_value.poll.return_value = None
                self.assertTrue(app_obj.ensure_bridge())
            kwargs = popen.call_args.kwargs
            self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
            self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
            self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
            self.assertTrue(kwargs["close_fds"])
            self.assertEqual(kwargs["creationflags"] & 0x08000000, 0x08000000)

        posix = handoff.background_process_kwargs("linux")
        self.assertTrue(posix["start_new_session"])
        windows = handoff.background_process_kwargs("win32")
        self.assertEqual(windows["creationflags"] & 0x08000000, 0x08000000)

        launcher = (handoff.integration_root() / "run-handoff.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$Foreground", launcher)
        self.assertIn("pythonw.exe", launcher)
        self.assertIn("-WindowStyle Hidden", launcher)
        self.assertNotIn("Start-Process -FilePath $python ", launcher)

    def test_windows_dpapi_symbols_exist_without_calling_them_here(self) -> None:
        self.assertTrue(callable(handoff.WinDpapiProtector().protect))
        self.assertEqual(handoff.SLACK_APP_ID, "A0BTJMFPTT6")
        self.assertEqual(handoff.DEFAULT_HANDOFF_BIND, "127.0.0.1:8789")
        self.assertEqual(handoff.GEMINI_HANDOFF_BIND, "127.0.0.1:8780")
        digest = hashlib.sha256(Path("integrations/gemini_slack/bridge.py").read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)

    def test_binary_cdata_roundtrip_keeps_embedded_nuls(self) -> None:
        blob = b"\x01\x00\x00\x00DPAPI\x00\xff" + bytes(range(32)) + b"\x00END"
        buf, n = handoff._cdata_from_bytes(blob)
        out = handoff._bytes_from_cdata(buf, n)
        self.assertEqual(out, blob)
        self.assertIn(b"\x00", out)
        source = (handoff.integration_root() / "handoff.py").read_text(encoding="utf-8")
        self.assertNotIn("create_string_buffer(blob", source)
        self.assertNotIn("create_string_buffer(plaintext", source)
        self.assertIn("from_buffer_copy", source)
        self.assertIn("WinDLL", source)

    def test_nul_embedding_protector_survives_write_and_is_not_deleted_on_failed_read(self) -> None:
        class NulBlobProtector(handoff.Protector):
            name = "nul_blob"

            def __init__(self, inner: handoff.Protector) -> None:
                self.inner = inner

            def protect(self, plaintext: bytes) -> bytes:
                return b"\x01\x00\x00\x00\xd0\x8c\x9d\xdf" + os.urandom(8) + self.inner.protect(plaintext)

            def unprotect(self, blob: bytes) -> bytes:
                if len(blob) < 16 or blob[:4] != b"\x01\x00\x00\x00":
                    raise handoff.VaultError("vault unreadable")
                return self.inner.unprotect(blob[16:])

        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grok_slack.vault"
            inner = handoff.PosixUserProtector(material=b"user-a")
            protector = NulBlobProtector(inner)
            written = handoff.write_vault(path, bot, app, protector=protector)
            raw = path.read_bytes()
            self.assertTrue(written["verified"])
            self.assertTrue(raw.startswith(handoff.MAGIC + handoff.KIND_POSIX))
            self.assertIn(b"\x00", raw[len(handoff.MAGIC) + 1 :])
            self.assertNotIn(bot.encode(), raw)
            loaded = handoff.read_vault(path, protector=protector)
            self.assertTrue(hmac.compare_digest(loaded["bot_token"], bot))
            before = path.read_bytes()
            other = handoff.PosixUserProtector(material=b"user-b")
            with self.assertRaises(handoff.VaultError):
                handoff.read_vault(path, protector=other)
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), before)

    def test_cross_process_and_restart_reread_same_vault(self) -> None:
        bot, app = _bot(), _app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grok_slack.vault"
            root = str(Path(__file__).resolve().parent)
            writer = (
                "import json,sys\\n"
                f"sys.path.insert(0,{root!r})\\n"
                "from pathlib import Path\\n"
                "from integrations.grok_slack import handoff\\n"
                f"path=Path({str(path)!r})\\n"
                f"bot={bot!r}; app={app!r}\\n"
                "p=handoff.PosixUserProtector(material=b'user-a')\\n"
                "handoff.write_vault(path, bot, app, protector=p)\\n"
                "print('WROTE', path.stat().st_size)\\n"
            )
            reader = (
                "import json,sys,hmac\\n"
                f"sys.path.insert(0,{root!r})\\n"
                "from pathlib import Path\\n"
                "from integrations.grok_slack import handoff\\n"
                f"path=Path({str(path)!r})\\n"
                f"bot={bot!r}; app={app!r}\\n"
                "p=handoff.PosixUserProtector(material=b'user-a')\\n"
                "loaded=handoff.read_vault(path, protector=p)\\n"
                "ok=hmac.compare_digest(loaded['bot_token'], bot) and hmac.compare_digest(loaded['app_token'], app)\\n"
                "print('READ', 'ok' if ok else 'bad', path.stat().st_size, loaded['slack_app_id'])\\n"
            )
            write_proc = subprocess.run([sys.executable, "-c", writer.replace("\\n", "\n")], capture_output=True, text=True, check=False)
            self.assertEqual(write_proc.returncode, 0, write_proc.stderr)
            self.assertIn("WROTE", write_proc.stdout)
            self.assertNotIn(bot, write_proc.stdout + write_proc.stderr)
            self.assertNotIn(app, write_proc.stdout + write_proc.stderr)
            read_proc = subprocess.run([sys.executable, "-c", reader.replace("\\n", "\n")], capture_output=True, text=True, check=False)
            self.assertEqual(read_proc.returncode, 0, read_proc.stderr)
            self.assertIn("READ ok", read_proc.stdout)
            self.assertIn("A0BTJMFPTT6", read_proc.stdout)
            self.assertNotIn(bot, read_proc.stdout + read_proc.stderr)
            env: dict[str, str] = {}
            restarted = handoff.HandoffApp(
                bind="127.0.0.1:0",
                vault_path=path,
                protector=handoff.PosixUserProtector(material=b"user-a"),
                starter=lambda _b, _a: None,
                live_probe=lambda: False,
                env=env,
            )
            restarted.load_and_maybe_start()
            self.assertTrue(hmac.compare_digest(env["SLACK_BOT_TOKEN"], bot))
            self.assertNotIn(bot, json.dumps(restarted.status()))
            self.assertTrue(path.is_file())

    def test_kind_win_header_is_preserved_and_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grok_slack.vault"
            fake = handoff.MAGIC + handoff.KIND_WIN + b"\x01\x00ciphertext\x00blob"
            path.write_bytes(fake)
            with self.assertRaises(handoff.VaultError):
                handoff.read_vault(path, protector=handoff.PosixUserProtector(material=b"x"))
            self.assertEqual(path.read_bytes(), fake)
            self.assertTrue(path.read_bytes().startswith(b"CGSVAULT1W"))

    def test_failed_write_does_not_replace_existing_vault(self) -> None:
        existing = handoff.MAGIC + handoff.KIND_WIN + b"\x01\x00keep-me\x00blob"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "grok_slack.vault"
            path.write_bytes(existing)

            class BoomProtector(handoff.Protector):
                name = "boom"

                def protect(self, plaintext: bytes) -> bytes:
                    del plaintext
                    return b"\x00new-ciphertext"

                def unprotect(self, blob: bytes) -> bytes:
                    del blob
                    raise handoff.VaultError("vault unreadable")

            with self.assertRaises(handoff.VaultError):
                handoff.write_vault(path, _bot(), _app(), protector=BoomProtector())
            self.assertEqual(path.read_bytes(), existing)
            self.assertFalse(path.with_suffix(path.suffix + ".tmp").is_file())



if __name__ == "__main__":
    unittest.main()
