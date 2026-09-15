from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from opportunities.naspo_sw1045_qualification_2026 import qualification_core as core
from opportunities.naspo_sw1045_qualification_2026 import qualification_tests_v1 as legacy

ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = Path(core.__file__).resolve()


def prime_ready_candidate():
    s, a, r = legacy.ready_packet()
    o = legacy.owner(team=False, cats=["CATEGORY_1_CONSULTING"])
    o["public_sector_references"] = [legacy.ref()]
    o["personnel_evidence"] = [legacy.staff()]
    o["mandatory_requirement_evidence"] = [legacy.mreq("CATEGORY_1_CONSULTING", "C1-EXP")]
    return s, a, r, o


def teaming_ready_candidate():
    s, a, r = legacy.ready_packet()
    o = legacy.owner(team=True, cats=[])
    o["prime_partner"] = {
        "status": "COMMITTED",
        "organization_ref": "partner:opaque",
        "commitment_evidence_ref": "evidence:commit",
        "commitment_evidence_sha256": legacy.H("6"),
        "public_sector_prime_track_record": ["evidence-bound public-sector prime record"],
        "cooperative_contract_admin_evidence_ref": "evidence:coop-admin",
        "cooperative_contract_admin_evidence_sha256": legacy.H("7"),
    }
    return s, a, r, o


def compile_via_fresh_cli(candidate, optimized: bool):
    s, a, r, o = candidate
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        paths = {}
        for name, obj in (("source", s), ("attachments", a), ("requirements", r), ("owner", o)):
            path = td_path / f"{name}.json"
            path.write_text(json.dumps(obj, sort_keys=True), encoding="utf-8")
            paths[name] = path
        cmd = [sys.executable]
        if optimized:
            cmd.append("-O")
        cmd.extend([
            str(CORE_PATH),
            "compile",
            "--source", str(paths["source"]),
            "--attachments", str(paths["attachments"]),
            "--requirements", str(paths["requirements"]),
            "--owner", str(paths["owner"]),
            "--trusted-now", legacy.NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ])
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=20)
        if proc.returncode not in {0, 3}:
            raise AssertionError(f"direct core CLI failed rc={proc.returncode}: {proc.stderr}")
        return json.loads(proc.stdout)


class DirectCoreTrustRootTests(unittest.TestCase):
    def test_direct_import_prime_candidate_cannot_mint_ready(self):
        s, a, r, o = prime_ready_candidate()
        self.assertFalse(core.packet_ready(s, a, r))
        rec = core.evaluate(s, a, r, o, trusted_now=legacy.NOW)
        self.assertFalse(rec["official_packet_ready"])
        self.assertEqual(rec["route_states"]["PRIME_CATEGORY_1_CONSULTING"], core.HOLD_PACKET)
        self.assertNotEqual(rec["state"], core.PRIME_READY)

    def test_direct_import_teaming_candidate_cannot_mint_ready(self):
        s, a, r, o = teaming_ready_candidate()
        self.assertFalse(core.packet_ready(s, a, r))
        rec = core.evaluate(s, a, r, o, trusted_now=legacy.NOW)
        self.assertFalse(rec["official_packet_ready"])
        self.assertEqual(rec["state"], core.TEAM_DRAFT)
        self.assertNotEqual(rec["state"], core.TEAM_READY)

    def test_fresh_direct_core_cli_prime_and_team_fail_closed_normal_and_optimized(self):
        for optimized in (False, True):
            with self.subTest(route="prime", optimized=optimized):
                rec = compile_via_fresh_cli(prime_ready_candidate(), optimized)
                self.assertFalse(rec["official_packet_ready"])
                self.assertNotEqual(rec["state"], core.PRIME_READY)
                self.assertNotIn(core.PRIME_READY, rec["route_states"].values())
            with self.subTest(route="teaming", optimized=optimized):
                rec = compile_via_fresh_cli(teaming_ready_candidate(), optimized)
                self.assertFalse(rec["official_packet_ready"])
                self.assertEqual(rec["state"], core.TEAM_DRAFT)
                self.assertNotEqual(rec["state"], core.TEAM_READY)

    def test_direct_core_verify_recomputes_fail_closed_generation(self):
        s, a, r, o = prime_ready_candidate()
        rec = core.evaluate(s, a, r, o, trusted_now=legacy.NOW)
        self.assertTrue(core.verify(s, a, r, o, rec, trusted_now=legacy.NOW))
        forged = json.loads(json.dumps(rec))
        forged["official_packet_ready"] = True
        forged["state"] = core.PRIME_READY
        forged["route_states"]["PRIME_CATEGORY_1_CONSULTING"] = core.PRIME_READY
        self.assertFalse(core.verify(s, a, r, o, forged, trusted_now=legacy.NOW))


if __name__ == "__main__":
    unittest.main()
