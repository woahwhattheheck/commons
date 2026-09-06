"""Work-map metadata follows each task's ordered protocol events."""
from __future__ import annotations

from copy import deepcopy
import unittest

from protocol.projector import project

NOW = "2026-09-06T23:20:00Z"
START = "2026-09-06T23:00:00Z"
LATER = "2026-09-06T23:01:00Z"
LATEST = "2026-09-06T23:02:00Z"


def event(eid: str, kind: str = "START", ts: str = START, **fields: object) -> dict:
    return {
        "event_id": eid, "kind": kind, "ts": ts,
        "session_id": "work-map-session", "task_id": "work-map-task", **fields,
    }


def task_for(events: list[dict], **options: object) -> dict:
    return project(events, now=NOW, **options)["work_map"][0]


class WorkMapUpdatesTests(unittest.TestCase):
    def test_latest_event_metadata_uses_chronology_not_input_order(self):
        first = event("work-first", checkpoint="initial checkpoint", head_sha="1" * 40)
        later = event("work-later", "CHECKPOINT", LATER,
                      checkpoint="latest checkpoint", head_sha="2" * 40)
        task = task_for([later, first])
        self.assertEqual(task["checkpoint"], "latest checkpoint")
        self.assertEqual(task["last_kind"], "CHECKPOINT")
        self.assertEqual(task["last_ts"], LATER)
        self.assertEqual(task["head_sha"], "2" * 40)

    def test_blocked_task_includes_the_current_reason(self):
        reason = {"type": "external_authority", "detail": "waiting for maintainer"}
        task = task_for([event("work-start"), event("work-blocked", "BLOCKED", LATER,
                        blocker=reason, checkpoint="review packet submitted")])
        self.assertEqual(task["state"], "BLOCKED")
        self.assertEqual(task["blocker"], reason)
        self.assertEqual(task["checkpoint"], "review packet submitted")
        self.assertEqual(task["last_kind"], "BLOCKED")
        self.assertEqual(task["last_ts"], LATER)

    def test_working_events_clear_the_previous_blocker(self):
        blocked = event("work-block-first", "BLOCKED", blocker={
            "type": "external_authority", "detail": "old blocker"})
        for kind in ("START", "HEARTBEAT", "CHECKPOINT", "HANDOFF"):
            with self.subTest(kind=kind):
                task = task_for([blocked, event("work-resume", kind, LATER)])
                self.assertEqual(task["state"], "WORKING")
                self.assertEqual(task["blocker"], {"type": "UNKNOWN", "detail": "UNKNOWN"})
                self.assertEqual(task["expected_next"], "CHECKPOINT or HEARTBEAT")

    def test_latest_head_removes_obsolete_branch_divergence(self):
        snap = project([
            event("work-old-head", head_sha="1" * 40),
            event("work-current-head", "CHECKPOINT", LATER, head_sha="2" * 40),
        ], now=NOW, head_sha="2" * 40)
        self.assertEqual(snap["work_map"][0]["head_sha"], "2" * 40)
        self.assertFalse(any(row["kind"] == "BRANCH_DIVERGENCE" for row in snap["collisions"]))

    def test_sparse_heartbeat_preserves_latest_known_fields(self):
        task = task_for([
            event("work-sparse-start", checkpoint="old", head_sha="1" * 40, semantic_area="old area"),
            event("work-sparse-checkpoint", "CHECKPOINT", LATER,
                  checkpoint={"progress": "new"}, head_sha="2" * 40, semantic_area="new area"),
            event("work-sparse-heartbeat", "HEARTBEAT", LATEST),
        ])
        self.assertEqual(task["checkpoint"], '{"progress":"new"}')
        self.assertEqual(task["head_sha"], "2" * 40)
        self.assertEqual(task["semantic_area"], "new area")
        self.assertEqual(task["last_kind"], "HEARTBEAT")
        self.assertEqual(task["last_ts"], LATEST)

    def test_scope_and_lineage_accumulate_without_rewriting_history(self):
        first = event("work-scope-first", claimed_paths=["src/a.py", "shared.py"],
                      parent_ids=["ancestor-first"], semantic_area="initial area")
        later = event("work-scope-later", "HANDOFF", LATER,
                      claimed_paths=["shared.py", "tests/b.py"],
                      parent_ids=["ancestor-first", "ancestor-second"], semantic_area="updated area")
        snap = project([later, first], now=NOW)
        task = snap["work_map"][0]
        self.assertEqual(task["claimed_paths"], ["src/a.py", "shared.py", "tests/b.py"])
        self.assertEqual(task["lineage"], ["ancestor-first", "ancestor-second"])
        self.assertEqual(task["semantic_area"], "updated area")
        by_id = {row["event_id"]: row for row in snap["timeline"]}
        self.assertEqual(by_id["work-scope-first"]["claimed_paths"], ["src/a.py", "shared.py"])
        self.assertEqual(by_id["work-scope-later"]["claimed_paths"], ["shared.py", "tests/b.py"])

    def test_evidence_includes_each_unique_ordered_event_once(self):
        first = event("work-evidence-first")
        later = event("work-evidence-later", "CHECKPOINT", LATER)
        snap = project([later, first, deepcopy(first)], now=NOW)
        evidence_ids = [row.get("event_id") for row in snap["work_map"][0]["evidence"]]
        self.assertEqual(evidence_ids, ["work-evidence-first", "work-evidence-later"])
        self.assertEqual(snap["duplicates_ignored"], ["work-evidence-first"])

    def test_different_tasks_do_not_inherit_each_others_metadata(self):
        snap = project([
            event("work-task-a", task_id="task-a", checkpoint="a-first", claimed_paths=["a.py"]),
            event("work-task-b", "START", LATER, task_id="task-b", checkpoint="b-only", claimed_paths=["b.py"]),
            event("work-task-a-update", "CHECKPOINT", LATEST, task_id="task-a",
                  checkpoint="a-later", claimed_paths=["a-test.py"]),
        ], now=NOW)
        tasks = {row["task_id"]: row for row in snap["work_map"]}
        self.assertEqual(tasks["task-a"]["checkpoint"], "a-later")
        self.assertEqual(tasks["task-a"]["claimed_paths"], ["a.py", "a-test.py"])
        self.assertEqual(tasks["task-b"]["checkpoint"], "b-only")
        self.assertEqual(tasks["task-b"]["claimed_paths"], ["b.py"])
        self.assertEqual(tasks["task-b"]["last_ts"], LATER)

    def test_handoff_updates_existing_owner_and_objective_behavior(self):
        task = task_for([
            event("work-owner-first", objective="initial objective"),
            event("work-owner-next", "HANDOFF", LATER,
                  session_id="successor-session", objective="current objective", checkpoint="handoff packet"),
        ])
        self.assertEqual(task["session_id"], "successor-session")
        self.assertEqual(task["objective"], "current objective")
        self.assertEqual(task["checkpoint"], "handoff packet")

    def test_terminal_events_refresh_metadata_without_changing_state_contract(self):
        for kind, expected in (("LANDING", "TERMINAL"), ("TERMINAL", "TERMINAL"),
                               ("RELEASE", "RELEASED"), ("SUPERSEDED", "SUPERSEDED")):
            with self.subTest(kind=kind):
                task = task_for([event("work-before-terminal", checkpoint="start"),
                                 event("work-terminal", kind, LATER, checkpoint="final receipt")])
                self.assertEqual(task["state"], expected)
                self.assertEqual(task["checkpoint"], "final receipt")
                self.assertEqual(task["last_kind"], kind)
                self.assertEqual(task["last_ts"], LATER)

    def test_unknown_timestamp_does_not_replace_known_observation(self):
        task = task_for([
            event("work-known-time", "CHECKPOINT", LATER, checkpoint="known observation"),
            event("work-unknown-time", ts="UNKNOWN", checkpoint="undated observation"),
        ])
        self.assertEqual(task["last_ts"], LATER)
        self.assertEqual(task["checkpoint"], "known observation")

    def test_projection_is_deterministic_and_does_not_mutate_inputs(self):
        events = [event("work-pure-start", claimed_paths=["a.py"], parent_ids=["parent-a"]),
                  event("work-pure-next", "CHECKPOINT", LATER,
                        claimed_paths=["b.py"], parent_ids=["parent-b"], checkpoint={"step": 2})]
        original = deepcopy(events)
        self.assertEqual(project(events, now=NOW), project(events, now=NOW))
        self.assertEqual(events, original)


if __name__ == "__main__":
    unittest.main()
