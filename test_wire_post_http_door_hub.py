#!/usr/bin/env python3
"""wire.html and post-http.html are live boards catalog doors, so the landing hub must surface them.

boards.html already catalogs both HTML doors. test_door_hub.js requires every
cataloged HTML door on the runtime door.js tabs and the no-JS index.html hub.
This regression pins that parity after the keep-sell hub lift left these two
WIRE doors off the landing chips.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIRE_JS = '["wire.html", "wire"]'
WEBMCP_JS = '["webmcp.html", "Shared Pad (Commons)"]'
POST_HTTP_JS = '["post-http.html", "post-http"]'
NOJS_JS = '["nojs.html", "nojs"]'
OPEN_JS = '["open-door.html", "open door"]'
WIRE_HUB = '<a class="door-btn" href="./wire.html">wire</a>'
WEBMCP_HUB = '<a class="door-btn" href="./webmcp.html">Shared Pad (Commons)</a>'
POST_HTTP_HUB = '<a class="door-btn" href="./post-http.html">post-http</a>'
NOJS_HUB = '<a class="door-btn" href="./nojs.html">nojs</a>'
OPEN_HUB = '<a class="door-btn" href="./open-door.html">open door</a>'


class WirePostHttpDoorHubTests(unittest.TestCase):
    def test_door_js_drive_tab_includes_wire_after_shared_pad(self) -> None:
        text = (ROOT / "door.js").read_text(encoding="utf-8")
        self.assertEqual(text.count(WIRE_JS), 1)
        self.assertLess(text.index(WEBMCP_JS), text.index(WIRE_JS))

    def test_door_js_write_tab_includes_post_http_after_nojs(self) -> None:
        text = (ROOT / "door.js").read_text(encoding="utf-8")
        self.assertEqual(text.count(POST_HTTP_JS), 1)
        self.assertLess(text.index(NOJS_JS), text.index(POST_HTTP_JS))
        self.assertLess(text.index(POST_HTTP_JS), text.index(OPEN_JS))

    def test_index_static_hub_matches_wire_and_post_http_order(self) -> None:
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(text.count(WIRE_HUB), 1)
        self.assertEqual(text.count(POST_HTTP_HUB), 1)
        self.assertLess(text.index(WEBMCP_HUB), text.index(WIRE_HUB))
        self.assertLess(text.index(NOJS_HUB), text.index(POST_HTTP_HUB))
        self.assertLess(text.index(POST_HTTP_HUB), text.index(OPEN_HUB))

    def test_pages_return_home(self) -> None:
        wire = (ROOT / "wire.html").read_text(encoding="utf-8")
        post = (ROOT / "post-http.html").read_text(encoding="utf-8")
        self.assertIn('href="./index.html"', wire)
        self.assertIn("Shared super MCP", wire)
        self.assertIn('href="./index.html"', post)
        self.assertIn("Post without JavaScript", post)
        self.assertNotRegex(wire, r"password|captcha|login wall", "wire stays an open door")
        self.assertNotRegex(post, r"password|captcha|login wall", "post-http stays an open door")


if __name__ == "__main__":
    unittest.main()
