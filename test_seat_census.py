#!/usr/bin/env python3
"""Contract for host/seat_census.py — the cross-harness seat census.

The module self-test covers liveness bands, rollups and the declared/derived
split. This covers the disk road: the open write path at seats/*.json, survival
of unrecognised fields, no-op byte stability, and the fail-closed path.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from host import seat_census  # noqa: E402

UNKNOWN = seat_census.UNKNOWN


class TempRepo(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="seat-census-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        os.makedirs(os.path.join(self.root, "seats"))

    def seat(self, name, payload):
        path = os.path.join(self.root, "seats", "%s.json" % name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def roster(self, rows):
        with open(os.path.join(self.root, "presence.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(rows, fh)

    def out(self):
        with open(os.path.join(self.root, "seats.json"), encoding="utf-8") as fh:
            return json.load(fh)


class TestSelfContract(unittest.TestCase):
    def test_module_self_test_passes(self):
        self.assertEqual(seat_census.self_test(), 0)


class TestOpenWriteRoad(TempRepo):
    def test_any_seat_may_write_one_file_with_whatever_it_knows(self):
        self.seat("MINIMAL", {"seat": "MINIMAL"})
        self.seat("FULL", {
            "seat": "FULL", "kind": "language-model", "model": "some-model",
            "harness": "some-harness", "heartbeat": "2026-09-10T20:00:00Z",
            "tools": {"count": 12}, "roads": ["slack"],
        })
        payload, changed = seat_census.write(self.root, now="2026-09-10T20:05:00Z")
        self.assertTrue(changed)
        seats = {s["seat"]: s for s in payload["seats"]}
        self.assertEqual(set(seats), {"MINIMAL", "FULL"})
        self.assertEqual(seats["FULL"]["derived"]["liveness"], "LIVE")
        self.assertEqual(seats["MINIMAL"]["derived"]["liveness"], UNKNOWN)

    def test_seat_name_falls_back_to_the_filename(self):
        self.seat("NAMELESS", {"kind": "worker"})
        declared, bad = seat_census.read_declared(self.root)
        self.assertEqual(bad, [])
        self.assertIn("NAMELESS", declared)
        self.assertEqual(declared["NAMELESS"]["seat"], "NAMELESS")

    def test_unrecognised_fields_survive_verbatim(self):
        self.seat("INVENTOR", {
            "seat": "INVENTOR",
            "heartbeat": "2026-09-10T20:00:00Z",
            "gpu_watts": 350,
            "nested": {"anything": ["at", "all"]},
        })
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seat = payload["seats"][0]
        self.assertEqual(seat["extra"]["gpu_watts"], 350)
        self.assertEqual(seat["extra"]["nested"], {"anything": ["at", "all"]})

    def test_a_malformed_file_is_reported_and_the_rest_still_build(self):
        self.seat("GOOD", {"seat": "GOOD", "heartbeat": "2026-09-10T20:00:00Z"})
        with open(os.path.join(self.root, "seats", "BROKEN.json"), "w",
                  encoding="utf-8") as fh:
            fh.write("{ not json")
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        self.assertEqual([s["seat"] for s in payload["seats"]], ["GOOD"])
        self.assertEqual(payload["unreadable_seat_files"][0]["file"],
                         "BROKEN.json")


class TestSilenceIsNotAbsence(TempRepo):
    def test_a_seat_that_never_declared_still_appears(self):
        self.roster([{"from": "NEVERWROTE", "ts": "2026-09-10T19:00:00Z"}])
        # 30 minutes since it last spoke: past LIVE, inside QUIET.
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:30:00Z")
        self.assertEqual(payload["seats"], [])
        entry = payload["roster"][0]
        self.assertEqual(entry["seat"], "NEVERWROTE")
        self.assertEqual(entry["liveness"], "QUIET")
        self.assertEqual(entry["heartbeat_age_s"], 1800)
        self.assertEqual(payload["totals"]["presence_only"], 1)
        self.assertEqual(payload["totals"]["seats"], 1)
        self.assertEqual(payload["by_liveness"], {"QUIET": 1})

    def test_roster_rows_carry_only_what_is_known(self):
        """A name with nothing declared must not cost a skeleton of UNKNOWNs."""
        self.roster([{"from": "N%d" % i, "ts": "2026-09-10T19:00:00Z"}
                     for i in range(50)])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        self.assertEqual(len(payload["roster"]), 50)
        for entry in payload["roster"]:
            self.assertEqual(set(entry),
                             {"seat", "liveness", "heartbeat", "heartbeat_age_s"})
        size = os.path.getsize(os.path.join(self.root, "seats.json"))
        self.assertLess(size, 12000,
                        "50 roster names should stay small, got %d bytes" % size)

    def test_roster_values_wrapped_in_literal_quotes_normalise(self):
        self.roster([{"from": '"QUOTED"', "ts": '"2026-09-10T19:00:00Z"'}])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        self.assertEqual([r["seat"] for r in payload["roster"]], ["QUOTED"])
        self.assertEqual(payload["roster"][0]["liveness"], "LIVE")

    def test_declared_heartbeat_beats_a_stale_roster_row(self):
        self.roster([{"from": "BOTH", "ts": "2026-01-01T00:00:00Z"}])
        self.seat("BOTH", {"seat": "BOTH", "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seat = payload["seats"][0]
        self.assertEqual(seat["source"], "declared")
        self.assertEqual(seat["derived"]["liveness"], "LIVE")


class TestMissingIsUnknownNotZero(TempRepo):
    def test_absent_capability_fields_never_read_as_zero(self):
        self.seat("QUIET", {"seat": "QUIET",
                            "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        declared = payload["seats"][0]["declared"]
        derived = payload["seats"][0]["derived"]
        self.assertEqual(declared["tools"]["count"], UNKNOWN)
        self.assertEqual(declared["context"]["limit_tokens"], UNKNOWN)
        self.assertEqual(declared["budget"]["remaining_pct"], UNKNOWN)
        self.assertEqual(declared["model"], UNKNOWN)
        self.assertEqual(derived["context_pressure_pct"], UNKNOWN)
        self.assertEqual(derived["budget_pressure"], UNKNOWN)
        # A seat that did not report tools must not be counted as reporting 0.
        self.assertEqual(payload["totals"]["seats_reporting_tools"], 0)
        self.assertEqual(payload["totals"]["tools_declared_total"], 0)

    def test_a_seat_reporting_zero_tools_is_distinct_from_silence(self):
        self.seat("ZERO", {"seat": "ZERO", "tools": {"count": 0},
                           "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        self.assertEqual(payload["seats"][0]["declared"]["tools"]["count"], 0)
        self.assertEqual(payload["totals"]["seats_reporting_tools"], 1)


class TestDeclaredVersusDerived(TempRepo):
    def test_a_seat_cannot_declare_itself_live(self):
        self.seat("BOASTER", {
            "seat": "BOASTER", "state": "WORKING", "liveness": "LIVE",
            "heartbeat": "2026-09-01T00:00:00Z",
        })
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        seat = payload["seats"][0]
        self.assertEqual(seat["derived"]["liveness"], "COLD")
        self.assertEqual(seat["declared"]["state"], "WORKING")
        # The self-asserted liveness lands in extra, never in derived.
        self.assertEqual(seat["extra"]["liveness"], "LIVE")

    def test_there_is_no_idle_band_only_a_declared_one(self):
        self.seat("RESTING", {"seat": "RESTING", "state": "IDLE",
                              "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seat = payload["seats"][0]
        self.assertEqual(seat["derived"]["liveness"], "LIVE")
        self.assertEqual(seat["declared"]["state"], "IDLE")
        self.assertNotIn("IDLE", payload["by_liveness"])


class TestRouting(TempRepo):
    def test_context_and_budget_pressure_surface_for_routing(self):
        self.seat("HOT", {
            "seat": "HOT", "heartbeat": "2026-09-10T20:00:00Z",
            "context": {"limit_tokens": 200000, "used_tokens": 180000},
            "budget": {"window": "weekly", "remaining_pct": 8,
                       "resets_at": "2026-09-10T21:00:00Z"},
        })
        self.seat("COOL", {
            "seat": "COOL", "heartbeat": "2026-09-10T20:00:00Z",
            "context": {"limit_tokens": 1000000, "used_tokens": 50000},
            "budget": {"window": "weekly", "remaining_pct": 90},
        })
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seats = {s["seat"]: s for s in payload["seats"]}
        self.assertEqual(seats["HOT"]["derived"]["context_pressure_pct"], 90.0)
        self.assertEqual(seats["COOL"]["derived"]["context_pressure_pct"], 5.0)
        self.assertEqual(seats["HOT"]["derived"]["budget_pressure"], "HIGH")
        self.assertEqual(seats["COOL"]["derived"]["budget_pressure"], "LOW")
        self.assertEqual([r["seat"] for r in payload["context_pressure"]], ["HOT"])
        self.assertEqual([r["seat"] for r in payload["budget_watch"]], ["HOT"])
        self.assertEqual(seats["HOT"]["derived"]["seconds_to_budget_reset"], 3540)

    def test_open_cants_roll_up_cheapest_first_with_their_seat(self):
        self.seat("A", {"seat": "A", "heartbeat": "2026-09-10T20:00:00Z",
                        "cants": [{"what": "no web", "need": "proxy",
                                   "est_minutes": 60}]})
        self.seat("B", {"seat": "B", "heartbeat": "2026-09-10T20:00:00Z",
                        "cants": [{"what": "no push", "need": "token scope",
                                   "est_minutes": 5}]})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        self.assertEqual([c["seat"] for c in payload["open_cants"]], ["B", "A"])
        self.assertEqual(payload["open_cants"][0]["need"], "token scope")

    def test_a_cant_without_an_estimate_sorts_last_and_reads_unknown(self):
        self.seat("A", {"seat": "A", "heartbeat": "2026-09-10T20:00:00Z",
                        "cants": [{"what": "unscoped"}]})
        self.seat("B", {"seat": "B", "heartbeat": "2026-09-10T20:00:00Z",
                        "cants": [{"what": "scoped", "est_minutes": 30}]})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        self.assertEqual([c["seat"] for c in payload["open_cants"]], ["B", "A"])
        self.assertEqual(payload["open_cants"][1]["est_minutes"], UNKNOWN)


class TestStability(TempRepo):
    def test_rebuild_with_unchanged_inputs_writes_nothing(self):
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T20:00:00Z"})
        seat_census.write(self.root)
        first = self.out()
        _, changed = seat_census.write(self.root)
        self.assertFalse(changed)
        self.assertEqual(self.out(), first)

    def test_reference_time_defaults_to_newest_input_not_wall_clock(self):
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root)
        self.assertEqual(payload["reference_time"], "2026-09-10T20:00:00Z")
        self.assertEqual(payload["seats"][0]["derived"]["heartbeat_age_s"], 0)

    def test_now_override_gives_a_live_reading(self):
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-12T20:00:00Z")
        self.assertEqual(payload["seats"][0]["derived"]["liveness"], "COLD")
        self.assertEqual(payload["seats"][0]["derived"]["heartbeat_age_s"],
                         2 * 86400)

    def test_band_boundaries_are_inclusive_as_documented(self):
        """<= 15m LIVE, <= 60m QUIET, <= 24h STALE, beyond that COLD."""
        cases = [
            ("2026-09-10T20:15:00Z", "LIVE"),    # exactly 15 minutes
            ("2026-09-10T20:15:01Z", "QUIET"),
            ("2026-09-10T21:00:00Z", "QUIET"),   # exactly 60 minutes
            ("2026-09-10T21:00:01Z", "STALE"),
            ("2026-09-11T20:00:00Z", "STALE"),   # exactly 24 hours
            ("2026-09-11T20:00:01Z", "COLD"),
        ]
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T20:00:00Z"})
        for now, expected in cases:
            payload, _ = seat_census.write(self.root, now=now)
            self.assertEqual(payload["seats"][0]["derived"]["liveness"],
                             expected, "at %s" % now)


class TestHonesty(TempRepo):
    def test_no_seats_and_no_roster_writes_nothing(self):
        with self.assertRaises(SystemExit) as caught:
            seat_census.write(self.root)
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "seats.json")))

    def test_unparsable_heartbeat_reads_unknown_not_cold(self):
        self.seat("S", {"seat": "S", "heartbeat": "whenever"})
        self.seat("T", {"seat": "T", "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seats = {s["seat"]: s for s in payload["seats"]}
        self.assertEqual(seats["S"]["derived"]["liveness"], UNKNOWN)
        self.assertEqual(seats["S"]["derived"]["heartbeat_age_s"], UNKNOWN)

    def test_a_future_heartbeat_clamps_to_zero_rather_than_going_negative(self):
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-11T00:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        self.assertEqual(payload["seats"][0]["derived"]["heartbeat_age_s"], 0)
        self.assertEqual(payload["seats"][0]["derived"]["liveness"], "LIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
