from __future__ import annotations

import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "revenue" / "hive_photo_meal_journal"
sys.path.insert(0, str(APP))

from journal import DELETE_CONFIRMATION, JournalError, MealJournal  # noqa: E402
from server import make_handler  # noqa: E402

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def meal_args(**overrides):
    data = dict(
        operation_id="security-meal-1",
        meal_date="2026-09-14",
        title="Security meal",
        portion_note="",
        notes="",
        ingredients=["rice"],
        photo=None,
        photo_mime=None,
    )
    data.update(overrides)
    return data


class ModelShapeRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.j = MealJournal(Path(self.tmp.name) / "shape.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_rejects_string_ingredients_without_mutation(self):
        with self.assertRaises(JournalError):
            self.j.create_meal(**meal_args(ingredients="rice"))
        self.assertEqual(self.j.state()["meals"], [])

    def test_create_rejects_mapping_ingredients_without_mutation(self):
        with self.assertRaises(JournalError):
            self.j.create_meal(**meal_args(ingredients={"rice": True}))
        self.assertEqual(self.j.state()["meals"], [])

    def test_update_rejects_string_ingredients_without_version_change(self):
        created = self.j.create_meal(**meal_args())
        with self.assertRaises(JournalError):
            self.j.update_meal(
                operation_id="bad-update",
                meal_id=created["meal_id"],
                expected_version=1,
                meal_date="2026-09-14",
                title="bad",
                portion_note="",
                notes="",
                ingredients="rice",
            )
        meal = self.j.state()["meals"][0]
        self.assertEqual(meal["version"], 1)
        self.assertEqual(meal["ingredients"], ["rice"])

    def test_recipe_rejects_mapping_ingredients_without_mutation(self):
        with self.assertRaises(JournalError):
            self.j.save_recipe(
                operation_id="bad-recipe",
                name="bad",
                ingredients={"rice": True},
                notes="",
            )
        self.assertEqual(self.j.state()["recipes"], [])


class BrowserBoundaryRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.j = MealJournal(Path(self.tmp.name) / "http.sqlite3")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.j))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def request(self, path, *, payload=None, raw=None, method=None, content_type=None, headers=None):
        if payload is not None:
            raw = json.dumps(payload).encode("utf-8")
        request_headers = dict(headers or {})
        if raw is not None and content_type is not None:
            request_headers["Content-Type"] = content_type
        if method is None:
            method = "POST" if raw is not None else "GET"
        req = urllib.request.Request(
            self.base + path,
            data=raw,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_cross_site_text_plain_delete_all_cannot_execute(self):
        self.j.create_meal(**meal_args())
        raw = json.dumps({
            "operation_id": "attacker-delete",
            "confirmation": DELETE_CONFIRMATION,
        }).encode("utf-8")
        status, _, body = self.request(
            "/api/delete-all",
            raw=raw,
            content_type="text/plain",
            headers={"Origin": "https://attacker.example", "Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(status, 422)
        self.assertIn(b"Content-Type must be application/json", body)
        self.assertEqual(len(self.j.state()["meals"]), 1)

    def test_cross_site_application_json_is_rejected_too(self):
        self.j.create_meal(**meal_args())
        status, _, body = self.request(
            "/api/delete-all",
            payload={"operation_id": "attacker-json", "confirmation": DELETE_CONFIRMATION},
            content_type="application/json",
            headers={"Origin": "https://attacker.example", "Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(status, 422)
        self.assertIn(b"cross-origin browser mutation rejected", body)
        self.assertEqual(len(self.j.state()["meals"]), 1)

    def test_same_origin_json_mutation_remains_available(self):
        status, _, body = self.request(
            "/api/meal/create",
            payload={
                "operation_id": "same-origin-create",
                "meal_date": "2026-09-14",
                "title": "same origin",
                "portion_note": "",
                "notes": "",
                "ingredients": ["rice"],
            },
            content_type="application/json",
            headers={"Origin": self.base, "Sec-Fetch-Site": "same-origin"},
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(len(self.j.state()["meals"]), 1)

    def test_preflight_is_closed_without_cors_grant(self):
        status, headers, _ = self.request(
            "/api/delete-all",
            method="OPTIONS",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(status, 403)
        self.assertIsNone(headers.get("Access-Control-Allow-Origin"))

    def test_svg_photo_document_is_sandboxed(self):
        data_url = "data:image/svg+xml;base64," + base64.b64encode(SVG).decode("ascii")
        status, _, body = self.request(
            "/api/meal/create",
            payload={
                "operation_id": "svg-create",
                "meal_date": "2026-09-14",
                "title": "svg",
                "portion_note": "",
                "notes": "",
                "ingredients": ["rice"],
                "photo_data_url": data_url,
            },
            content_type="application/json",
        )
        self.assertEqual(status, 200, body)
        meal_id = json.loads(body)["meal_id"]
        status, headers, body = self.request(f"/photo/{meal_id}")
        self.assertEqual(status, 200)
        self.assertEqual(body, SVG)
        self.assertEqual(headers.get_content_type(), "image/svg+xml")
        csp = headers.get("Content-Security-Policy", "")
        self.assertIn("sandbox", csp)
        self.assertIn("default-src 'none'", csp)

    def test_http_string_ingredients_rejected_without_mutation(self):
        status, _, body = self.request(
            "/api/meal/create",
            payload={
                "operation_id": "bad-http-ingredients",
                "meal_date": "2026-09-14",
                "title": "bad",
                "portion_note": "",
                "notes": "",
                "ingredients": "rice",
            },
            content_type="application/json",
        )
        self.assertEqual(status, 422)
        self.assertIn(b"ingredients must be a list", body)
        self.assertEqual(self.j.state()["meals"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
