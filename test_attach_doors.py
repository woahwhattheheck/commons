#!/usr/bin/env python3
"""Dir 5 leftover: #compose-attach on every #say door, not only the landing.

Cite clamp-landing-attach-control-20260819-01, latch-dir5-image-attach-20260819-01.
Do not remint those. Did not PUT ingest.
"""
import hub_pages

form = hub_pages.say_form("TABLE", "ANNEX")
fails = []
if 'id="compose-attach"' not in form:
    fails.append("say_form missing #compose-attach")
if 'type="file"' not in form:
    fails.append("say_form missing file input")
if "attachments (optional)" not in form:
    fails.append("say_form missing attach label")
if hub_pages.CARRIER_V != hub_pages.ASSET_V:
    fails.append("CARRIER_V should follow ASSET_V so baked doors drop stale carrier cache")
if "carrier.js?v=%s" % hub_pages.CARRIER_V not in hub_pages.CARRIER_JS_TAG:
    fails.append("CARRIER_JS_TAG does not follow CARRIER_V")

src_hub = open("hub_pages.py", encoding="utf-8").read()
if "carrier.js?v=20260818j" in src_hub:
    fails.append("hub_pages still emits cached carrier.js?v=20260818j")

if fails:
    print("FAIL " + " | ".join(fails))
    raise SystemExit(1)
print("ok   say_form emits #compose-attach; carrier cache key follows CARRIER_V")
