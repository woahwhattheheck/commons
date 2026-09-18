#!/usr/bin/env python3
"""The Commons Android APK project is real source, not a Pages wrapper."""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))


class CommonsAndroidProjectTests(unittest.TestCase):
    def test_gradle_tree_exists(self):
        for rel in (
            "android/settings.gradle",
            "android/build.gradle",
            "android/app/build.gradle",
            "android/app/src/main/AndroidManifest.xml",
            "android/app/src/main/java/org/commons/android/MainActivity.kt",
            "android/app/src/main/java/org/commons/android/HandsEngine.kt",
            "android/app/src/main/java/org/commons/android/HandsAccessibilityService.kt",
            "android/app/debug.keystore",
            ".github/workflows/commons-android.yml",
            "host/commons_android/lan_client.py",
        ):
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(path), rel)

    def test_not_a_webview_of_pages(self):
        kotlin_root = os.path.join(ROOT, "android/app/src/main/java")
        hits = []
        for dirpath, _dirs, files in os.walk(kotlin_root):
            for name in files:
                if not name.endswith(".kt"):
                    continue
                text = Path(dirpath, name).read_text(encoding="utf-8")
                if re.search(r"android\.webkit\.WebView|\bWebView\s*\(", text):
                    hits.append(name)
        self.assertEqual(hits, [])

    def test_workflow_assembles_debug(self):
        text = Path(os.path.join(ROOT, ".github/workflows/commons-android.yml")).read_text(encoding="utf-8")
        self.assertIn("working-directory: android", text)
        self.assertIn("assembleDebug", text)
        self.assertIn("workflow_dispatch", text)
        self.assertNotIn("listArtifactsForRepo", text)
        self.assertNotIn("deleteArtifact", text)

    def test_ntfy_hosts_match_relay_manifest(self):
        manifest = json.loads(Path(os.path.join(ROOT, "relay-manifest.json")).read_text(encoding="utf-8"))
        client = Path(
            os.path.join(ROOT, "android/app/src/main/java/org/commons/android/CommonsClient.kt"),
        ).read_text(encoding="utf-8")
        for relay in manifest["relays"]:
            self.assertIn(relay["url"], client)
        self.assertIn(manifest["topic"], client)

    def test_lan_forwarder_contract(self):
        from host.titan_hands.tests.test_android_lan import LanAndroidTests

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(LanAndroidTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        self.assertTrue(result.wasSuccessful())

    def test_job_post_is_cited_not_reminted(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "p/wire-commons-android-apk-20260826-01.md")))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "p/grok-titan-android-open-lan-20260828-01.md")))
        lan = Path(os.path.join(ROOT, "host/commons_android/lan_client.py")).read_text(encoding="utf-8")
        self.assertIn("wire-commons-android-apk-20260826-01", lan)
        self.assertIn("grok-titan-android-open-lan-20260828-01", lan)
        readme = Path(os.path.join(ROOT, "android/README.md")).read_text(encoding="utf-8")
        self.assertIn("wire-commons-android-apk-20260826-01", readme)
        self.assertIn("assembleDebug", readme)
        self.assertNotIn("X-Commons-Pairing", readme)
        self.assertNotIn("TITAN_HANDS_ANDROID_LAN_PAIRING", readme)
        self.assertIn("credential-free", readme.lower())
        self.assertFalse(os.path.isfile(os.path.join(ROOT, "android/app/src/main/java/org/commons/android/Pairing.kt")))
        lan_src = Path(os.path.join(ROOT, "android/app/src/main/java/org/commons/android/HttpJsonServer.kt")).read_text(encoding="utf-8")
        self.assertNotIn("PAIRING_REQUIRED", lan_src)
        self.assertNotIn("expectedPairing", lan_src)


if __name__ == "__main__":
    unittest.main()
