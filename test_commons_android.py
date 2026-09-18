#!/usr/bin/env python3
"""The Commons Android APK project is real source, not a Pages wrapper."""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))

SETUP_ANDROID_USES = re.compile(
    r"^(?P<indent>[ \t]*)uses:[ \t]*android-actions/setup-android@v(?P<major>\d+)\S*[ \t]*$",
    re.MULTILINE,
)


def setup_android_package_tokens(workflow_text: str) -> tuple[int, list[str] | None]:
    """Return (major version, packages list or None if the step does not pin packages).

    Tokenize on whitespace so `cmdline-tools` is not treated as the retired
    `tools` package. android-actions/setup-android@v3 defaults to
    `tools platform-tools`; Google stopped serving `tools` on 2026-09-15.
    """
    match = SETUP_ANDROID_USES.search(workflow_text)
    if match is None:
        raise AssertionError("workflow is missing android-actions/setup-android")
    indent = match.group("indent")
    major = int(match.group("major"))
    packages = None
    for line in workflow_text[match.end() :].splitlines():
        if not line.strip():
            continue
        stripped = line.lstrip(" \t")
        line_indent = line[: len(line) - len(stripped)]
        if stripped.startswith("- ") and len(line_indent) <= len(indent):
            break
        if len(line_indent) < len(indent):
            break
        if stripped.startswith("packages:"):
            raw = stripped.split(":", 1)[1].strip().strip("'\"")
            packages = [token for token in raw.split() if token]
    return major, packages


def assert_setup_android_skips_retired_tools(workflow_text: str) -> list[str]:
    major, packages = setup_android_package_tokens(workflow_text)
    if major < 4:
        raise AssertionError(
            "setup-android@v%s still defaults to the retired tools package" % major
        )
    if packages is None:
        raise AssertionError(
            "setup-android must pin packages; do not inherit a default that requests tools"
        )
    if "tools" in packages:
        raise AssertionError("setup-android still requests the retired SDK tools package")
    if "platform-tools" not in packages:
        raise AssertionError("setup-android must still install platform-tools")
    return packages


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

    def test_unpinned_v3_setup_android_is_the_measured_failure(self):
        hostile = (
            "      - name: Setup Android SDK\n"
            "        uses: android-actions/setup-android@v3\n"
            "\n"
            "      - name: assembleDebug\n"
        )
        major, packages = setup_android_package_tokens(hostile)
        self.assertEqual(major, 3)
        self.assertIsNone(packages)
        with self.assertRaisesRegex(AssertionError, "retired tools package"):
            assert_setup_android_skips_retired_tools(hostile)

    def test_explicit_tools_package_is_rejected_and_cmdline_tools_is_not_tools(self):
        pinned_tools = (
            "      - name: Setup Android SDK\n"
            "        uses: android-actions/setup-android@v4\n"
            "        with:\n"
            "          packages: tools platform-tools\n"
        )
        with self.assertRaisesRegex(AssertionError, "retired SDK tools package"):
            assert_setup_android_skips_retired_tools(pinned_tools)
        ok = (
            "      - name: Setup Android SDK\n"
            "        uses: android-actions/setup-android@v4\n"
            "        with:\n"
            "          packages: cmdline-tools platform-tools\n"
        )
        self.assertEqual(
            assert_setup_android_skips_retired_tools(ok),
            ["cmdline-tools", "platform-tools"],
        )

    def test_workflow_does_not_request_removed_sdk_tools_package(self):
        text = Path(os.path.join(ROOT, ".github/workflows/commons-android.yml")).read_text(
            encoding="utf-8"
        )
        packages = assert_setup_android_skips_retired_tools(text)
        self.assertEqual(packages, ["platform-tools"])
        self.assertIn("android-actions/setup-android@v4", text)

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
