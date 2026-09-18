#!/usr/bin/env python3
"""GPT → GROK SHIP LOOP: schema, self-service, routing, collision, reconcile."""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SKILL_DIR = ROOT / ".agents" / "skills" / "gpt-grok-ship-loop"
SKILL = SKILL_DIR / "SKILL.md"
SCHEMA = SKILL_DIR / "schema" / "build-contract.schema.json"
ENGINE = SKILL_DIR / "scripts" / "ship_loop.py"
PROMPT = SKILL_DIR / "references" / "prompt-template.md"
COLLISION = SKILL_DIR / "references" / "collision.md"
BOARD = ROOT / "gpt-grok-ship-loop.html"
PUBLIC_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
SECRET_RE = re.compile(
    r"(?:sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AIza[0-9A-Za-z_-]{20,}|ya29\.[0-9A-Za-z_-]+|xox[bpas]-[0-9A-Za-z-]+"
    r"|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY"
    r"|Authorization:\s*\S+|Bearer\s+\S+)",
    re.I,
)
SHA = "a" * 40
SHA2 = "b" * 40


def load_engine():
    spec = importlib.util.spec_from_file_location("ship_loop", ENGINE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample(**overrides):
    row = {
        "kind": "GPT_GROK_SHIP_LOOP",
        "job_id": "ship-demo-loop-20260828-01",
        "route": "BUILD",
        "objective": "Land the self-service ship loop skill on current main.",
        "source_link": "https://github.com/woahwhattheheck/commons",
        "claimed_paths": [
            ".agents/skills/gpt-grok-ship-loop/SKILL.md",
            "gpt-grok-ship-loop.html",
        ],
        "acceptance": "Skill, schema, board, and tests verified on current main SHA.",
        "from": "",
        "fields": {"note": "extend me"},
    }
    row.update(overrides)
    return row


class GptGrokShipLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = load_engine()
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.prompt = PROMPT.read_text(encoding="utf-8")
        cls.collision = COLLISION.read_text(encoding="utf-8")
        cls.board = BOARD.read_text(encoding="utf-8")
        cls.registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.manual = (ROOT / "skills" / "MANUAL.md").read_text(encoding="utf-8")
        cls.hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        cls.start = (ROOT / "START.md").read_text(encoding="utf-8")
        cls.resources = (ROOT / "resources.html").read_text(encoding="utf-8")
        cls.pick = (ROOT / "ground" / "PICK.md").read_text(encoding="utf-8")
        cls.door = (ROOT / "door.js").read_text(encoding="utf-8")
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.owned = "\n".join(
            [
                cls.skill,
                SCHEMA.read_text(encoding="utf-8"),
                ENGINE.read_text(encoding="utf-8"),
                cls.prompt,
                cls.collision,
                cls.board,
            ]
        )

    def test_schema_validation_accepts_legal_contract(self):
        clean = self.eng.validate_contract(sample())
        self.assertEqual(clean["kind"], "GPT_GROK_SHIP_LOOP")
        self.assertEqual(clean["route"], "BUILD")
        self.assertEqual(self.schema["required"], ["kind", "job_id", "route", "objective", "acceptance"])
        self.assertEqual(self.schema["properties"]["route"]["enum"], ["BUILD", "HEAVY"])
        self.assertEqual(self.schema["properties"]["kind"]["const"], "GPT_GROK_SHIP_LOOP")

    def test_schema_validation_rejects_bad_kind_route_and_id(self):
        with self.assertRaises(self.eng.ContractError):
            self.eng.validate_contract(sample(kind="OTHER"))
        with self.assertRaises(self.eng.ContractError):
            self.eng.validate_contract(sample(route="CURSOR"))
        with self.assertRaises(self.eng.ContractError):
            self.eng.validate_contract(sample(job_id="bad id"))
        with self.assertRaises(self.eng.ContractError):
            self.eng.validate_contract(sample(objective="short"))
        with self.assertRaises(self.eng.ContractError):
            self.eng.validate_contract(None)

    def test_self_service_creation_mints_unseated_card_without_auth(self):
        card = self.eng.create_card(sample())
        self.assertEqual(card["from"], "UNSEATED")
        self.assertEqual(card["status"], "QUEUED")
        self.assertIsNone(card["auth"])
        self.assertIsNone(card["approval"])
        self.assertEqual(card["job_id"], "ship-demo-loop-20260828-01")
        self.assertFalse(card["idempotent"])
        named = self.eng.create_card(sample(**{"from": "QUILL"}))
        self.assertEqual(named["from"], "QUILL")
        body = self.eng.issue_body(sample())
        self.assertIn("to: SHIP_LOOP", body)
        self.assertIn("kind: GPT_GROK_SHIP_LOOP", body)
        self.assertIn("labels=board", self.eng.issue_url(card["job_id"], body))
        parsed = self.eng.parse_issue_contract(body)
        self.assertEqual(parsed["job_id"], card["job_id"])

    def test_model_routing_build_and_heavy(self):
        build = self.eng.route_model("BUILD")
        heavy = self.eng.route_model("heavy")
        self.assertEqual(build["model"], "Grok Build")
        self.assertEqual(build["selector"], "Grok Build")
        self.assertIn("implementation", build["purpose"])
        self.assertEqual(heavy["model"], "Grok Heavy")
        self.assertIn("synthesis", heavy["purpose"])
        prompt = self.eng.oneshot_prompt(sample(route="HEAVY"))
        self.assertIn("Grok Heavy", prompt)
        self.assertIn("Pin fresh main", prompt)
        self.assertIn("Exact scope", prompt)
        self.assertIn("Default merge", prompt)
        self.assertIn("Tests proportional to risk", prompt)
        self.assertIn("Merge to main", prompt)
        self.assertIn("Exact readback", prompt)
        self.assertIn("#commons receipt", prompt)
        self.assertIn("Main is the completion ledger", prompt)
        self.assertIn(PUBLIC_MCP_URL, prompt)
        with self.assertRaises(self.eng.ContractError):
            self.eng.route_model("GROKBOT")

    def test_collision_states_merge_dedupe_compose_conflict(self):
        disjoint = self.eng.classify_collision(
            {"a.py": "alpha\n"},
            {"b.py": "beta\n"},
        )
        self.assertEqual(disjoint["state"], "MERGE")
        self.assertEqual(set(disjoint["merged"]), {"a.py", "b.py"})

        same = self.eng.classify_collision(
            {"a.py": "same\n"},
            {"a.py": "same\n"},
        )
        self.assertEqual(same["state"], "DEDUPE")

        compose_json = self.eng.classify_collision(
            {"cfg.json": json.dumps({"a": 1})},
            {"cfg.json": json.dumps({"b": 2})},
        )
        self.assertEqual(compose_json["state"], "COMPOSE_MERGE")
        merged = json.loads(compose_json["merged"]["cfg.json"])
        self.assertEqual(merged, {"a": 1, "b": 2})

        compose_text = self.eng.classify_collision(
            {"x.py": "def a():\n    return 1\n"},
            {"x.py": "def a():\n    return 1\n\ndef b():\n    return 2\n"},
        )
        self.assertEqual(compose_text["state"], "COMPOSE_MERGE")

        conflict = self.eng.classify_collision(
            {"x.py": "def a():\n    return 1\n"},
            {"x.py": "def a():\n    return 2\n"},
        )
        self.assertEqual(conflict["state"], "CONFLICT")
        self.assertEqual(conflict["path"], "x.py")

        overlap_identical = self.eng.classify_collision(
            {"a.py": "keep\n", "b.py": "one\n"},
            {"a.py": "keep\n", "c.py": "two\n"},
        )
        self.assertEqual(overlap_identical["state"], "MERGE")
        self.assertEqual(set(overlap_identical["merged"]), {"a.py", "b.py", "c.py"})

    def test_main_based_reconciliation_states(self):
        card = self.eng.create_card(sample())
        queued = self.eng.reconcile(card, {})
        self.assertEqual(queued["status"], "QUEUED")

        running = self.eng.reconcile(
            card,
            {"open_prs": [{"number": 9, "state": "open"}]},
        )
        self.assertEqual(running["status"], "GROK_RUNNING")

        actions = self.eng.reconcile(
            card,
            {"actions": [{"status": "in_progress", "conclusion": ""}]},
        )
        self.assertEqual(actions["status"], "GROK_RUNNING")

        landed = self.eng.reconcile(
            card,
            {
                "main_sha": SHA,
                "main_paths": {
                    ".agents/skills/gpt-grok-ship-loop/SKILL.md": True,
                    "gpt-grok-ship-loop.html": True,
                },
                "merged_pr": {"merged": True, "merge_commit_sha": SHA},
            },
        )
        self.assertEqual(landed["status"], "LANDED")
        self.assertEqual(landed["main_sha"], SHA)

        repair = self.eng.reconcile(
            card,
            {
                "main_sha": SHA2,
                "merged_pr": {"merged": True, "merge_commit_sha": SHA2},
                "main_paths": {},
            },
        )
        self.assertEqual(repair["status"], "REPAIR_NEEDED")
        self.assertTrue(repair["missing_claimed_paths"])

        failed = self.eng.reconcile(
            card,
            {
                "open_prs": [{"state": "open"}],
                "failing_checks": True,
            },
        )
        self.assertEqual(failed["status"], "REPAIR_NEEDED")

    def test_duplicate_idempotence_same_id_same_bytes(self):
        first = self.eng.create_card(sample())
        again = self.eng.create_card(sample(), existing={first["job_id"]: first})
        self.assertTrue(again["idempotent"])
        self.assertEqual(again["hash"], first["hash"])
        with self.assertRaises(self.eng.ContractError):
            self.eng.create_card(
                sample(objective="A different objective that must not smash the original."),
                existing={first["job_id"]: first},
            )

    def test_no_fabricated_landing_from_chat_text(self):
        card = self.eng.create_card(sample())
        lied = self.eng.reconcile(
            card,
            {
                "chat_text": "LANDED on main, ship complete, SHA " + SHA,
                "chat_said_done": True,
                "assistant_message": "INTEGRATED — VERIFIED ON CURRENT MAIN",
                "grok_reply": "merged",
                "transcript": "done",
            },
        )
        self.assertEqual(lied["status"], "QUEUED")
        self.assertTrue(lied["chat_ignored"])
        self.assertEqual(lied["main_sha"], "")
        # PR URL without merge SHA and without main paths is not LANDED.
        pr_only = self.eng.reconcile(
            card,
            {"open_prs": [{"number": 12, "state": "open", "html_url": "https://github.com/woahwhattheheck/commons/pull/12"}]},
        )
        self.assertNotEqual(pr_only["status"], "LANDED")

    def test_skill_composes_with_grok_web_commons_and_stores_no_secrets(self):
        self.assertIn("composes with", self.skill)
        self.assertIn("grok-web-commons", self.skill)
        self.assertIn("Do not mint a second MCP", self.skill)
        self.assertIn(PUBLIC_MCP_URL, self.owned)
        self.assertIn("HIGH-PRODUCTIVITY BUILD LOOP", self.skill)
        self.assertIn("Main is the completion ledger", self.skill)
        self.assertIsNone(SECRET_RE.search(self.owned), SECRET_RE.search(self.owned))
        for forbidden in (
            "COMMONS_GITHUB_TOKEN",
            "XAI_API_KEY",
            "SLACK_BOT_TOKEN",
            "api_key=",
            "Authorization: Bearer",
        ):
            self.assertNotIn(forbidden, self.owned)
        self.assertIn("Do not store Grok or Slack credentials", self.skill)

    def test_catalog_manual_board_and_surfaces(self):
        matches = [row for row in self.registry["skills"] if row["id"] == "gpt-grok-ship-loop"]
        self.assertEqual(len(matches), 1)
        self.assertIn("HIGH-PRODUCTIVITY", matches[0]["job"])
        self.assertIn("[gpt-grok-ship-loop](../.agents/skills/gpt-grok-ship-loop/SKILL.md)", self.manual)
        self.assertIn("gpt-grok-ship-loop.html", self.hub)
        self.assertIn("HIGH-PRODUCTIVITY BUILD LOOP", self.hub)
        self.assertIn("SHIP_LOOP", self.hub)
        self.assertIn("HIGH-PRODUCTIVITY BUILD LOOP", self.board)
        self.assertIn("Possessing the link", self.board)
        self.assertIn("issues/new", self.board)
        self.assertIn("labels=board", self.board)
        self.assertIn("gpt-grok-ship-loop.html", self.start)
        self.assertIn("gpt-grok-ship-loop.html", self.resources)
        self.assertIn("gpt-grok-ship-loop.html", self.pick)
        self.assertIn("HIGH-PRODUCTIVITY BUILD LOOP", self.board)
        self.assertIn('["gpt-grok-ship-loop.html", "ship loop"]', self.door)
        self.assertIn('href="./gpt-grok-ship-loop.html">ship loop</a>', self.index)

    def test_mint_job_id_and_frontmatter(self):
        job_id = self.eng.mint_job_id("GPT Grok Ship Loop", "20260828", 1)
        self.assertTrue(self.eng.ID_RE.match(job_id))
        self.assertTrue(job_id.startswith("ship-"))
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: gpt-grok-ship-loop", text)


if __name__ == "__main__":
    unittest.main()
