"""Commons Protocol v0.1 + Observatory. unittest only. No extra deps."""
from __future__ import annotations

import json
import time
import unittest
from copy import deepcopy
from pathlib import Path

from protocol.emit import EXAMPLES, continue_from_observation, emit
from protocol.events import event_id_for, parse_event, parse_events
from protocol.projector import project
from protocol.schema import EVENT_KINDS, PROTOCOL_ID, SNAPSHOT_SCHEMA

HERE = Path(__file__).resolve().parent
OBS_TOOLS = (
    "read_observatory",
    "observe_work",
    "project_live_work",
    "continue_from_observation",
)


def load_json(rel):
    return json.loads((HERE / rel).read_text(encoding="utf-8"))


class ProtocolEventTests(unittest.TestCase):
    def test_positive_events_round_trip(self):
        rows = parse_events(load_json("protocol/fixtures/positive.json"))
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(row["event_id"] for row in rows))
        self.assertEqual(rows[0]["kind"], "START")
        self.assertEqual(rows[0]["classification"], "LOCAL")

    def test_malformed_events_are_kept(self):
        rows = parse_events(load_json("protocol/fixtures/malformed.json"))
        self.assertEqual(len(rows), 5)
        self.assertTrue(any(row["parse_state"] == "MALFORMED" for row in rows))
        self.assertTrue(all(row["session_id"] for row in rows))

    def test_stable_event_ids(self):
        payload = {"kind": "START", "session_id": "abc-session", "ts": "2026-08-28T08:00:00Z", "task_id": "t1"}
        self.assertEqual(event_id_for(payload), event_id_for(payload))
        self.assertNotEqual(event_id_for(payload), event_id_for({**payload, "ts": "2026-08-28T08:00:01Z"}))

    def test_unknown_future_harness_is_accepted(self):
        event = EXAMPLES["unknown_future"]
        self.assertEqual(event["session_id"], "UNKNOWN")
        self.assertEqual(event["classification"], "UNKNOWN")
        self.assertEqual(event["kind"], "START")


class ProjectorTests(unittest.TestCase):
    def test_deterministic_rebuild(self):
        events = load_json("protocol/fixtures/positive.json")
        first = project(events, now="2026-08-28T09:30:00Z")
        second = project(deepcopy(events), now="2026-08-28T09:30:00Z")
        self.assertEqual(first["digest"], second["digest"])
        self.assertEqual(first["schema"], SNAPSHOT_SCHEMA)
        self.assertEqual(first["protocol"], PROTOCOL_ID)

    def test_zero_sessions_when_empty(self):
        snap = project([], now="2026-08-28T09:30:00Z")
        self.assertEqual(snap["sessions"], [])
        self.assertEqual(snap["cockpit"]["counts"]["confirmed_active"], 0)
        self.assertEqual(snap["economy"]["collected_cash_usd"], 0)

    def test_quiet_presence_is_not_a_session(self):
        legacy = load_json("protocol/fixtures/legacy_partial.json")
        snap = project([], now="2026-08-28T09:30:00Z", legacy=legacy)
        self.assertTrue(snap["presence"])
        self.assertFalse(any(row["claim"] == "RIVET" and row["is_session"] for row in snap["presence"]))
        self.assertTrue(any(row["session_id"].startswith("job.") for row in snap["sessions"]))

    def test_slack_author_does_not_mint_session(self):
        legacy = {
            "recent": [
                {"from": "BRYCE", "id": "slack-1", "kind": "slack_message", "ts": "2026-08-28T09:00:00Z", "body": "hi"},
                {"from": "BRYCE", "id": "slack-2", "kind": "slack_thread_reply", "ts": "2026-08-28T09:01:00Z", "body": "again"},
            ]
        }
        snap = project([], now="2026-08-28T09:30:00Z", legacy=legacy)
        self.assertEqual(snap["sessions"], [])

    def test_duplicate_start_does_not_double_spend(self):
        event = emit("START", session_id="dup-session-01", task_id="t-dup", run_id="r-dup", ts="2026-08-28T08:00:00Z", dedupe_key="same")
        snap = project([event, deepcopy(event)], now="2026-08-28T09:00:00Z")
        self.assertEqual(len([s for s in snap["sessions"] if s["session_id"] == "dup-session-01"]), 1)
        self.assertEqual(len(snap["duplicates_ignored"]), 1)

    def test_duplicate_grok_url_is_advisory_collision(self):
        a = emit("START", session_id="g1", task_id="t1", run_id="r1", ts="2026-08-28T08:00:00Z", classification="BROWSER", grok_url="https://grok.com/c/same-rid", harness="grok.com")
        b = emit("START", session_id="g2", task_id="t2", run_id="r2", ts="2026-08-28T08:01:00Z", classification="BROWSER", grok_url="https://grok.com/c/same-rid?rid=x", harness="grok.com")
        snap = project([a, b], now="2026-08-28T08:02:00Z")
        kinds = [row["kind"] for row in snap["collisions"]]
        self.assertIn("DUPLICATE_GROK_URL", kinds)
        self.assertTrue(all(row["advisory"] and row["blocks_participation"] is False for row in snap["collisions"]))

    def test_path_overlap_is_advisory(self):
        a = emit("START", session_id="p1", task_id="t1", ts="2026-08-28T08:00:00Z", claimed_paths=["protocol/schema.py"])
        b = emit("START", session_id="p2", task_id="t2", ts="2026-08-28T08:00:01Z", claimed_paths=["protocol/schema.py"])
        snap = project([a, b], now="2026-08-28T08:02:00Z")
        self.assertTrue(any(row["kind"] == "EXACT_PATH" for row in snap["collisions"]))
        self.assertFalse(any(row.get("blocks_participation") for row in snap["collisions"]))

    def test_out_of_order_checkpoints(self):
        start = emit("START", session_id="oo-1", task_id="t-oo", ts="2026-08-28T08:00:00Z")
        later = emit("CHECKPOINT", session_id="oo-1", task_id="t-oo", ts="2026-08-28T08:05:00Z", checkpoint="second")
        earlier = emit("CHECKPOINT", session_id="oo-1", task_id="t-oo", ts="2026-08-28T08:01:00Z", checkpoint="first")
        snap = project([later, start, earlier], now="2026-08-28T08:06:00Z")
        session = snap["sessions"][0]
        self.assertEqual(session["checkpoint"], "second")
        self.assertEqual(session["last_ts"], "2026-08-28T08:05:00Z")

    def test_stale_after_is_explicit(self):
        event = emit("START", session_id="stale-1", task_id="t-stale", ts="2026-08-28T07:00:00Z")
        snap = project([event], now="2026-08-28T09:00:00Z", stale_after_seconds=60)
        self.assertEqual(snap["sessions"][0]["state"], "STALE")
        self.assertEqual(snap["stale_after_seconds"], 60)

    def test_cash_stays_zero_and_does_not_invent_revenue(self):
        legacy = {"recovery": {"truth": {"collected_cash_usd": 0, "replies_observed": 0, "bank_available": "NOT_LANDED"}, "offer": {"collected_cash_usd": 0, "cash_state": "NOT_LANDED"}}}
        snap = project(list(EXAMPLES.values()), now="2026-08-28T09:30:00Z", legacy=legacy)
        self.assertEqual(snap["economy"]["collected_cash_usd"], 0)
        self.assertIn("Commons revenue remains USD 0.", snap["cockpit"]["lines"])
        self.assertIn("draft", snap["economy"]["never_counted_as_revenue"])

    def test_forged_cost_without_visible_evidence_is_unknown(self):
        event = parse_event({"kind": "HEARTBEAT", "session_id": "cost-1", "ts": "2026-08-28T08:00:00Z", "tokens": "a million"})
        self.assertIsNone(event["cost"]["tokens"])
        self.assertEqual(event["cost"]["grade"], "UNKNOWN")

    def test_private_artifact_without_bytes(self):
        event = emit("CHECKPOINT", session_id="art-1", task_id="t-art", ts="2026-08-28T08:00:00Z", artifacts=[{"path": "secret.bin", "provider_private": True}])
        snap = project([event], now="2026-08-28T08:01:00Z")
        self.assertTrue(any(row["kind"] == "PRIVATE_ARTIFACT" for row in snap["attention"]))

    def test_released_session_can_return(self):
        rel = emit("RELEASE", session_id="ret-1", task_id="t-ret", ts="2026-08-28T08:00:00Z")
        start = emit("START", session_id="ret-1", task_id="t-ret", ts="2026-08-28T08:10:00Z")
        snap = project([rel, start], now="2026-08-28T08:11:00Z")
        self.assertEqual(snap["sessions"][0]["state"], "WORKING")

    def test_continue_from_observation_is_advisory(self):
        snap = project(list(EXAMPLES.values()), now="2026-08-28T09:30:00Z")
        cont = continue_from_observation(snap)
        self.assertTrue(cont["advisory"])
        self.assertFalse(cont["authority"])
        self.assertFalse(cont["replay_finished_prompt"])
        self.assertIn("open_carrier_envelope", cont)

    def test_router_does_not_dump_browser_work_on_local(self):
        local = emit("START", session_id="loc-1", ts="2026-08-28T08:00:00Z", classification="LOCAL", tools=["filesystem"], harness="Codex desktop local")
        browser = emit("START", session_id="br-1", ts="2026-08-28T08:00:00Z", classification="BROWSER", tools=["browser"], harness="grok.com")
        snap = project([local, browser], now="2026-08-28T08:01:00Z", need={"capabilities": ["BROWSER"]})
        ranked = snap["routes"]
        browser_rank = next(row["rank"] for row in ranked if row["session_id"] == "br-1")
        local_rank = next(row["rank"] for row in ranked if row["session_id"] == "loc-1")
        self.assertLess(browser_rank, local_rank)

    def test_blocked_capability_is_not_recommended_first(self):
        blocked = emit("BLOCKED", session_id="blk-1", ts="2026-08-28T08:00:00Z", classification="BROWSER", tools=["browser"], blocker={"type": "external_authority", "detail": "cloudflare"})
        healthy = emit("START", session_id="ok-1", ts="2026-08-28T08:00:00Z", classification="BROWSER", tools=["browser"])
        snap = project([blocked, healthy], now="2026-08-28T08:01:00Z", need={"capabilities": ["BROWSER"]})
        self.assertEqual(snap["routes"][0]["session_id"], "ok-1")

    def test_open_door_flags(self):
        snap = project([], now="2026-08-28T09:30:00Z")
        self.assertFalse(snap["open_door"]["authentication"])
        self.assertFalse(snap["open_door"]["authorization"])
        self.assertTrue(snap["open_door"]["leases_are_descriptive"])
        self.assertTrue(snap["open_door"]["collisions_are_advisory"])

    def test_twenty_sessions_and_stress(self):
        events = []
        for i in range(20):
            sid = "sess-%02d-abcdef" % i
            events.append(emit("START", session_id=sid, task_id="task-%02d" % i, ts="2026-08-28T08:00:00Z", claimed_paths=["lane-%02d/file.py" % i], classification="CLOUD" if i % 2 else "LOCAL"))
            events.append(emit("HEARTBEAT", session_id=sid, task_id="task-%02d" % i, ts="2026-08-28T08:01:00Z"))
        events.append(emit("START", session_id="collide-a-abcdef", task_id="task-col", ts="2026-08-28T08:02:00Z", claimed_paths=["shared/x.py"]))
        events.append(emit("START", session_id="collide-b-abcdef", task_id="task-col-2", ts="2026-08-28T08:02:01Z", claimed_paths=["shared/x.py"]))
        t0 = time.perf_counter()
        snap = project(events, now="2026-08-28T08:03:00Z")
        elapsed = time.perf_counter() - t0
        self.assertGreaterEqual(len(snap["sessions"]), 20)
        self.assertTrue(any(row["kind"] == "EXACT_PATH" for row in snap["collisions"]))
        self.assertLess(elapsed, 2.0)

    def test_projection_does_not_mutate_inputs(self):
        events = load_json("protocol/fixtures/positive.json")
        before = json.dumps(events)
        project(events, now="2026-08-28T09:30:00Z")
        self.assertEqual(json.dumps(events), before)

    def test_semantic_collision_on_different_paths(self):
        a = emit("START", session_id="sem-a-abcdef", task_id="t-a", ts="2026-08-28T08:00:00Z", claimed_paths=["a/one.py"], semantic_area="observatory-protocol")
        b = emit("START", session_id="sem-b-abcdef", task_id="t-b", ts="2026-08-28T08:00:01Z", claimed_paths=["b/two.py"], semantic_area="observatory-protocol")
        snap = project([a, b], now="2026-08-28T08:02:00Z")
        self.assertTrue(any(row["kind"] == "SEMANTIC_AREA" for row in snap["collisions"]))
        self.assertTrue(all(row["advisory"] for row in snap["collisions"]))

    def test_moving_main_is_advisory_divergence(self):
        event = emit("START", session_id="div-1-abcdef", task_id="t-div", ts="2026-08-28T08:00:00Z", head_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
        snap = project([event], now="2026-08-28T08:01:00Z", head_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertTrue(any(row["kind"] == "BRANCH_DIVERGENCE" for row in snap["collisions"]))
        self.assertFalse(any(row.get("blocks_participation") for row in snap["collisions"]))

    def test_takeover_after_staleness_remains_open(self):
        stale = emit("START", session_id="old-sess-abcdef", task_id="t-old", ts="2026-08-28T06:00:00Z", claimed_paths=["protocol/emit.py"])
        fresh = emit("START", session_id="new-sess-abcdef", task_id="t-new", ts="2026-08-28T08:00:00Z", claimed_paths=["protocol/emit.py"])
        snap = project([stale, fresh], now="2026-08-28T08:01:00Z", stale_after_seconds=60)
        states = {row["session_id"]: row["state"] for row in snap["sessions"]}
        self.assertEqual(states["old-sess-abcdef"], "STALE")
        self.assertEqual(states["new-sess-abcdef"], "WORKING")
        self.assertTrue(any(row["kind"] == "EXACT_PATH" and row["advisory"] for row in snap["collisions"]))

    def test_contradictory_receipts_are_labeled(self):
        a = emit("TERMINAL", session_id="con-1-abcdef", task_id="t-con", ts="2026-08-28T08:00:00Z", terminal_disposition="DONE")
        b = emit("TERMINAL", session_id="con-1-abcdef", task_id="t-con", ts="2026-08-28T08:01:00Z", terminal_disposition="FAILED")
        snap = project([a, b], now="2026-08-28T08:02:00Z")
        self.assertTrue(snap["sessions"][0].get("contradiction"))
        self.assertTrue(any(row["kind"] == "UNSUPPORTED_CLAIM" for row in snap["attention"]))

    def test_provider_output_without_gpt_review(self):
        event = emit("LANDING", session_id="rev-1-abcdef", task_id="t-rev", ts="2026-08-28T08:00:00Z", terminal_disposition="DONE", provider={"needs_gpt_review": True})
        snap = project([event], now="2026-08-28T08:01:00Z")
        self.assertTrue(any(row["kind"] == "AMBIGUOUS_COMPLETION" for row in snap["attention"]))

    def test_executor_crash_before_and_after_submit(self):
        pre = {
            "job_id": "grok-pre-submit-01",
            "status": "OPEN",
            "harness": "grok.com authenticated browser via Commons MCP",
            "updated_at": "2026-08-28T08:00:00Z",
            "objective": "capture one grok run",
            "checkpoint": {
                "schema": "commons-grok-executor-job/v1",
                "run_key": "run-pre-1",
                "origin": {"session_id": "grok-exec-pre-01", "task_id": "t-pre"},
                "execution": {"state": "QUEUED", "submission_state": "NOT_SUBMITTED", "prompt_replay_allowed": True},
            },
        }
        post = {
            "job_id": "grok-post-submit-01",
            "status": "LEASED",
            "harness": "grok.com authenticated browser via Commons MCP",
            "updated_at": "2026-08-28T08:00:00Z",
            "objective": "capture one grok run",
            "checkpoint": {
                "schema": "commons-grok-executor-job/v1",
                "run_key": "run-post-1",
                "conversation_url": "https://grok.com/c/post-rid",
                "origin": {"session_id": "grok-exec-post-01", "task_id": "t-post"},
                "execution": {"state": "RUNNING", "submission_state": "SUBMITTED", "prompt_replay_allowed": False},
            },
        }
        snap = project([], now="2026-08-28T08:01:00Z", legacy={"jobs": [pre, post]})
        by_id = {row["session_id"]: row for row in snap["sessions"]}
        self.assertEqual(by_id["grok-exec-pre-01"]["state"], "IDLE")
        self.assertEqual(by_id["grok-exec-post-01"]["state"], "BLOCKED")
        self.assertEqual(by_id["grok-exec-post-01"]["classification"], "BROWSER")
        self.assertTrue(any(row["kind"] == "PROVIDER_UNCERTAINTY" for row in snap["attention"]))
        cont = continue_from_observation(snap, session_id="grok-exec-post-01")
        self.assertFalse(cont["replay_finished_prompt"])

    def test_stress_two_hundred_sessions_stays_cheap(self):
        events = []
        for i in range(200):
            sid = "bulk-%03d-abcdef" % i
            events.append(emit("START", session_id=sid, task_id="bulk-%03d" % i, ts="2026-08-28T08:00:00Z", claimed_paths=["bulk/%03d.py" % i]))
        t0 = time.perf_counter()
        snap = project(events, now="2026-08-28T08:01:00Z")
        elapsed = time.perf_counter() - t0
        self.assertEqual(len(snap["sessions"]), 200)
        self.assertLess(elapsed, 2.0)

    def test_jsonl_malformed_line_does_not_crash_host(self):
        from host import observatory as obs
        snap = obs.snapshot(str(HERE), now="2026-08-28T09:30:00Z", events=["not-object", {"kind": "START", "session_id": "jsonl-1-abcdef", "ts": "2026-08-28T08:00:00Z"}])
        self.assertEqual(snap["schema"], SNAPSHOT_SCHEMA)


class HostAndSurfaceTests(unittest.TestCase):
    def test_host_projector_reads_legacy_bakes(self):
        from host import observatory as obs
        snap = obs.snapshot(str(HERE), now="2026-08-28T09:30:00Z")
        self.assertEqual(snap["schema"], SNAPSHOT_SCHEMA)
        self.assertGreaterEqual(len(snap["presence"]), 1)
        self.assertEqual(snap["economy"]["collected_cash_usd"], 0)
        self.assertEqual(snap["state"], "BAKE")

    def test_host_write_is_deterministic(self):
        from host import observatory as obs
        first = obs.snapshot(str(HERE), now="2026-08-28T09:30:00Z")
        second = obs.snapshot(str(HERE), now="2026-08-28T09:30:00Z")
        self.assertEqual(first["digest"], second["digest"])

    def test_html_surface_has_landmarks_and_no_verdict(self):
        html = (HERE / "observatory.html").read_text(encoding="utf-8")
        js = (HERE / "observatory.js").read_text(encoding="utf-8")
        css = (HERE / "observatory.css").read_text(encoding="utf-8")
        self.assertIn('aria-labelledby="cockpit-title"', html)
        self.assertIn("noscript", html.lower())
        self.assertIn('role="status"', html)
        self.assertIn("<caption>", html)
        self.assertIn('name="harness"', html)
        self.assertIn('name="revenue"', html)
        self.assertNotIn("VERDICT", html)
        self.assertNotIn("VERDICT", js)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("forced-colors", css)
        self.assertNotIn("337", html)

    def test_protocol_document_and_schema_exist(self):
        self.assertTrue((HERE / "protocol" / "PROTOCOL.md").is_file())
        schema = load_json("protocol/schema/event.schema.json")
        self.assertEqual(set(schema["properties"]["kind"]["enum"]), set(EVENT_KINDS))


class McpObservatoryTests(unittest.TestCase):
    def _mcp_source(self):
        return (HERE / "commons_mcp.py").read_text(encoding="utf-8")

    def test_tools_appended_after_verify_durability(self):
        source = self._mcp_source()
        self.assertLess(source.find('"name": "verify_durability"'), source.find('"name": "read_observatory"'))
        for name in OBS_TOOLS:
            self.assertIn('"name": "%s"' % name, source)
        chunk = source[source.find('"name": "read_observatory"'):source.find('"name": "continue_from_observation"') + 900]
        self.assertIn("readOnlyHint", chunk)

    def test_resource_is_listed(self):
        source = self._mcp_source()
        self.assertIn('"uri": "commons://observatory"', source)
        self.assertIn('("observatory", ""): ("observatory.json"', source)

    def test_gateway_tools_do_not_require_identity(self):
        from host import observatory as obs
        row = obs.read_observatory(str(HERE), {})
        self.assertEqual(row["state"], "BAKE")
        row = obs.observe_work(str(HERE), {"garbage": True})
        self.assertIn("cockpit", row)
        row = obs.project_live_work(str(HERE), "not-an-object")
        self.assertEqual(row["schema"], SNAPSHOT_SCHEMA)
        row = obs.continue_from(str(HERE), {})
        self.assertFalse(row["replay_finished_prompt"])

    def test_pagination_is_deterministic(self):
        from host import observatory as obs
        first = obs.read_observatory(str(HERE), {"view": "census", "limit": 3, "offset": 0})
        second = obs.read_observatory(str(HERE), {"view": "census", "limit": 3, "offset": 0})
        self.assertEqual(first.get("sessions"), second.get("sessions"))
        self.assertEqual(first["pagination"][0]["deterministic"], True)
        malformed = obs.read_observatory(str(HERE), {"view": "timeline", "limit": "nope", "offset": "x", "garbage": True})
        self.assertEqual(malformed["state"], "BAKE")
        self.assertIn("timeline", malformed)


class ExtraAdversarialTests(unittest.TestCase):
    def test_branch_landed_under_different_pr(self):
        a = emit("LANDING", session_id="pr-a-abcdef", task_id="t-same", ts="2026-08-28T08:00:00Z", artifacts=[{"url": "https://github.com/woahwhattheheck/commons/pull/1"}])
        b = emit("LANDING", session_id="pr-b-abcdef", task_id="t-same", ts="2026-08-28T08:01:00Z", artifacts=[{"url": "https://github.com/woahwhattheheck/commons/pull/2"}])
        snap = project([a, b], now="2026-08-28T08:02:00Z")
        self.assertTrue(any(row["kind"] == "AMBIGUOUS_COMPLETION" and "different PRs" in str(row.get("detail")) for row in snap["attention"]))

    def test_handoff_supersede_lease_attention_kinds(self):
        events = [
            emit("START", session_id="life-1-abcdef", task_id="t-life", ts="2026-08-28T08:00:00Z"),
            emit("HANDOFF", session_id="life-1-abcdef", task_id="t-life", ts="2026-08-28T08:02:00Z"),
            emit("LEASE_EXPIRED", session_id="life-1-abcdef", task_id="t-life", ts="2026-08-28T08:03:00Z"),
            emit("ATTENTION_REQUESTED", session_id="life-1-abcdef", task_id="t-life", ts="2026-08-28T08:04:00Z", attention_reason="owner money decision"),
            emit("SUPERSEDED", session_id="life-1-abcdef", task_id="t-life", ts="2026-08-28T08:05:00Z", supersedes="life-1-abcdef"),
        ]
        snap = project(events, now="2026-08-28T08:06:00Z")
        self.assertEqual(snap["sessions"][0]["state"], "SUPERSEDED")
        self.assertTrue(any(row["kind"] == "HUMAN_REQUESTED" for row in snap["attention"]))

    def test_no_access_gate_in_protocol_source(self):
        for rel in ("protocol/PROTOCOL.md", "protocol/projector.py", "host/observatory.py", "observatory.html"):
            text = (HERE / rel).read_text(encoding="utf-8").lower()
            self.assertNotIn("permission denied", text)
            self.assertNotIn("unauthorized", text)
            self.assertNotIn("login required", text)

    def test_independent_mcp_manifest_has_observatory_tools(self):
        tools = load_json("independent_commons_mcp/fixtures/tools.json")
        names = [row["name"] for row in tools["tools"]]
        for name in OBS_TOOLS:
            self.assertIn(name, names)

    def test_conformance_cli(self):
        import subprocess, sys
        proc = subprocess.run([sys.executable, "-m", "protocol", "--self-test"], cwd=str(HERE), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PASS", proc.stdout)


class OpenDoorSurfaceTests(unittest.TestCase):
    def test_no_auth_words_in_protocol_package(self):
        html = (HERE / "observatory.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("log in", html)
        self.assertNotIn("sign up", html)
        self.assertNotIn("password", html)
        js = (HERE / "observatory.js").read_text(encoding="utf-8").lower()
        self.assertNotIn("authorization required", js)
        self.assertNotIn("permission denied", js)


if __name__ == "__main__":
    unittest.main()
