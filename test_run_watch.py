import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("host") / "run_watch.py"
SPEC = importlib.util.spec_from_file_location("run_watch", MODULE)
run_watch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_watch)

SHA = "a" * 40
RUN = 34567890123


def watch_doc(run_id=RUN, head=SHA):
    return {
        "schema": run_watch.WATCH_SCHEMA,
        "watches": [
            {
                "run_id": run_id,
                "head_sha": head,
                "on_success": {"kind": "integrate", "summary": "integrate exact head"},
                "on_failure": {"kind": "inspect", "summary": "inspect failing job"},
            }
        ],
    }


def observation(state, run_id=RUN, head=SHA):
    return {
        "schema": run_watch.OBSERVATION_SCHEMA,
        "runs": [{"run_id": run_id, "head_sha": head, "hosted": state}],
    }


class RunWatchTests(unittest.TestCase):
    def test_initialize_is_non_firing(self):
        state = run_watch.initialize(watch_doc(), observation("NOT_EXECUTED_QUEUED"))
        self.assertEqual(state["fired_event_ids"], [])
        self.assertEqual(state["runs"][0]["hosted"], "NOT_EXECUTED_QUEUED")

    def test_success_transition_fires_once(self):
        state = run_watch.initialize(watch_doc(), observation("NOT_EXECUTED_QUEUED"))
        result = run_watch.reduce_watch(watch_doc(), state, observation("SUCCESS"))
        self.assertEqual(len(result["events"]), 1)
        event = result["events"][0]
        self.assertEqual(event["from"], "NOT_EXECUTED_QUEUED")
        self.assertEqual(event["to"], "SUCCESS")
        self.assertEqual(event["action"]["kind"], "integrate")
        replay = run_watch.reduce_watch(watch_doc(), result["state"], observation("SUCCESS"))
        self.assertEqual(replay["events"], [])
        self.assertEqual(replay["state"], result["state"])

    def test_failure_transition_uses_failure_step(self):
        state = run_watch.initialize(watch_doc(), observation("RUNNING"))
        result = run_watch.reduce_watch(watch_doc(), state, observation("FAILED"))
        self.assertEqual(result["events"][0]["action"]["kind"], "inspect")

    def test_approval_gate_does_not_fire(self):
        state = run_watch.initialize(watch_doc(), observation("NOT_EXECUTED_QUEUED"))
        result = run_watch.reduce_watch(watch_doc(), state, observation("APPROVAL_GATED"))
        self.assertEqual(result["events"], [])
        self.assertEqual(result["state"]["runs"][0]["hosted"], "APPROVAL_GATED")

    def test_duplicate_watch_rejected(self):
        doc = watch_doc()
        doc["watches"].append(dict(doc["watches"][0]))
        with self.assertRaises(run_watch.WatchError):
            run_watch.parse_watches(doc)

    def test_bool_run_id_rejected(self):
        with self.assertRaises(run_watch.WatchError):
            run_watch.parse_watches(watch_doc(run_id=True))

    def test_head_mismatch_rejected(self):
        state = run_watch.initialize(watch_doc(), observation("RUNNING"))
        with self.assertRaises(run_watch.WatchError):
            run_watch.reduce_watch(watch_doc(), state, observation("SUCCESS", head="b" * 40))

    def test_unknown_hosted_state_rejected(self):
        with self.assertRaises(run_watch.WatchError):
            run_watch.initialize(watch_doc(), observation("QUEUED"))

    def test_terminal_state_regression_rejected(self):
        state = run_watch.initialize(watch_doc(), observation("SUCCESS"))
        with self.assertRaises(run_watch.WatchError):
            run_watch.reduce_watch(watch_doc(), state, observation("RUNNING"))

    def test_missing_watched_run_rejected(self):
        obs = {"schema": run_watch.OBSERVATION_SCHEMA, "runs": []}
        with self.assertRaises(run_watch.WatchError):
            run_watch.initialize(watch_doc(), obs)

    def test_duplicate_json_key_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            duplicate = Path(td) / "duplicate.json"
            duplicate.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaises(run_watch.WatchError):
                run_watch.load_json(duplicate)
            nonfinite = Path(td) / "nonfinite.json"
            nonfinite.write_text('{"x":NaN}', encoding="utf-8")
            with self.assertRaises(run_watch.WatchError):
                run_watch.load_json(nonfinite)

    def test_fired_event_inconsistent_with_nonterminal_state_rejected(self):
        state = run_watch.initialize(watch_doc(), observation("RUNNING"))
        event = run_watch.reduce_watch(watch_doc(), state, observation("FAILED"))["events"][0]
        state["fired_event_ids"] = [event["event_id"]]
        with self.assertRaises(run_watch.WatchError):
            run_watch.reduce_watch(watch_doc(), state, observation("FAILED"))


if __name__ == "__main__":
    unittest.main()
