#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['players/CODEX_SOL-amber-hour.html', 'players/CODEX_SOL.html', 'titan/titan.html', 'titan/titan_live.html', 'packs/thanks.html', 'packs/waitlist.html', 'packs/tjlabs-terms.html', 'ground/index.html', 'lotlens/app.html', 'd/2026-08-24.html', 'd/2026-08-20.html', 'd/2026-09-09.html', 'd/2026-08-29.html', 'd/"2026-09-0.html', 'd/2026-08-28.html', 'd/2026-08-22.html', 'd/2026-08-19.html', 'd/2026-08-25.html', 'd/2026-09-07.html', 'd/2026-09-01.html', 'd/2026-09-02.html', 'd/2026-08-21.html', 'd/2026-08-23.html', 'd/2026-09-04.html', 'd/2026-08-26.html', 'd/2026-09-03.html', 'd/2026-09-08.html', 'd/2026-08-18.html', 'd/2026-08-27.html', 'd/2026-08-31.html', 'd/2026-08-30.html', 'd/undated.html', 'd/2026-09-06.html', 'door/index.html', 'discord/plugin.html', 'embed/demo.html', 'repair-capsules/index.html', 'r/kite-github-pages-probe-20260817-01.html', 'r/commons-agent-use-20260817-01.html', 'slack/plugin.html', 'host/counterfactual_lab/index.html', 'sites/bugfix/index.html', 'packs/sidewalk-signal-web-desk-20260902-01/offer.html', 'packs/sidewalk-signal-web-desk-20260902-01/index.html', 'packs/desk-website-service-20260902-01/door.html', 'packs/curbline-weekend-yard-help-20260902-01/index.html', 'packs/lotribbon-greetings-20260902-01/index.html', 'titan/builds/muhl_display.html', 'cli/tests/fixtures/action.html', 'integrations/command_center/web/index.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepDatePacks20260909Test(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
