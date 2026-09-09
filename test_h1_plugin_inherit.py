#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from h1_plugin_inherit import (
    DOCUMENTED_PLUGINS,
    SCHEMA,
    classify,
    documented_hit_fixture,
    enabled_plugins_from_settings,
    evaluate,
    inspect_half,
    probe_inherit_source,
    user_claude_home,
)


class TestH1PluginInherit(unittest.TestCase):
    def test_empty_home_is_seat_clear(self):
        with tempfile.TemporaryDirectory() as home:
            result = evaluate(home)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["status"], "SEAT_CLEAR")
        self.assertFalse(result["source"]["inherit_source"])
        self.assertEqual(result["inspect"]["inspect_status"], "NOT_RUN")
        self.assertTrue(result["do_not_rewrite_claude_settings"])

    def test_official_enabled_plugins_are_inherit_source(self):
        with tempfile.TemporaryDirectory() as home:
            claude = user_claude_home(home)
            os.makedirs(claude)
            with open(os.path.join(claude, "settings.json"), "w", encoding="utf-8") as handle:
                json.dump({"enabledPlugins": {DOCUMENTED_PLUGINS[0]: True}}, handle)
            source = probe_inherit_source(home)
            result = evaluate(home)
        self.assertEqual(source["official_plugins_enabled"], [DOCUMENTED_PLUGINS[0]])
        self.assertTrue(source["inherit_source"])
        self.assertEqual(result["status"], "INHERIT_SOURCE_PRESENT")

    def test_documented_hit_is_h1_hit(self):
        inspection, settings = documented_hit_fixture()
        with tempfile.TemporaryDirectory() as home:
            claude = user_claude_home(home)
            os.makedirs(claude)
            with open(os.path.join(claude, "settings.json"), "w", encoding="utf-8") as handle:
                json.dump(settings, handle)
            result = evaluate(home, inspection=inspection)
        self.assertEqual(result["status"], "H1_HIT")
        self.assertEqual(result["inspect"]["inspect_status"], "BLOCKED")
        self.assertEqual(result["inspect"]["claude_plugins_enabled"], 3)
        self.assertEqual(result["inspect"]["claude_compat_cells_enabled"], 0)

    def test_malformed_settings_is_finder_failed(self):
        with tempfile.TemporaryDirectory() as home:
            claude = user_claude_home(home)
            os.makedirs(claude)
            with open(os.path.join(claude, "settings.json"), "w", encoding="utf-8") as handle:
                handle.write("{not-json")
            result = evaluate(home)
        self.assertEqual(result["status"], "FINDER-FAILED")
        self.assertTrue(result["source"]["errors"])

    def test_inspect_error_is_finder_failed_not_zero(self):
        with tempfile.TemporaryDirectory() as home:
            result = evaluate(home, inspect_error="grok inspect failed")
        self.assertEqual(result["status"], "FINDER-FAILED")
        self.assertEqual(result["inspect"]["inspect_status"], "FINDER-FAILED")
        self.assertTrue(any("never silent 0" in row.lower() for row in result["z"]))

    def test_cursor_public_cache_is_not_user_inherit(self):
        with tempfile.TemporaryDirectory() as home:
            decoy = os.path.join(home, ".cursor", "plugins", "cache", "cursor-public", "x", ".claude")
            os.makedirs(decoy)
            with open(os.path.join(decoy, "settings.json"), "w", encoding="utf-8") as handle:
                json.dump({"enabledPlugins": {DOCUMENTED_PLUGINS[0]: True}}, handle)
            result = evaluate(home)
        self.assertEqual(result["status"], "SEAT_CLEAR")
        self.assertFalse(result["source"]["inherit_source"])

    def test_classify_requires_compat_false_plus_enabled_plugins(self):
        source = {"inherit_source": True, "errors": []}
        inspect_row = {
            "inspect_status": "BLOCKED",
            "claude_plugins_enabled": 1,
            "claude_compat_cells_enabled": 0,
        }
        self.assertEqual(classify(source, inspect_row), "H1_HIT")
        inspect_row["claude_compat_cells_enabled"] = 1
        self.assertEqual(classify(source, inspect_row), "INHERIT_SOURCE_PRESENT")

    def test_enabled_plugins_helper_and_inspect_half(self):
        self.assertEqual(
            enabled_plugins_from_settings({"enabledPlugins": {"a@claude-plugins-official": True, "b": False}}),
            ["a@claude-plugins-official"],
        )
        clean = inspect_half({
            "externalCompat": {"cells": [{"vendor": "claude", "surface": "skills", "enabled": False}]},
            "projectInstructions": [],
            "skills": [],
            "plugins": [],
            "hooks": [],
            "mcpServers": [],
        })
        self.assertEqual(clean["inspect_status"], "PASS")


if __name__ == "__main__":
    unittest.main()
