#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['revenue/hive/apparel-catalog-image-studio/index.html', 'revenue/hive/catering-workspace/index.html', 'revenue/hive/conversation-desk/index.html', 'revenue/hive/copy-production-desk/index.html', 'revenue/hive/creator-app-studio/planner.html', 'revenue/hive/creator-app-studio/studio.html', 'revenue/hive/creator-toolkit/index.html', 'revenue/hive/design-subscription-desk/index.html', 'revenue/hive/exhibitor-operations/index.html', 'revenue/hive/focused-storefront/index.html', 'revenue/hive/fulfillment-desk/index.html', 'revenue/hive/intake-crm-workflow/index.html', 'revenue/hive/newsletter-production/desk.html', 'revenue/hive/newsletter-production/fourfold/index.html', 'revenue/hive/newsletter-workshop/workshop.html', 'revenue/hive/niche-newsletter-publication/index.html', 'revenue/hive/office-workspace/index.html', 'revenue/hive/outbound-appointment-ops/index.html', 'revenue/hive/parts-sourcing-desk/index.html', 'revenue/hive/podcast-content-workspace/index.html', 'revenue/hive/prospect-workspace/persistence.html', 'revenue/hive/purchasing-paperwork-operator/desk.html', 'revenue/hive/rental-operations/index.html', 'revenue/hive/roughcut-editor/desk.html', 'revenue/hive/shop-operations/desk.html', 'revenue/hive/short-video-studio/index.html', 'revenue/hive/supplier-reorder-assistant/desk.html', 'revenue/hive/tenant-maintenance-desk/index.html', 'revenue/hive/voice-support-desk/index.html', 'revenue/hive_campaign_router/static/index.html', 'revenue/hive_community_events/chess.html', 'revenue/hive_community_events/index.html', 'revenue/website_people_email_book/fixture_seller.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepRevenueHtml20260909Test(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
