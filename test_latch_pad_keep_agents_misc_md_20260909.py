#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['revenue/OFFERING_FAMILIES.md', 'receipts/ink-pixel-presence-20260905-01.md', 'artifacts/urgent-expensify-99976-candidate-20260906-v2.md', 'inventory/commons-inventory-20260822-01.md', 'excerpts/README.md', 'audit/commons-integrated-builder-report-2026-08-26.md', 'repair-capsules/README.md', 'toolbench/README.md', 'harness_wake/README.md', 'architecture/PATHS.md', 'plugins/commons-grok-cloud/README.md', 'plugins/commons-grok-cloud/skills/commons-grok-cloud/SKILL.md', 'audit/readme-20260825/README.md', 'audit/readme-20260825/source_ledger.md', 'audit/readme-20260825/dissent.md', 'excerpts/20260821/GEMINI_NEST_TYPES_20260821.md', 'excerpts/20260821/GEMINI_PEER_DUMP_20260821.md', 'inventory/resources/README.md', 'claude_compute/packets/README.md', 'orchestration/jeffersonville/README.md', 'lotlens/samples/README.md', 'lotlens/samples/citric-forward.md', 'lotlens/samples/citric-forward-assumed.md', 'lotlens/samples/ship3-backward.md', 'compress/muhc_v1/README.md', 'compress/ringdelta/queue/README.md', 'builds/records/open-door-negative-assertions/OPEN-DOOR-NEGATIVE-ASSERTIONS.md', '.agents/skills/slash-commands/SKILL.md', '.agents/skills/record-append/SKILL.md', '.agents/skills/take-a-line/SKILL.md', '.agents/skills/post/SKILL.md', '.agents/skills/surfaces/SKILL.md', '.agents/skills/sprint-integration/SKILL.md', '.agents/skills/pfc-spec/SKILL.md', '.agents/skills/head-truth/SKILL.md', '.agents/skills/new-branch-and-pr/SKILL.md', '.agents/skills/muhl-hook/SKILL.md', '.agents/skills/listing-registry/SKILL.md', '.agents/skills/write-roads/SKILL.md', '.agents/skills/harness-wake/SKILL.md', '.agents/skills/ping-wake/SKILL.md', 'contributions/rustchain-bounties-100-onboarding/README.md', '.github/ISSUE_TEMPLATE/board.md', '.github/ISSUE_TEMPLATE/commons-post.md', 'revenue/at_grok_cmdp_evidence/README.md', 'revenue/at_grok_cmdp_evidence/SCHEMA_MATRIX.md', 'revenue/bsk_multilab_accession_parity/README.md', 'revenue/bounties/sol-bottube-2215-20260908.md', 'revenue/csplabs_express_capacity_assurance/receipt.md', 'revenue/plant_downtime_handoff/receipt.md', 'revenue/production_survival/README.md', 'revenue/production_survival/crm.md', 'revenue/production_survival/acceptance_contract.md', 'revenue/production_survival/claims.md', 'revenue/production_survival/INTAKE.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class T(unittest.TestCase):
    def test_all(self):
        for name in PAGES:
            with self.subTest(page=name):
                text=(ROOT/name).read_text(encoding='utf-8')
                for n in REQUIRED: self.assertIn(n, text)
if __name__ == '__main__':
    unittest.main()
