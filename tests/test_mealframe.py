from __future__ import annotations

import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "revenue" / "hive_photo_meal_journal"
sys.path.insert(0, str(APP))

from journal import (  # noqa: E402
    ConflictError,
    DELETE_CONFIRMATION,
    JournalError,
    MAX_PHOTO_BYTES,
    MealJournal,
    NotFoundError,
)
from server import load_demo, make_handler  # noqa: E402

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="12">meal</text></svg>'

def meal_args(**overrides):
    data = dict(
        operation_id="meal-op-1",
        meal_date="2026-09-14",
        title="Tomato toast",
        portion_note="two slices",
        notes="user-edited note",
        ingredients=["toast", "tomato", "basil"],
        photo=SVG,
        photo_mime="image/svg+xml",
    )
    data.update(overrides)
    return data

class JournalModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "meal.sqlite3"
        self.j = MealJournal(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_state_and_exact_photo_round_trip(self):
        result = self.j.create_meal(**meal_args())
        self.assertEqual(result["version"], 1)
        state = self.j.state()
        self.assertEqual(len(state["meals"]), 1)
        meal = state["meals"][0]
        self.assertEqual(meal["ingredients"], ["toast", "tomato", "basil"])
        self.assertNotIn("photo_bytes", meal)
        photo, mime, sha = self.j.photo(meal["id"])
        self.assertEqual(photo, SVG)
        self.assertEqual(mime, "image/svg+xml")
        self.assertEqual(sha, meal["photo_sha256"])

    def test_same_operation_retry_is_idempotent(self):
        a = self.j.create_meal(**meal_args())
        b = self.j.create_meal(**meal_args())
        self.assertEqual(a, b)
        self.assertEqual(len(self.j.state()["meals"]), 1)

    def test_operation_id_payload_collision_rejected(self):
        self.j.create_meal(**meal_args())
        with self.assertRaises(ConflictError):
            self.j.create_meal(**meal_args(title="different"))

    def test_update_uses_optimistic_version_and_preserves_photo(self):
        created = self.j.create_meal(**meal_args())
        updated = self.j.update_meal(
            operation_id="update-1",
            meal_id=created["meal_id"],
            expected_version=1,
            meal_date="2026-09-15",
            title="Edited toast",
            portion_note="one plate",
            notes="edited",
            ingredients=["toast", "tomato"],
        )
        self.assertEqual(updated["version"], 2)
        state = self.j.state()["meals"][0]
        self.assertEqual(state["title"], "Edited toast")
        self.assertEqual(state["ingredients"], ["toast", "tomato"])
        self.assertEqual(self.j.photo(created["meal_id"])[0], SVG)

    def test_stale_meal_update_rejected(self):
        created = self.j.create_meal(**meal_args())
        self.j.update_meal(
            operation_id="update-ok", meal_id=created["meal_id"], expected_version=1,
            meal_date="2026-09-14", title="v2", portion_note="", notes="", ingredients=[],
        )
        with self.assertRaises(ConflictError):
            self.j.update_meal(
                operation_id="update-stale", meal_id=created["meal_id"], expected_version=1,
                meal_date="2026-09-14", title="stale", portion_note="", notes="", ingredients=[],
            )

    def test_delete_meal_removes_photo(self):
        created = self.j.create_meal(**meal_args())
        out = self.j.delete_meal(operation_id="delete-1", meal_id=created["meal_id"], expected_version=1)
        self.assertEqual(out["deleted_meal_id"], created["meal_id"])
        self.assertEqual(self.j.state()["meals"], [])
        with self.assertRaises(NotFoundError):
            self.j.photo(created["meal_id"])

    def test_delete_meal_stale_version_rejected(self):
        created = self.j.create_meal(**meal_args())
        self.j.update_meal(
            operation_id="u2", meal_id=created["meal_id"], expected_version=1,
            meal_date="2026-09-14", title="v2", portion_note="", notes="", ingredients=[],
        )
        with self.assertRaises(ConflictError):
            self.j.delete_meal(operation_id="d-stale", meal_id=created["meal_id"], expected_version=1)

    def test_delete_all_requires_exact_confirmation(self):
        self.j.create_meal(**meal_args())
        with self.assertRaises(JournalError):
            self.j.delete_all(operation_id="wipe-no", confirmation="delete")
        self.assertEqual(len(self.j.state()["meals"]), 1)

    def test_delete_all_clears_meals_photos_and_recipes(self):
        self.j.create_meal(**meal_args())
        self.j.save_recipe(operation_id="recipe-1", name="Toast", ingredients=["toast"], notes="")
        out = self.j.delete_all(operation_id="wipe", confirmation=DELETE_CONFIRMATION)
        self.assertEqual(out, {"deleted_meals": 1, "deleted_photos": 1, "deleted_recipes": 1})
        self.assertEqual(self.j.state()["meals"], [])
        self.assertEqual(self.j.state()["recipes"], [])

    def test_recipe_save_and_recipe_based_suggestions(self):
        self.j.save_recipe(
            operation_id="recipe-1", name="Tomato toast",
            ingredients=["toast", "tomato", "basil"], notes="saved by user",
        )
        suggestions = self.j.suggestions("tomato toast")
        values = {x["ingredient"]: x for x in suggestions}
        self.assertIn("tomato", values)
        self.assertIn("recipe", values["tomato"]["source"])
        self.assertIn("not inferred from photo", values["tomato"]["basis"])

    def test_recipe_update_and_stale_guard(self):
        created = self.j.save_recipe(operation_id="r1", name="A", ingredients=["x"], notes="")
        updated = self.j.save_recipe(
            operation_id="r2", recipe_id=created["recipe_id"], expected_version=1,
            name="A2", ingredients=["x", "y"], notes="edited",
        )
        self.assertEqual(updated["version"], 2)
        with self.assertRaises(ConflictError):
            self.j.save_recipe(
                operation_id="r3", recipe_id=created["recipe_id"], expected_version=1,
                name="bad", ingredients=["x"], notes="",
            )

    def test_history_based_suggestions_are_labeled(self):
        self.j.create_meal(**meal_args(photo=None, photo_mime=None))
        suggestions = self.j.suggestions("")
        tomato = next(x for x in suggestions if x["ingredient"] == "tomato")
        self.assertIn("history", tomato["source"])
        self.assertEqual(tomato["basis"], "saved recipe/history only; not inferred from photo")

    def test_state_explicitly_disclaims_nutrition_and_photo_recognition(self):
        state = self.j.state()
        self.assertFalse(state["nutrition_inference"])
        self.assertFalse(state["photo_recognition"])
        self.assertEqual(state["privacy"], "local_instance_only")

    def test_week_json_is_portable_and_omits_photo_bytes(self):
        self.j.create_meal(**meal_args())
        data = json.loads(self.j.export_week_json("2026-09-14"))
        self.assertEqual(len(data["meals"]), 1)
        self.assertTrue(data["meals"][0]["photo_included"])
        self.assertNotIn("photo_bytes", json.dumps(data))
        self.assertFalse(data["nutrition_estimates_included"])
        self.assertFalse(data["photo_recognition_used"])

    def test_week_must_start_monday(self):
        with self.assertRaises(JournalError):
            self.j.export_week_json("2026-09-15")

    def test_week_html_escapes_user_text(self):
        self.j.create_meal(**meal_args(title="<script>alert(1)</script>", photo=None, photo_mime=None))
        text = self.j.export_week_html("2026-09-14").decode()
        self.assertNotIn("<script>alert(1)</script>", text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", text)
        self.assertIn("No nutrition, calorie, medical", text)

    def test_unsupported_mime_rejected(self):
        with self.assertRaises(JournalError):
            self.j.create_meal(**meal_args(photo=b"abc", photo_mime="text/plain"))

    def test_oversize_photo_rejected(self):
        with self.assertRaises(JournalError):
            self.j.create_meal(**meal_args(photo=b"x" * (MAX_PHOTO_BYTES + 1), photo_mime="image/png"))

    def test_duplicate_ingredients_rejected_case_insensitive(self):
        with self.assertRaises(JournalError):
            self.j.create_meal(**meal_args(ingredients=["Tomato", "tomato"]))

    def test_invalid_calendar_date_rejected(self):
        with self.assertRaises(JournalError):
            self.j.create_meal(**meal_args(meal_date="2026-02-30"))

    def test_reopen_preserves_state_and_photo(self):
        created = self.j.create_meal(**meal_args())
        other = MealJournal(self.db)
        self.assertEqual(other.state()["meals"][0]["title"], "Tomato toast")
        self.assertEqual(other.photo(created["meal_id"])[0], SVG)

    def test_concurrent_same_operation_creates_one_meal(self):
        results, errors = [], []
        def worker():
            try:
                results.append(self.j.create_meal(**meal_args()))
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 6)
        self.assertTrue(all(x == results[0] for x in results))
        self.assertEqual(len(self.j.state()["meals"]), 1)

    def test_concurrent_distinct_updates_same_version_allow_one(self):
        created = self.j.create_meal(**meal_args(photo=None, photo_mime=None))
        successes, conflicts = [], []
        def worker(n):
            try:
                successes.append(self.j.update_meal(
                    operation_id=f"concurrent-{n}", meal_id=created["meal_id"], expected_version=1,
                    meal_date="2026-09-14", title=f"title-{n}", portion_note="", notes="", ingredients=[],
                ))
            except ConflictError:
                conflicts.append(n)
        a = threading.Thread(target=worker, args=(1,))
        b = threading.Thread(target=worker, args=(2,))
        a.start(); b.start(); a.join(); b.join()
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(self.j.state()["meals"][0]["version"], 2)

    def test_demo_is_idempotent(self):
        load_demo(self.j)
        load_demo(self.j)
        state = self.j.state()
        self.assertEqual(len(state["meals"]), 1)
        self.assertEqual(len(state["recipes"]), 1)
        self.assertIn("Self-authored fictional demo entry", state["meals"][0]["notes"])

class HttpTests(unittest.TestCase):
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

    def request(self, path, payload=None, raw=None):
        if payload is not None:
            raw = json.dumps(payload).encode()
        headers = {}
        method = "GET"
        if raw is not None:
            method = "POST"
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=raw, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, exc.read()

    def test_home_and_initial_state(self):
        status, _, body = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"MealFrame", body)
        status, _, body = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["meals"], [])

    def test_http_photo_create_and_exact_get(self):
        data_url = "data:image/svg+xml;base64," + base64.b64encode(SVG).decode()
        payload = {
            "operation_id": "http-create", "meal_date": "2026-09-14", "title": "HTTP meal",
            "portion_note": "one bowl", "notes": "", "ingredients": ["rice"], "photo_data_url": data_url,
        }
        status, _, body = self.request("/api/meal/create", payload)
        self.assertEqual(status, 200)
        meal_id = json.loads(body)["meal_id"]
        status, headers, body = self.request(f"/photo/{meal_id}")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get_content_type(), "image/svg+xml")
        self.assertEqual(body, SVG)
        self.assertTrue(headers["ETag"].startswith('"sha256-'))

    def test_http_duplicate_json_key_rejected(self):
        raw = b'{"operation_id":"a","operation_id":"b"}'
        status, _, body = self.request("/api/meal/create", raw=raw)
        self.assertEqual(status, 422)
        self.assertIn(b"duplicate JSON key", body)

    def test_http_suggestions_and_exports(self):
        self.j.save_recipe(operation_id="r-http", name="Rice bowl", ingredients=["rice", "beans"], notes="")
        status, _, body = self.request("/api/suggestions?title=Rice%20bowl")
        self.assertEqual(status, 200)
        self.assertIn("rice", [x["ingredient"] for x in json.loads(body)["suggestions"]])
        self.j.create_meal(**meal_args(operation_id="m-http", photo=None, photo_mime=None))
        status, headers, body = self.request("/api/export?week=2026-09-14&format=json")
        self.assertEqual(status, 200)
        self.assertIn("attachment;", headers["Content-Disposition"])
        self.assertEqual(len(json.loads(body)["meals"]), 1)
        status, _, body = self.request("/api/export?week=2026-09-14&format=html")
        self.assertEqual(status, 200)
        self.assertIn(b"MealFrame weekly journal", body)

    def test_http_stale_update_is_409(self):
        created = self.j.create_meal(**meal_args(operation_id="http-base", photo=None, photo_mime=None))
        payload = {
            "operation_id": "http-u1", "meal_id": created["meal_id"], "expected_version": 1,
            "meal_date": "2026-09-14", "title": "v2", "portion_note": "", "notes": "", "ingredients": [],
        }
        self.assertEqual(self.request("/api/meal/update", payload)[0], 200)
        payload["operation_id"] = "http-u2"
        payload["title"] = "stale"
        self.assertEqual(self.request("/api/meal/update", payload)[0], 409)

    def test_http_delete_all_removes_photo_route(self):
        data_url = "data:image/svg+xml;base64," + base64.b64encode(SVG).decode()
        status, _, body = self.request("/api/meal/create", {
            "operation_id": "to-delete", "meal_date": "2026-09-14", "title": "Delete",
            "portion_note": "", "notes": "", "ingredients": [], "photo_data_url": data_url,
        })
        meal_id = json.loads(body)["meal_id"]
        status, _, _ = self.request("/api/delete-all", {
            "operation_id": "wipe-http", "confirmation": DELETE_CONFIRMATION,
        })
        self.assertEqual(status, 200)
        self.assertEqual(self.request(f"/photo/{meal_id}")[0], 404)

    def test_unknown_route_is_404(self):
        self.assertEqual(self.request("/not-a-route")[0], 404)

if __name__ == "__main__":
    unittest.main(verbosity=2)
