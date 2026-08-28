#!/usr/bin/env python3
"""Negative + contract tests for the Directive 10 owner-context display host.

Cite: BRYCE-1787134106972-vr8fo8. Do not remint.
Law: admin-no-verification-loop-20260819-01. Do not remint.
Run: python3 test_owner_context.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "host"))

import owner_context as oc
import owner_enroll
import owner_net

FIXTURE_V4 = "192.0.2.1"
FIXTURE_V4B = "198.51.100.9"
FIXTURE_V6 = "2001:db8::1"
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(r"\b[0-9a-fA-F:]+:[0-9a-fA-F:]+\b")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def spec_two_slot() -> dict:
    pc = owner_enroll.digest_ip(FIXTURE_V4, "commons-owner-v1")
    phone = owner_enroll.digest_ip(FIXTURE_V6, "commons-owner-v1")
    spec = {
        "claim": "BRYCE",
        "algo": "sha256",
        "pepper": "commons-owner-v1",
        "slots": {"pc": {"sha256": pc}, "phone": {"sha256": phone}},
        "hashes": [],
        "context_host": {
            "k": "owner-context",
            "v": 1,
            "pepper_version": "v1",
            "retention_seconds": 21600,
            "display_only": True,
            "authority": False,
            "gate": False,
            "public_url": "",
            "candidates": [],
            "status": "CODE_LANDED",
        },
    }
    owner_net.refresh_hashes(spec)
    return spec


class OwnerContextTests(unittest.TestCase):
    def setUp(self) -> None:
        oc.CACHE.rows.clear()
        self.spec = spec_two_slot()

    def _call(self, method="GET", path="/owner-context", headers=None, body=b"", remote=""):
        return oc.handle_http(method, path, headers or {}, body, remote, spec=self.spec, host_name="test")

    def _json(self, method="GET", path="/owner-context", headers=None, body=b"", remote=""):
        status, hdrs, blob = self._call(method, path, headers, body, remote)
        text = blob.decode("utf-8")
        self.assertFalse(IPV4_RE.search(text), "response leaked an IPv4")
        self.assertFalse(IPV6_RE.search(text), "response leaked an IPv6")
        obj = json.loads(text) if text else {}
        return status, dict(hdrs), obj

    def test_digest_matches_owner_enroll(self):
        self.assertEqual(oc.digest_ip(FIXTURE_V4), owner_enroll.digest_ip(FIXTURE_V4, "commons-owner-v1"))

    def test_pc_and_phone_are_distinct(self):
        one = oc.simulate(FIXTURE_V4, "pc", spec=self.spec)
        two = oc.simulate(FIXTURE_V6, "phone", spec=self.spec)
        self.assertNotEqual(one["sha256"], two["sha256"])
        self.assertEqual(one["slot"], "pc")
        self.assertEqual(two["slot"], "phone")
        self.assertTrue(owner_net.distinct_live(self.spec))

    def test_display_only_flags(self):
        payload = oc.simulate(FIXTURE_V4, "pc", spec=self.spec)
        self.assertTrue(payload["display_only"])
        self.assertIs(payload["authority"], False)
        self.assertIs(payload["gate"], False)
        self.assertTrue(payload["claim_still"])

    def test_missing_peer_is_200_not_a_lock(self):
        status, _hdrs, obj = self._json(headers={}, remote="")
        self.assertEqual(status, 200)
        self.assertFalse(obj["available"])
        self.assertEqual(obj["reason"], "no-peer")
        self.assertIs(obj["authority"], False)
        self.assertIs(obj["gate"], False)

    def test_no_www_authenticate_and_no_401(self):
        status, hdrs, obj = self._json(headers={"Authorization": "Bearer pretend"})
        self.assertEqual(status, 200)
        joined = " ".join("%s:%s" % item for item in hdrs.items())
        self.assertNotIn("www-authenticate", joined.lower())
        self.assertNotIn("401", str(status))
        self.assertIs(obj["gate"], False)

    def test_cookie_is_ignored_not_a_session(self):
        status, _hdrs, obj = self._json(headers={"Cookie": "session=forged", "X-Real-IP": FIXTURE_V4})
        self.assertEqual(status, 200)
        self.assertEqual(obj["slot"], "pc")
        self.assertIs(obj["authority"], False)

    def test_client_supplied_digest_cannot_spoof_slot(self):
        phone = owner_enroll.digest_ip(FIXTURE_V6, "commons-owner-v1")
        body = json.dumps({"sha256": phone, "via": "phone"}).encode("utf-8")
        status, _hdrs, obj = self._json(
            method="POST",
            path="/owner-context",
            headers={"X-Real-IP": FIXTURE_V4, "Content-Type": "application/json"},
            body=body,
        )
        self.assertEqual(status, 200)
        self.assertEqual(obj["sha256"], oc.digest_ip(FIXTURE_V4))
        self.assertEqual(obj["slot"], "pc")
        self.assertNotEqual(obj["slot"], "phone")

    def test_lookalike_via_is_dropped(self):
        for via in ("PC", "owner", "admin", "root", "phone ", "pc\n", "phone%00", " Pal"):
            self.assertEqual(oc.normalize_via(via), "", via)
        self.assertEqual(oc.normalize_via("pc"), "pc")
        self.assertEqual(oc.normalize_via("phone"), "phone")

    def test_via_hint_is_not_authority(self):
        status, _hdrs, obj = self._json(path="/owner-context?via=phone", headers={"X-Real-IP": FIXTURE_V4})
        self.assertEqual(obj["via_hint"], "phone")
        self.assertEqual(obj["slot"], "pc")
        self.assertIs(obj["authority"], False)

    def test_replay_same_digest_is_not_a_token(self):
        first = oc.simulate(FIXTURE_V4, "pc", spec=self.spec)
        second = oc.simulate(FIXTURE_V4, "pc", spec=self.spec)
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(second["slot"], "pc")
        self.assertIs(second["authority"], False)
        cached = oc.CACHE.get(first["sha256"])
        self.assertIsNotNone(cached)

    def test_retention_expires(self):
        digest = oc.digest_ip(FIXTURE_V4)
        from datetime import datetime, timedelta, timezone
        past = datetime.now(timezone.utc) - timedelta(seconds=oc.RETENTION_SECONDS + 10)
        oc.CACHE.put(digest, "pc", now=past)
        self.assertIsNone(oc.CACHE.get(digest))

    def test_cross_slot_confusion_refused(self):
        # pc digest never paints as phone even if via_hint says phone.
        payload = oc.annotate_context(
            headers={"X-Real-IP": FIXTURE_V4},
            spec=self.spec,
            via_hint="phone",
        )
        self.assertEqual(payload["slot"], "pc")
        other = oc.annotate_context(
            headers={"X-Real-IP": FIXTURE_V4B},
            spec=self.spec,
            via_hint="pc",
        )
        self.assertEqual(other["slot"], "")
        self.assertNotEqual(other["sha256"], payload["sha256"])

    def test_raw_ip_refused_in_blob(self):
        with self.assertRaises(ValueError):
            oc.refuse_raw_ips('{"note":"%s"}' % FIXTURE_V4)
        with self.assertRaises(ValueError):
            oc.refuse_raw_ips('{"note":"%s"}' % FIXTURE_V6)

    def test_put_and_delete_still_200_display(self):
        for method in ("PUT", "DELETE", "PATCH"):
            status, _hdrs, obj = self._json(method=method, headers={"X-Real-IP": FIXTURE_V4})
            self.assertEqual(status, 200, method)
            self.assertIs(obj["gate"], False)

    def test_options_is_204_cors_open(self):
        status, hdrs, _obj = self._json(method="OPTIONS")
        self.assertEqual(status, 204)
        self.assertEqual(hdrs.get("Access-Control-Allow-Origin"), "*")

    def test_health_and_doctor_omit_ips(self):
        status, _hdrs, health = self._json(path="/health")
        self.assertEqual(status, 200)
        self.assertTrue(health["ok"])
        report = oc.doctor(spec=self.spec, probe=False, root=HERE)
        blob = json.dumps(report)
        self.assertFalse(IPV4_RE.search(blob))
        self.assertFalse(IPV6_RE.search(blob))
        self.assertTrue(report["display_only"])
        self.assertIs(report["authority"], False)
        self.assertIs(report["gate"], False)
        self.assertIn("EXTERNAL_HOST_ACTION", report)
        self.assertTrue(report["EXTERNAL_HOST_ACTION"])
        self.assertNotEqual(report["state"], "LIVE")

    def test_doctor_does_not_invent_live(self):
        report = oc.doctor(spec=self.spec, probe=False)
        self.assertFalse(report["live"])
        self.assertEqual(report["public_url"], "")
        self.assertIn("commons-spark-mcp.vercel.app", report["EXTERNAL_HOST_ACTION"])

    def test_simulate_rejects_non_documentation_ip_on_cli(self):
        code = oc.main(["simulate", "--ip", "8.8.8.8"])
        self.assertEqual(code, 2)

    def test_loopback_server_does_not_log_ip(self):
        handler = oc.OwnerContextHandler
        handler.spec = self.spec
        handler.host_name = "loop"
        import io
        from http.server import ThreadingHTTPServer
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = httpd.server_address[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:%d/owner-context" % port,
                headers={"X-Real-IP": FIXTURE_V4, "User-Agent": "owner-context-test"},
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = resp.read().decode("utf-8")
                self.assertEqual(resp.status, 200)
            obj = json.loads(raw)
            self.assertEqual(obj["slot"], "pc")
            self.assertFalse(IPV4_RE.search(raw))
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_adapter_names_external_action(self):
        vercel = oc.deployment_adapter("vercel")
        self.assertTrue(vercel["ok"])
        self.assertTrue(vercel["EXTERNAL_HOST_ACTION"])
        self.assertIs(vercel["authority"], False)
        local = oc.deployment_adapter("local")
        self.assertEqual(local["EXTERNAL_HOST_ACTION"], "")

    def test_owner_json_on_disk_has_no_ip(self):
        blob = open(os.path.join(HERE, "owner.json"), encoding="utf-8").read()
        self.assertFalse(IPV4_RE.search(blob))
        self.assertFalse(IPV6_RE.search(blob))
        spec = json.loads(blob)
        self.assertTrue(owner_net.distinct_live(spec))

    def test_active_sources_never_gate(self):
        paths = [
            "host/owner_context.py",
            "owner_net.js",
            "owner-net.html",
            "owner.html",
            "api/owner_context.py",
            "integrations/owner_context/service.py",
        ]
        forbidden = (
            "www-authenticate",
            "status = 401",
            "status = 403",
            "require_login",
            "AUTH_REQUIRED",
        )
        for rel in paths:
            path = os.path.join(HERE, rel)
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8").read().lower()
            for token in forbidden:
                self.assertNotIn(token.lower(), text, rel)

    def test_js_does_not_fill_claim_from_host(self):
        js = open(os.path.join(HERE, "owner_net.js"), encoding="utf-8").read()
        self.assertIn("fetchHostContext", js)
        self.assertIn("fillClaim(ONLY_CLAIM)", js)
        # fillClaim stays bound to local matchingSlot, not host slot.
        self.assertIn("matchedSlot = matchingSlot(spec, digests)", js)
        self.assertIn("if (matched)", js)
        self.assertNotIn("fillClaim(host", js)
        self.assertIn("authority", js.lower())

    def test_html_says_display_only(self):
        html = open(os.path.join(HERE, "owner-net.html"), encoding="utf-8").read()
        self.assertIn("owner-host-state", html)
        self.assertIn("display only", html.lower())
        self.assertIn("cannot control participation, reads, writes, or execution", html)

    def test_leftover_measure_and_classify(self):
        facts = {path: True for path in oc.SEARCH_SPACE}
        measured = oc.measure_from_rows(facts)
        self.assertEqual(measured["state"], "PRESENT")
        classified = oc.classify({"code_landed": True, "live": False})
        self.assertEqual(classified["state"], "CODE_LANDED")
        live = oc.classify({"code_landed": True, "live": True})
        self.assertEqual(live["state"], "LIVE")
        miss = oc.measure_from_rows({})
        self.assertEqual(miss["state"], oc.FINDER_FAILED)
        self.assertIn("Never 0", miss["note"])

    def test_source_contains_land_markers(self):
        src = open(os.path.join(HERE, "host", "owner_context.py"), encoding="utf-8").read()
        for token in (
            "def annotate_context",
            "def doctor",
            "def simulate",
            "def measure_from_rows",
            "def classify",
            "display_only",
            "no auth",
            "no gate",
            "refuse_raw_ips",
            "EXTERNAL_HOST_ACTION",
            "FINDER-FAILED",
            "Never 0",
        ):
            self.assertIn(token, src, token)


if __name__ == "__main__":
    raise SystemExit(unittest.main(verbosity=2))
