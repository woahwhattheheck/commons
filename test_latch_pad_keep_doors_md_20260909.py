#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['protocol/README.md', 'protocol/PROTOCOL.md', 'door/README.md', 'embed/README.md', 'ping/chatgpt.md', 'ping/adapters.md', 'ping/claude.md', 'ping/action.md', 'mesh/PROTOCOL-v1.md', 'mesh/d/README.md', 'peer_wake/README.md', 'cli/README.md', 'backups/README.md', 'backups/HEAD_IDENTITY.md', 'experience/README.md', 'experience/wiki/index.md', 'experience/wiki/patterns/publish-discovery-before-interaction.md', 'trust_cache/README.md', 'trust_cache/CANARY.md', 'titan/README.md', 'titan/INDEX.md', 'features/README.md', 'skills/MANUAL.md', 'charttrace/README.md', 'android/README.md', 'embassy/visitors.md', 'dest/LIVE_MOUTHS.md', 'dest/DEST_IS_THE_MACHINE.md', 'dest/MNO_DS_17_table_mail.md', 'dests/INGRESS.md', 'dests/TOKENIZER_MAP.md', 'wake_jobs/README.md', 'evidence/README.md', 'evidence/archive_misdescribed/REUNIFICATION_INVENTORY.md', 'evidence/archive_misdescribed/CONFIRMED_PROOF_ON_DEVICE.md', 'evidence/archive_misdescribed/MODEL_COMPUTER.md', 'evidence/archive_misdescribed/SPECTROMETER_FINDINGS.md', 'evidence/archive_misdescribed/SDC_ADDRESSING.md', 'evidence/archive_misdescribed/SDC_FORWARD_PASS.md', 'evidence/archive_misdescribed/PARKED_FEATURES.md', 'evidence/archive_misdescribed/NOT_BUILT.md', 'evidence/archive_misdescribed/MODEL_DIALECTS.md', 'evidence/archive_misdescribed/SCOREBOARD_SPEC.md', 'evidence/archive_misdescribed/ZERO_RAM_PROOF_RUN_BY_CLAUDE.md', 'evidence/archive_misdescribed/BASE_MODEL_SUBSTRATE.md', 'lotlens/README.md', 'lotlens/IMPORT_SPEC.md', 'claude_compute/README.md', 'mirror-capsule/OPEN.md', 'sales-sample/FREE-SAMPLE-SALES-INSERT.md', 'patent-products/SALES-INSERT.md', 'titan-hands-sample/SALES-INSERT.md', 'data/whitebox_pfc_mix.md', 'data/MUHL_WHITEBOX_TREE_MAP.md']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class T(unittest.TestCase):
    def test_all(self):
        for name in PAGES:
            with self.subTest(page=name):
                text=(ROOT/name).read_text(encoding='utf-8')
                for n in REQUIRED: self.assertIn(n, text)
if __name__ == '__main__':
    unittest.main()
