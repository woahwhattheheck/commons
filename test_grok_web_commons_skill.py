#!/usr/bin/env python3
"""Canonical grok.com web Skill: portable source, not account installation."""
from __future__ import annotations

import importlib.util
import io
import json
import re
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent
SKILL_DIR = ROOT / ".agents" / "skills" / "grok-web-commons"
SKILL = SKILL_DIR / "SKILL.md"
CONTRACT = SKILL_DIR / "references" / "connector-contract.md"
CHECKER = SKILL_DIR / "scripts" / "check_live_connector.py"
PUBLIC_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AIza[0-9A-Za-z_-]{20,}|ya29\.[0-9A-Za-z_-]+|xox[bpas]-[0-9A-Za-z-]+"
    r"|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY"
    r"|Authorization:\s*\S+|Bearer\s+\S+)",
    re.I,
)


def load_checker():
    spec = importlib.util.spec_from_file_location("check_live_connector", CHECKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unclosed YAML frontmatter")
    data = {}
    key = None
    for line in text[4:end].splitlines():
        if line.startswith("  ") and key == "description":
            data[key] = (data.get(key, "") + " " + line.strip()).strip()
            continue
        if line.startswith("  ") and key == "metadata":
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, val = match.group(1), match.group(2).strip()
        if val in {">", "|"}:
            data[key] = ""
            continue
        data[key] = val.strip("\"'")
    return data


class GrokWebCommonsSkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.contract = CONTRACT.read_text(encoding="utf-8")
        cls.checker_src = CHECKER.read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills" / "MANUAL.md").read_text(encoding="utf-8")
        cls.checker = load_checker()
        cls.owned = "\n".join([cls.skill, cls.contract, cls.checker_src])

    def test_required_frontmatter_and_directory_name_match(self):
        meta = frontmatter(self.skill)
        self.assertEqual(meta["name"], "grok-web-commons")
        self.assertEqual(SKILL_DIR.name, meta["name"])
        self.assertEqual(meta["license"], "Apache-2.0")
        desc = meta.get("description") or ""
        self.assertGreaterEqual(len(desc), 1)
        self.assertLessEqual(len(desc), 1024)
        self.assertIn("grok.com web", desc)
        self.assertIn("GitHub connector", desc)
        self.assertIn("Commons", desc)

    def test_catalog_and_manual_registration(self):
        matches = [row for row in self.registry["skills"] if row["id"] == "grok-web-commons"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["job"], "grok.com web connector + persistent Skill")
        self.assertEqual(matches[0].get("token") or "", "")
        self.assertIn(
            "[grok-web-commons](../.agents/skills/grok-web-commons/SKILL.md)",
            self.manual,
        )
        ids = [row["id"] for row in self.registry["skills"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("slash-commands", ids)
        self.assertLess(ids.index("slash-commands"), ids.index("grok-web-commons"))

    def test_exact_connector_url_and_auth_mode(self):
        for text in (self.skill, self.contract, self.checker_src):
            self.assertIn(PUBLIC_MCP_URL, text)
            self.assertIn("Streamable HTTP", text)
        self.assertIn("Authentication: None", self.skill)
        self.assertIn("Authentication | None", self.contract)
        self.assertIn('AUTH_MODE = "None"', self.checker_src)
        self.assertIn("Headers: none", self.skill)
        self.assertNotIn("Authorization:", self.skill)
        self.assertNotIn("Bearer ", self.skill)

    def test_surface_separation_from_grokbot_cursor_and_local_grok(self):
        for marker in (
            "surface: grok.com web",
            "Never report Grokbot, Cursor, terminal Grok",
            "plugins/commons-grok-cloud/**",
            "is not this Skill",
            "Do not rename or misrepresent",
        ):
            self.assertIn(marker, self.skill)
        self.assertIn("not this", self.contract)
        self.assertIn("grok.com web Skill and not a second Commons", self.contract)
        self.assertNotIn("You are Grokbot", self.skill)
        self.assertNotIn("Sent using Cursor", self.skill)

    def test_open_door_language(self):
        for marker in (
            "Possessing the link authorizes use",
            "Do not add login, authorization",
            "Speaker and capability fields stay optional",
            "context, never a gate",
            "never a gate",
            "Blank `from=` lands as `UNSEATED`",
            "open-door",
        ):
            self.assertIn(marker, self.skill)
        self.assertIn("never a", self.contract)
        self.assertIn("gate.", self.contract)
        self.assertNotIn("authentication required", self.owned.lower())
        self.assertNotIn("authorization required", self.owned.lower())
        self.assertNotIn("permission denied", self.owned.lower())

    def test_stable_id_and_durability_rules(self):
        for marker in (
            "ACCEPTED_DURABILITY_PENDING",
            "carrier acceptance only",
            "DURABLE_PAGE",
            "p/{id}.md",
            "matching body hash",
            "Never remint an ID merely because a response timed out",
            "identical bytes is an idempotent recovery path",
            "different content is a conflict",
            "3,900-byte UTF-8",
            "Current Git HEAD plus exact `p/{id}.md`",
        ):
            self.assertIn(marker, self.skill)

    def test_github_and_mcp_operating_rules(self):
        for marker in (
            "search_connected_tools",
            "call_connected_tool",
            "Resolve live GitHub `main`",
            "Inspect open PRs and path overlap",
            "unique non-force branch",
            "read_observatory",
            "route_grokcom_revenue_work` only for an actual revenue directive",
            "fire_action` only when the directive calls for a real Commons action",
            "get_send_link` is link generation",
            "commons://head",
        ):
            self.assertIn(marker, self.skill)

    def test_no_secrets_or_auth_requirements(self):
        self.assertIsNone(SECRET_RE.search(self.owned), SECRET_RE.search(self.owned))
        for forbidden in (
            "COMMONS_GITHUB_TOKEN",
            "XAI_API_KEY",
            "SLACK_BOT_TOKEN",
            "api_key=",
            "Authorization: Bearer",
        ):
            self.assertNotIn(forbidden, self.owned)
        self.assertIn("No credentials", self.skill)
        self.assertIn("Never print or store credentials", self.skill)

    def test_live_checker_defaults_to_read_only(self):
        args = self.checker.parse_args([])
        self.assertFalse(args.write_canary)
        self.assertEqual(args.canary_id, "")
        self.assertEqual(args.url, PUBLIC_MCP_URL)
        self.assertIn("action=\"store_true\"", self.checker_src)
        self.assertIn("default=False", self.checker_src)
        self.assertIn("Never use in unit tests or CI", self.checker_src)
        self.assertNotIn("write_canary=True", self.checker_src)
        self.assertIn("if args.write_canary", self.checker_src)

    def test_no_second_server_plugin_or_queue(self):
        for marker in (
            "Do not mint a second MCP core",
            "Do not stand up a second Vercel",
            "not a second Commons",
        ):
            self.assertTrue(marker in self.skill or marker in self.contract, marker)
        urls = set(re.findall(r"https://[^\s)`]+", self.owned))
        mcp_urls = {url.rstrip("/") for url in urls if url.rstrip("/").endswith("/mcp")}
        self.assertEqual(mcp_urls, {PUBLIC_MCP_URL})
        self.assertNotIn("new Vercel project", self.owned)

    def test_compare_detects_stale_production_without_network(self):
        source = {
            "name": "commons",
            "version": "1.2.0",
            "tools": list(self.checker.EXPECTED_SOURCE_TOOLS),
            "resources": ["commons://head", "commons://observatory"],
            "annotations": {
                "verify_durability": {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": True,
                }
            },
            "required": {"append_post": ["id", "body"]},
        }
        live = {
            "name": "commons",
            "version": "1.0.0",
            "tools": [
                "open_commons_composer",
                "fire_action",
                "append_post",
                "post_to_action_pad",
                "create_memory_board",
                "append_memory",
                "verify_durability",
                "get_send_link",
            ],
            "resources": ["commons://head"],
            "annotations": {
                "verify_durability": {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": True,
                }
            },
            "required": {"append_post": ["id", "body"]},
            "http": {"initialize": 200, "tools_list": 200, "GET": 200, "HEAD": 200},
            "session": None,
            "oauth_metadata": {
                "/.well-known/oauth-authorization-server": 404,
                "/.well-known/oauth-protected-resource": 404,
            },
        }
        drift = self.checker.compare(source, live)
        self.assertFalse(drift["parity"])
        self.assertEqual(drift["state"], "STALE_DEPLOYMENT")
        self.assertIn("append_model_post", drift["missing_tools"])
        self.assertIn("read_observatory", drift["missing_tools"])
        self.assertIn("route_grokcom_revenue_work", drift["missing_tools"])
        self.assertEqual(drift["version"]["source"], "1.2.0")
        self.assertEqual(drift["version"]["live"], "1.0.0")

    def test_compare_accepts_matching_source_and_live(self):
        tools = list(self.checker.EXPECTED_SOURCE_TOOLS)
        shared = {
            "name": "commons",
            "version": "1.2.0",
            "tools": tools,
            "resources": ["commons://head"],
            "annotations": {},
            "required": {},
        }
        live = {
            **shared,
            "http": {"initialize": 200, "tools_list": 200, "GET": 200},
            "session": None,
            "oauth_metadata": {
                "/.well-known/oauth-authorization-server": 404,
                "/.well-known/oauth-protected-resource": 404,
            },
        }
        drift = self.checker.compare(shared, live)
        self.assertTrue(drift["parity"])
        self.assertEqual(drift["state"], "LIVE_SOURCE_PARITY_VERIFIED")

    def test_main_does_not_write_when_flag_omitted(self):
        live = {
            "url": PUBLIC_MCP_URL,
            "name": "commons",
            "version": "1.2.0",
            "protocolVersion": "2025-03-26",
            "tools": list(self.checker.EXPECTED_SOURCE_TOOLS),
            "resources": [],
            "http": {"initialize": 200, "tools_list": 200, "GET": 200},
            "session": None,
            "oauth_metadata": {
                "/.well-known/oauth-authorization-server": 404,
                "/.well-known/oauth-protected-resource": 404,
            },
        }
        source = {
            "name": "commons",
            "version": "1.2.0",
            "tools": list(self.checker.EXPECTED_SOURCE_TOOLS),
            "resources": [],
            "imported": True,
            "annotations": {},
            "required": {},
        }
        with (
            mock.patch.object(self.checker, "load_source_surface", return_value=source),
            mock.patch.object(self.checker, "measure_live", return_value=live),
            mock.patch.object(self.checker, "write_canary") as write,
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            code = self.checker.main([])
        self.assertEqual(code, 0)
        write.assert_not_called()
        report = json.loads(stdout.getvalue())
        self.assertTrue(report["ok"])
        self.assertIsNone(report["write"])

    def test_write_canary_without_id_does_not_call_append(self):
        live = {
            "url": PUBLIC_MCP_URL,
            "name": "commons",
            "version": "1.0.0",
            "tools": ["append_post"],
            "resources": [],
            "http": {"initialize": 200, "tools_list": 200, "GET": 200},
            "session": None,
            "oauth_metadata": {
                "/.well-known/oauth-authorization-server": 404,
                "/.well-known/oauth-protected-resource": 404,
            },
        }
        source = {"name": "commons", "version": "1.2.0", "tools": ["append_post"], "resources": [], "imported": False}
        with (
            mock.patch.object(self.checker, "load_source_surface", return_value=source),
            mock.patch.object(self.checker, "measure_live", return_value=live),
            mock.patch.object(self.checker, "write_canary") as write,
            mock.patch("sys.stdout", new_callable=io.StringIO),
        ):
            code = self.checker.main(["--write-canary"])
        self.assertEqual(code, 1)
        write.assert_not_called()

    def test_load_source_surface_uses_canonical_adapter_when_importable(self):
        surface = self.checker.load_source_surface(str(ROOT))
        self.assertTrue(surface["imported"])
        self.assertEqual(surface["name"], "commons")
        self.assertEqual(surface["version"], "1.4.0")
        self.assertEqual(surface["tools"], list(self.checker.EXPECTED_SOURCE_TOOLS))
        self.assertIn("commons://head", surface["resources"])
        self.assertIn("read_observatory", surface["tools"])
        self.assertTrue(surface["annotations"]["verify_durability"]["readOnlyHint"])
        self.assertEqual(surface["required"]["append_post"], ["id", "body"])


if __name__ == "__main__":
    unittest.main()
