"""Run the shipped knight packs through Lantern's real SQLite and HTTP consumer."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

import app as lantern
import knight_pack as pack

ROOT = Path(__file__).resolve().parent


def rows(week=1, count=12):
    return pack.adapt(pack.generate(f"community-knight-week-{week}", count),
                      answer_key="correct", explanation_key=None)


class LanternKnightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "events.sqlite3"
        self.now = 1000.0
        self.store = lantern.Store(self.database, clock=lambda: self.now)

    def payload(self, questions=None, opens=900):
        return {"title": "Knight challenge", "room": "Community",
                "opens": opens, "ends": 2000,
                "questions": rows() if questions is None else questions}

    def test_shipped_files_are_exact_ready_to_import_packs(self):
        for week in (1, 2):
            with self.subTest(week=week):
                data = json.loads((ROOT / f"knight-week-{week}.json").read_text(encoding="utf-8"))
                self.assertEqual(data, rows(week))
                self.assertEqual(set(data[0]), {"prompt", "choices", "correct"})
                event = self.store.create(self.payload(data))["id"]
                self.assertEqual(self.store.state(event)["question_count"], 12)

    def test_generic_answer_key_needs_the_explicit_consumer_mapping(self):
        with self.assertRaises(lantern.Problem) as error:
            self.store.create(self.payload(pack.adapt(pack.generate())))
        self.assertEqual(error.exception.status, 422)
        self.assertEqual(self.store.listing(), [])

    def test_schedule_and_answer_visibility_keep_existing_semantics(self):
        event = self.store.create(self.payload(opens=1100))["id"]
        self.assertEqual(self.store.state(event)["questions"], [])
        self.now = 1100
        current = self.store.state(event)
        self.assertEqual(current["phase"], "open")
        self.assertEqual(len(current["questions"]), 12)
        self.assertTrue(all("correct" not in item and "explanation" not in item
                            for item in current["questions"]))
        self.store.finish(event)
        self.assertEqual([q["correct"] for q in self.store.state(event)["questions"]],
                         [q["correct"] for q in rows()])

    def test_both_packs_score_and_reconnect_from_persistent_storage(self):
        for week in (1, 2):
            questions = rows(week)
            event = self.store.create(self.payload(questions))["id"]
            member = self.store.join(event, {"name": "Puzzle player"})["id"]
            for index, item in enumerate(questions):
                self.store.answer(event, {"member_id": member, "question": index, "choice": item["correct"]})
            self.store.finish(event)
            reopened = lantern.Store(self.database, clock=lambda: self.now)
            self.assertEqual(reopened.join(event, {"member_id": member})["id"], member)
            state = reopened.state(event, member)
            self.assertEqual(len(state["answers"]), 12)
            self.assertEqual(state["leaderboard"][0]["points"], 1200)
            self.assertEqual(state["leaderboard"][0]["rank"], 1)

    def test_first_answer_and_retries_do_not_duplicate_points(self):
        questions = rows()
        event = self.store.create(self.payload(questions))["id"]
        member = self.store.join(event, {"name": "Retry player"})["id"]
        answer = {"member_id": member, "question": 0, "choice": questions[0]["correct"]}
        self.assertFalse(self.store.answer(event, answer)["replayed"])
        self.assertTrue(self.store.answer(event, answer)["replayed"])
        with self.assertRaises(lantern.Problem) as error:
            self.store.answer(event, dict(answer, choice=(answer["choice"] + 1) % 4))
        self.assertEqual(error.exception.status, 409)
        self.store.answer(event, {"member_id": member, "question": 1,
                                  "choice": (questions[1]["correct"] + 1) % 4})
        self.store.finish(event)
        state = self.store.state(event, member)
        self.assertEqual(state["leaderboard"][0]["points"], 100)
        self.assertEqual(state["leaderboard"][0]["answered"], 2)

    def test_documented_cli_output_imports_without_manual_edits(self):
        output = Path(self.temp.name) / "new-week.json"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "knight_pack.py"),
                                 "--seed", "community-knight-week-3", "--count", "12",
                                 "--answer-key", "correct", "--omit-explanation",
                                 "--output", str(output)], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        event = self.store.create(self.payload(json.loads(output.read_text(encoding="utf-8"))))["id"]
        self.assertEqual(self.store.state(event)["question_count"], 12)

    def test_consumer_question_limit_is_distinct_from_generator_limit(self):
        self.assertEqual(len(pack.generate(count=64)), 64)
        event = self.store.create(self.payload(rows(count=50)))["id"]
        self.assertEqual(self.store.state(event)["question_count"], 50)
        with self.assertRaises(lantern.Problem) as error:
            self.store.create(self.payload(rows(count=51)))
        self.assertEqual(error.exception.status, 422)

    def test_actual_http_create_join_answer_finish_and_reconnect(self):
        server = lantern.ThreadingHTTPServer(("127.0.0.1", 0), lantern.make_handler(self.store))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()

        def request(path, payload=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            try:
                data = None if payload is None else json.dumps(payload).encode("utf-8")
                connection.request("GET" if payload is None else "POST", path, body=data,
                                   headers={} if data is None else {"Content-Type": "application/json"})
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        try:
            questions = json.loads((ROOT / "knight-week-1.json").read_text(encoding="utf-8"))
            status, event = request("/api/events", self.payload(questions))
            self.assertEqual(status, 201)
            prefix = "/api/events/" + event["id"]
            status, member = request(prefix + "/join", {"name": "HTTP player"})
            self.assertEqual(status, 200)
            for index, item in enumerate(questions):
                payload = {"member_id": member["id"], "question": index, "choice": item["correct"]}
                self.assertEqual(request(prefix + "/answers", payload)[0], 200)
                self.assertTrue(request(prefix + "/answers", payload)[1]["replayed"])
            self.assertEqual(request(prefix + "/finish", {})[0], 200)
            self.assertEqual(request(prefix + "/join", {"member_id": member["id"]})[1], member)
            status, state = request(prefix + "?member=" + member["id"])
            self.assertEqual(status, 200)
            self.assertEqual(state["phase"], "finished")
            self.assertEqual(state["leaderboard"][0]["points"], 1200)
            self.assertEqual(state["leaderboard"][0]["answered"], 12)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
            self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
