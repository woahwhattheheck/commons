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

    def test_a_roster_row_with_no_time_still_names_someone(self):
        """presence.json carries rows like {"from": "ADAM-CREW", "ts": ""}."""
        self.roster([{"from": "NOTIME", "ts": ""},
                     {"from": "TIMED", "ts": "2026-09-10T19:00:00Z"},
                     {"from": "TIMED", "ts": ""}])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        rows = {r["seat"]: r for r in payload["roster"]}
        self.assertEqual(rows["NOTIME"]["liveness"], UNKNOWN)
        self.assertEqual(rows["NOTIME"]["heartbeat"], UNKNOWN)
        # An empty time never erases a real one for the same name.
        self.assertEqual(rows["TIMED"]["heartbeat"], "2026-09-10T19:00:00Z")

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

    def test_seats_that_say_they_are_idle_are_listed_as_worker_slots(self):
        self.seat("WAITING", {"seat": "WAITING", "state": "IDLE — send work",
                              "heartbeat": "2026-09-10T20:00:00Z",
                              "roads": ["slack", "github-git-data"]})
        self.seat("OLDIDLE", {"seat": "OLDIDLE", "state": "idle",
                              "heartbeat": "2026-09-10T19:00:00Z"})
        self.seat("BUSY", {"seat": "BUSY", "state": "WORKING",
                           "heartbeat": "2026-09-10T20:00:00Z"})
        self.seat("SILENT", {"seat": "SILENT",
                             "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        self.assertEqual([r["seat"] for r in payload["declared_idle"]],
                         ["WAITING", "OLDIDLE"])
        self.assertEqual(payload["declared_idle"][0]["roads"],
                         ["github-git-data", "slack"])
        # Nothing is ever inferred idle: a quiet seat with no state is not one.
        self.assertNotIn("SILENT", [r["seat"] for r in payload["declared_idle"]])

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


class TestLivenessActuallyAges(TempRepo):
    """The bake's ages are historical; a reader must derive its own.

    Without this, the seat that supplied the newest timestamp in the inputs is
    compared against itself forever and stays LIVE while it is gone.
    """

    def bake_once(self):
        self.seat("ALPHA", {"seat": "ALPHA", "kind": "language-model",
                            "heartbeat": "2026-09-10T20:00:00Z"})
        # An hour behind ALPHA, so it sits on the QUIET boundary at bake time
        # while ALPHA supplies the reference and reads age zero.
        self.roster([{"from": "BETA", "ts": "2026-09-10T19:00:00Z"}])
        payload, _ = seat_census.write(self.root)
        return payload

    def test_the_newest_seat_reads_live_in_the_bake_and_ages_on_read(self):
        baked = self.bake_once()
        # The bake compares the newest heartbeat to itself.
        self.assertEqual(baked["reference_time"], "2026-09-10T20:00:00Z")
        self.assertEqual(baked["seats"][0]["derived"]["liveness"], "LIVE")
        self.assertEqual(baked["seats"][0]["derived"]["heartbeat_age_s"], 0)
        self.assertEqual(baked["liveness_basis"], "bake")

        # A day later, with the file byte-for-byte unchanged, it is not LIVE.
        later = seat_census.recompute(baked, "2026-09-11T20:00:00Z")
        self.assertEqual(later["seats"][0]["derived"]["liveness"], "STALE")
        self.assertEqual(later["seats"][0]["derived"]["heartbeat_age_s"], 86400)
        self.assertEqual(later["liveness_basis"], "read")
        self.assertEqual(later["reference_time"], "2026-09-11T20:00:00Z")

    def test_time_advance_walks_every_band_on_unchanged_bytes(self):
        baked = self.bake_once()
        before = json.dumps(baked, sort_keys=True)
        walk = [
            ("2026-09-10T20:10:00Z", "LIVE"),
            ("2026-09-10T20:40:00Z", "QUIET"),
            ("2026-09-11T10:00:00Z", "STALE"),
            ("2026-09-12T20:00:01Z", "COLD"),
        ]
        for now, expected in walk:
            out = seat_census.recompute(baked, now)
            self.assertEqual(out["seats"][0]["derived"]["liveness"], expected,
                             "seat at %s" % now)
            self.assertEqual(out["by_liveness"].get(expected, 0) >= 1, True)
        # recompute never mutates the payload it was handed.
        self.assertEqual(json.dumps(baked, sort_keys=True), before)

    def test_roster_entries_age_too(self):
        baked = self.bake_once()
        self.assertEqual(baked["roster"][0]["liveness"], "QUIET")
        later = seat_census.recompute(baked, "2026-09-12T20:00:00Z")
        self.assertEqual(later["roster"][0]["liveness"], "COLD")

    def test_budget_reset_countdown_is_recomputed_not_frozen(self):
        self.seat("B", {"seat": "B", "heartbeat": "2026-09-10T20:00:00Z",
                        "budget": {"window": "weekly", "remaining_pct": 80,
                                   "resets_at": "2026-09-10T23:00:00Z"}})
        payload, _ = seat_census.write(self.root)
        self.assertEqual(payload["seats"][0]["derived"]["seconds_to_budget_reset"],
                         3 * 3600)
        later = seat_census.recompute(payload, "2026-09-10T22:00:00Z")
        self.assertEqual(later["seats"][0]["derived"]["seconds_to_budget_reset"],
                         3600)
        # Inside the six-hour window it now appears on the watch list.
        self.assertEqual([r["seat"] for r in later["budget_watch"]], ["B"])

    def test_an_explicit_now_marks_the_written_file_as_a_live_reading(self):
        self.seat("A", {"seat": "A", "heartbeat": "2026-09-10T20:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:30:00Z")
        self.assertEqual(payload["liveness_basis"], "read")
        self.assertEqual(payload["seats"][0]["derived"]["liveness"], "QUIET")

    def test_liveness_at_is_the_one_implementation(self):
        self.assertEqual(
            seat_census.liveness_at("2026-09-10T20:00:00Z",
                                    "2026-09-10T20:15:00Z"), ("LIVE", 900))
        self.assertEqual(
            seat_census.liveness_at("2026-09-10T20:00:00Z",
                                    "2026-09-10T20:15:01Z"), ("QUIET", 901))
        self.assertEqual(
            seat_census.liveness_at("nonsense", "2026-09-10T20:00:00Z"),
            (UNKNOWN, None))
        # A heartbeat within clock skew clamps rather than going negative; one
        # hours ahead cannot be measured and is not LIVE.
        self.assertEqual(
            seat_census.liveness_at("2026-09-10T20:03:00Z",
                                    "2026-09-10T20:00:00Z"), ("LIVE", 0))
        self.assertEqual(
            seat_census.liveness_at("2026-09-11T00:00:00Z",
                                    "2026-09-10T20:00:00Z"), (UNKNOWN, None))


class TestNonFiniteInput(TempRepo):
    """A seat may write anything. Nothing it writes may break the JSON."""

    def test_non_finite_numbers_never_reach_the_published_file(self):
        # json.load accepts these bare tokens, so a seat file really can carry
        # them; json.dumps would then emit them and no browser could parse it.
        # A seat file carrying one is quarantined whole and named, and the rest
        # of the census still builds.
        self.seat("GOOD", {"seat": "GOOD", "heartbeat": "2026-09-10T20:00:00Z"})
        path = os.path.join(self.root, "seats", "WILD.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"seat":"WILD","heartbeat":"2026-09-10T20:00:00Z",'
                     '"context":{"limit_tokens":NaN,"used_tokens":Infinity},'
                     '"budget":{"remaining_pct":-Infinity},'
                     '"tools":{"count":NaN}}')
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        blob = json.dumps(payload)
        for token in ("NaN", "Infinity", "-Infinity"):
            self.assertNotIn(token, blob)
        # Round-trips through a strict parser, which is what a browser does.
        json.loads(blob, parse_constant=self._reject)
        with open(os.path.join(self.root, "seats.json"), encoding="utf-8") as fh:
            json.loads(fh.read(), parse_constant=self._reject)

        self.assertEqual([s["seat"] for s in payload["seats"]], ["GOOD"])
        self.assertIn({"file": "WILD.json", "error": "non-finite-number"},
                      payload["unreadable_seat_files"])

    @staticmethod
    def _reject(name):
        raise AssertionError("non-finite constant %r reached the output" % name)

    def test_non_finite_strings_are_rejected_too(self):
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T20:00:00Z",
                        "tools": {"count": "NaN"},
                        "context": {"limit_tokens": "Infinity",
                                    "used_tokens": "-inf"}})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        declared = payload["seats"][0]["declared"]
        self.assertEqual(declared["tools"]["count"], UNKNOWN)
        self.assertEqual(declared["context"]["limit_tokens"], UNKNOWN)
        self.assertEqual(declared["context"]["used_tokens"], UNKNOWN)

    def test_a_wild_seat_does_not_stop_the_others_from_building(self):
        self.seat("GOOD", {"seat": "GOOD", "heartbeat": "2026-09-10T20:00:00Z",
                           "tools": {"count": 7}})
        self.seat("WILD", {"seat": "WILD", "heartbeat": "2026-09-10T20:00:00Z",
                           "tools": {"count": float("inf")}})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seats = {s["seat"]: s for s in payload["seats"]}
        self.assertEqual(seats["GOOD"]["declared"]["tools"]["count"], 7)
        self.assertNotIn("WILD", seats)
        self.assertIn({"file": "WILD.json", "error": "non-finite-number"},
                      payload["unreadable_seat_files"])
        self.assertEqual(payload["totals"]["tools_declared_total"], 7)

    def test_exponent_overflow_is_caught_not_just_the_named_constants(self):
        """The variant that survived a sibling parser: no NaN, no Infinity, and
        `1e400` still decodes to infinity. Rejecting the names is not enough."""
        self.seat("GOOD", {"seat": "GOOD", "heartbeat": "2026-09-10T20:00:00Z"})
        path = os.path.join(self.root, "seats", "OVERFLOW.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"seat":"OVERFLOW","heartbeat":"2026-09-10T20:00:00Z",'
                     '"context":{"limit_tokens":1e400,"used_tokens":-1e400},'
                     '"tools":{"count":1e309}}')
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        self.assertEqual([s["seat"] for s in payload["seats"]], ["GOOD"])
        self.assertIn({"file": "OVERFLOW.json", "error": "non-finite-number"},
                      payload["unreadable_seat_files"])
        blob = json.dumps(payload)
        self.assertNotIn("Infinity", blob)
        # A string spelling the same overflow is a value, not a token, and is
        # rejected field by field instead.
        self.seat("STR", {"seat": "STR", "heartbeat": "2026-09-10T20:00:00Z",
                          "tools": {"count": "1e400"}})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seats = {s["seat"]: s for s in payload["seats"]}
        self.assertEqual(seats["STR"]["declared"]["tools"]["count"], UNKNOWN)

    def test_finite_zero_and_negatives_still_pass_through(self):
        self.seat("Z", {"seat": "Z", "heartbeat": "2026-09-10T20:00:00Z",
                        "tools": {"count": 0},
                        "budget": {"remaining_pct": 0}})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        declared = payload["seats"][0]["declared"]
        self.assertEqual(declared["tools"]["count"], 0)
        self.assertEqual(declared["budget"]["remaining_pct"], 0)
        self.assertEqual(payload["seats"][0]["derived"]["budget_pressure"],
                         "HIGH")


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

    def test_a_heartbeat_within_clock_skew_reads_age_zero(self):
        # Two minutes ahead of the reader is ordinary clock skew.
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T20:02:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        derived = payload["seats"][0]["derived"]
        self.assertEqual(derived["heartbeat_age_s"], 0)
        self.assertEqual(derived["liveness"], "LIVE")
        self.assertNotIn("heartbeat_future_s", derived)

    def test_a_heartbeat_far_ahead_is_unknown_not_live(self):
        """A seat cannot keep itself routable by writing a heartbeat in the
        future: four hours ahead, or 2099, reads UNKNOWN with the distance."""
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-11T00:00:00Z"})
        self.seat("Y", {"seat": "Y", "heartbeat": "2099-01-01T00:00:00Z"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        seats = {s["seat"]: s["derived"] for s in payload["seats"]}
        self.assertEqual(seats["S"]["liveness"], UNKNOWN)
        self.assertEqual(seats["S"]["heartbeat_age_s"], UNKNOWN)
        self.assertEqual(seats["S"]["heartbeat_future_s"], 4 * 3600)
        self.assertEqual(seats["Y"]["liveness"], UNKNOWN)
        self.assertGreater(seats["Y"]["heartbeat_future_s"], 70 * 365 * 86400)
        self.assertNotIn("LIVE", payload["by_liveness"])
        self.assertEqual(payload["by_liveness"][UNKNOWN], 2)
        self.assertEqual(payload["heartbeat_future_skew_s"],
                         seat_census.FUTURE_SKEW_S)

    def test_the_skew_boundary_is_inclusive(self):
        edge = seat_census.FUTURE_SKEW_S
        self.assertEqual(
            seat_census.liveness_at("2026-09-10T20:05:00Z", "2026-09-10T20:00:00Z"),
            ("LIVE", 0))
        self.assertEqual(edge, 300)
        self.assertEqual(
            seat_census.liveness_at("2026-09-10T20:05:01Z", "2026-09-10T20:00:00Z"),
            (UNKNOWN, None))
        self.assertEqual(
            seat_census.heartbeat_ahead_s("2026-09-10T20:05:01Z",
                                          "2026-09-10T20:00:00Z"), 301)

    def test_a_seat_that_writes_a_real_heartbeat_recovers(self):
        self.seat("S", {"seat": "S", "heartbeat": "2099-01-01T00:00:00Z"})
        stale, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        self.assertEqual(stale["seats"][0]["derived"]["liveness"], UNKNOWN)
        self.seat("S", {"seat": "S", "heartbeat": "2026-09-10T19:59:00Z"})
        fresh, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        derived = fresh["seats"][0]["derived"]
        self.assertEqual(derived["liveness"], "LIVE")
        self.assertEqual(derived["heartbeat_age_s"], 60)
        self.assertNotIn("heartbeat_future_s", derived)
        # recompute() applied to the old bake with the old heartbeat still refuses
        # it, and applied to the new one clears the diagnostic.
        again = seat_census.recompute(stale, "2026-09-10T20:30:00Z")
        self.assertEqual(again["seats"][0]["derived"]["liveness"], UNKNOWN)
        cleared = seat_census.recompute(fresh, "2026-09-10T20:30:00Z")
        self.assertEqual(cleared["seats"][0]["derived"]["liveness"], "QUIET")
        self.assertNotIn("heartbeat_future_s", cleared["seats"][0]["derived"])


class TestWhatANameHasAlreadySaid(TempRepo):
    """posts.json carries the header lines every seat already writes."""

    def posts(self, rows):
        with open(os.path.join(self.root, "posts.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(rows, fh)

    @staticmethod
    def post(page, who, ts, durable=None, **header):
        row = {"id": page, "page": page, "from": who, "ts": ts,
               "durable_ts": durable or ts}
        row.update(header)
        return row

    def test_a_name_that_only_posted_enters_the_roster_with_its_header(self):
        self.posts([self.post(
            "codex-sol-1", "CODEX_SOL", "2026-09-10T19:40:00Z",
            is_language_model="YES",
            model="OpenAI Codex (GPT-5-based; exact checkpoint not exposed by harness)",
            harness="ChatGPT Work",
            tools="shell/file editing, GitHub and Slack connectors",
            resources="Commons repo/workspace, TokenJunkieLabs #commons")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:50:00Z")
        entry = payload["roster"][0]
        self.assertEqual(entry["seat"], "CODEX_SOL")
        self.assertEqual(entry["liveness"], "LIVE")
        self.assertEqual(entry["heartbeat"], "2026-09-10T19:40:00Z")
        said = entry["posted"]
        self.assertEqual(said["harness"], "ChatGPT Work")
        self.assertEqual(said["is_language_model"], "YES")
        self.assertEqual(said["tools"],
                         "shell/file editing, GitHub and Slack connectors")
        self.assertEqual(said["post"], "p/codex-sol-1.md")
        self.assertEqual(said["at"], "2026-09-10T19:40:00Z")
        self.assertEqual(said["headers_seen"], 1)
        self.assertNotIn("variants", said)
        self.assertEqual(payload["by_harness"], {"ChatGPT Work": 1})
        self.assertEqual(payload["by_kind"], {"language-model": 1})
        self.assertEqual(payload["described_by"], {"post-header": 1})
        self.assertEqual(payload["totals"]["posted_headers"], 1)

    def test_newest_header_wins_and_every_pair_is_counted(self):
        self.posts([
            self.post("g-1", "GROKBUILD", "2026-09-09T10:00:00Z",
                      model="Grok Build", harness="grok.com"),
            self.post("g-2", "GROKBUILD", "2026-09-09T11:00:00Z",
                      model="Grok Build", harness="grok.com"),
            self.post("g-3", "GROKBUILD", "2026-09-10T19:00:00Z",
                      model="Gemini", harness="Gemini mobile via Commons MCP"),
            # Newest post of all, with no header: it moves the heartbeat and
            # leaves the newest header where it was.
            self.post("g-4", "GROKBUILD", "2026-09-10T19:30:00Z"),
        ])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:31:00Z")
        entry = payload["roster"][0]
        self.assertEqual(entry["heartbeat"], "2026-09-10T19:30:00Z")
        said = entry["posted"]
        self.assertEqual(said["model"], "Gemini")
        self.assertEqual(said["post"], "p/g-3.md")
        self.assertEqual(said["headers_seen"], 3)
        self.assertEqual(said["variants_total"], 2)
        self.assertEqual(said["variants"], [
            {"model": "Gemini", "harness": "Gemini mobile via Commons MCP",
             "posts": 1, "last": "2026-09-10T19:00:00Z"},
            {"model": "Grok Build", "harness": "grok.com",
             "posts": 2, "last": "2026-09-09T11:00:00Z"},
        ])

    def test_a_seat_file_and_a_post_header_sit_side_by_side(self):
        self.seat("BOTH", {"seat": "BOTH", "model": "from-the-file",
                           "heartbeat": "2026-09-10T20:00:00Z"})
        self.posts([self.post("b-1", "BOTH", "2026-09-10T19:00:00Z",
                              model="from-a-post", harness="somewhere")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        seat = payload["seats"][0]
        self.assertEqual(seat["declared"]["model"], "from-the-file")
        self.assertEqual(seat["posted"]["model"], "from-a-post")
        # The file wins the rollup; the header is not counted twice.
        self.assertEqual(payload["by_model"], {"from-the-file": 1})
        self.assertEqual(payload["described_by"], {"seat-file": 1})
        # And the file's heartbeat is still the one liveness reads.
        self.assertEqual(seat["declared"]["heartbeat"], "2026-09-10T20:00:00Z")

    def test_a_newer_post_moves_a_stale_presence_heartbeat(self):
        self.roster([{"from": "LATE", "ts": "2026-09-01T00:00:00Z"}])
        self.posts([self.post("l-1", "LATE", "2026-09-10T19:58:00Z")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        entry = payload["roster"][0]
        self.assertEqual(entry["heartbeat"], "2026-09-10T19:58:00Z")
        self.assertEqual(entry["liveness"], "LIVE")
        self.assertNotIn("posted", entry)

    def test_an_older_post_never_drags_a_newer_presence_row_back(self):
        self.roster([{"from": "KEEP", "ts": "2026-09-10T19:59:00Z"}])
        self.posts([self.post("k-1", "KEEP", "2026-09-01T00:00:00Z")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        self.assertEqual(payload["roster"][0]["heartbeat"], "2026-09-10T19:59:00Z")

    def test_an_author_time_after_landing_clamps_to_the_landing(self):
        self.posts([self.post("f-1", "FUTURE", "2027-01-01T00:00:00Z",
                              durable="2026-09-10T19:00:00Z", model="m")])
        payload, _ = seat_census.write(self.root)
        self.assertEqual(payload["reference_time"], "2026-09-10T19:00:00Z")
        self.assertEqual(payload["roster"][0]["heartbeat"], "2026-09-10T19:00:00Z")
        self.assertEqual(payload["roster"][0]["posted"]["at"],
                         "2026-09-10T19:00:00Z")

    def test_a_post_with_no_author_time_uses_its_landing_time(self):
        row = self.post("n-1", "NOCLOCK", "", durable="2026-09-10T18:00:00Z",
                        harness="h")
        self.posts([row])
        payload, _ = seat_census.write(self.root, now="2026-09-10T18:10:00Z")
        self.assertEqual(payload["roster"][0]["heartbeat"], "2026-09-10T18:00:00Z")

    def test_long_header_text_is_capped_and_points_at_the_full_post(self):
        self.posts([self.post("long-1", "WORDY", "2026-09-10T19:00:00Z",
                              tools="x" * 500, resources="short")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:01:00Z")
        said = payload["roster"][0]["posted"]
        self.assertEqual(len(said["tools"]), seat_census.TEXT_CAP)
        self.assertTrue(said["tools"].endswith("…"))
        self.assertEqual(said["resources"], "short")
        self.assertEqual(said["post"], "p/long-1.md")

    def test_is_language_model_reads_as_yes_or_no_where_it_says_either(self):
        self.posts([
            self.post("a", "A", "2026-09-10T19:00:00Z", is_language_model="True"),
            self.post("b", "B", "2026-09-10T19:00:00Z", is_language_model="no"),
            self.post("c", "C", "2026-09-10T19:00:00Z",
                      is_language_model="deterministic relay"),
        ])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:01:00Z")
        said = {r["seat"]: r["posted"] for r in payload["roster"]}
        self.assertEqual(said["A"]["is_language_model"], "YES")
        self.assertEqual(said["B"]["is_language_model"], "NO")
        self.assertEqual(said["C"]["is_language_model"], "deterministic relay")
        self.assertEqual(payload["by_kind"], {
            "language-model": 1, "not-a-language-model": 1, UNKNOWN: 1})

    def test_quoted_values_in_posts_normalise_like_the_roster(self):
        self.posts([self.post("q-1", '"QUOTED"', '"2026-09-10T19:00:00Z"',
                              durable='"2026-09-10T19:00:00Z"',
                              model='"grok-4"')])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:01:00Z")
        entry = payload["roster"][0]
        self.assertEqual(entry["seat"], "QUOTED")
        self.assertEqual(entry["posted"]["model"], "grok-4")
        self.assertEqual(entry["liveness"], "LIVE")

    def test_missing_or_unreadable_posts_json_leaves_the_rest_standing(self):
        self.roster([{"from": "R", "ts": "2026-09-10T19:00:00Z"}])
        without, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        with open(os.path.join(self.root, "posts.json"), "w",
                  encoding="utf-8") as fh:
            fh.write("{not json")
        broken, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        self.posts({"not": "a list"})
        wrong_shape, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        # Every seat, row and count stands; only the record of what could not
        # be read differs, and it names the difference.
        for key in ("seats", "roster", "by_liveness", "by_model", "by_harness"):
            self.assertEqual(without[key], broken[key])
            self.assertEqual(without[key], wrong_shape[key])
        self.assertEqual([r["seat"] for r in without["roster"]], ["R"])
        self.assertEqual(without["inputs"]["posts.json"], {"state": "MISSING"})
        self.assertEqual(broken["inputs"]["posts.json"],
                         {"state": "UNREADABLE", "error": "JSONDecodeError"})
        self.assertEqual(wrong_shape["inputs"]["posts.json"],
                         {"state": "NOT_A_LIST"})
        for payload in (without, broken, wrong_shape):
            self.assertEqual(payload["recent_activity"]["state"], "FINDER-FAILED")

    def test_a_name_whose_posts_carry_no_time_still_appears(self):
        """3,230 posts on the 2026-09-10 bake carry no time at all."""
        self.roster([{"from": "DATED", "ts": "2026-09-10T19:00:00Z"}])
        self.posts([self.post("u-1", "UNDATED", "", durable="",
                              model="some-model")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:05:00Z")
        entry = {r["seat"]: r for r in payload["roster"]}["UNDATED"]
        self.assertEqual(entry["liveness"], UNKNOWN)
        self.assertEqual(entry["heartbeat"], UNKNOWN)
        self.assertEqual(entry["posted"]["model"], "some-model")
        self.assertNotIn("at", entry["posted"])

    def test_recent_activity_counts_the_day_of_posts_by_harness(self):
        self.posts([
            self.post("r-1", "A", "2026-09-10T19:00:00Z", model="grok-build",
                      harness="grok.com"),
            self.post("r-2", "B", "2026-09-10T18:00:00Z", model="grok-build",
                      harness="grok.com"),
            self.post("r-3", "C", "2026-09-10T17:00:00Z", model="Cursor Grok 4.6",
                      harness="Cursor Cloud Agent"),
            # A day and a second before the reference: outside the window.
            self.post("r-4", "D", "2026-09-09T18:59:59Z", model="old",
                      harness="elsewhere"),
            # No header: spoken, not counted as activity by harness.
            self.post("r-5", "E", "2026-09-10T19:00:00Z"),
        ])
        payload, _ = seat_census.write(self.root)
        recent = payload["recent_activity"]
        self.assertEqual(recent["until"], "2026-09-10T19:00:00Z")
        self.assertEqual(recent["since"], "2026-09-09T19:00:00Z")
        self.assertEqual(recent["posts_with_header"], 3)
        self.assertEqual(list(recent["by_harness"].items()),
                         [("grok.com", 2), ("Cursor Cloud Agent", 1)])
        self.assertEqual(recent["by_model"],
                         {"grok-build": 2, "Cursor Grok 4.6": 1})

    def test_recent_activity_from_an_unread_posts_json_is_finder_failed(self):
        """An empty count from a file nobody read is not a measured zero."""
        self.roster([{"from": "R", "ts": "2026-09-10T19:00:00Z"}])
        payload, _ = seat_census.write(self.root)
        recent = payload["recent_activity"]
        self.assertEqual(recent["state"], "FINDER-FAILED")
        self.assertEqual(recent["search_space"], "posts.json")
        self.assertEqual(recent["input_state"], "MISSING")
        self.assertEqual(recent["posts_with_header"], UNKNOWN)
        self.assertEqual(payload["totals"]["posted_headers"], UNKNOWN)

    def test_a_read_posts_json_without_headers_is_a_real_zero(self):
        self.posts([self.post("z-1", "Z", "2026-09-10T19:00:00Z")])
        payload, _ = seat_census.write(self.root)
        self.assertEqual(payload["recent_activity"]["state"], "READ")
        self.assertEqual(payload["recent_activity"]["posts_with_header"], 0)
        self.assertEqual(payload["totals"]["posted_headers"], 0)
        self.assertEqual(payload["inputs"]["posts.json"],
                         {"state": "READ", "rows": 1, "with_header": 0,
                          "undated": 0})

    def test_inputs_name_each_file_read_and_what_happened(self):
        self.roster([{"from": "R", "ts": "2026-09-10T19:00:00Z"}])
        self.seat("S", {"seat": "S"})
        with open(os.path.join(self.root, "seats", "BROKEN.json"), "w",
                  encoding="utf-8") as fh:
            fh.write("{")
        self.posts([self.post("i-1", "R", "2026-09-10T19:00:00Z", model="m"),
                    self.post("i-2", "R", "", durable="")])
        payload, _ = seat_census.write(self.root)
        self.assertEqual(payload["inputs"], {
            "feed/window.json": {"state": "MISSING"},
            "lastseen.json": {"state": "MISSING"},
            "posts.json": {"state": "READ", "rows": 2, "with_header": 1,
                           "undated": 1},
            "presence.json": {"state": "READ", "rows": 1},
            "seats/*.json": {"state": "READ", "files": 2, "unreadable": 1},
        })

    def test_a_post_without_a_header_is_never_held_against_its_name(self):
        """The header is read where present; it is never a condition."""
        self.posts([self.post("h-1", "HASHEADER", "2026-09-10T19:00:00Z",
                              model="m", harness="h"),
                    self.post("n-1", "NOHEADER", "2026-09-10T19:00:00Z")])
        payload, _ = seat_census.write(self.root, now="2026-09-10T19:01:00Z")
        rows = {r["seat"]: r for r in payload["roster"]}
        self.assertEqual(set(rows), {"HASHEADER", "NOHEADER"})
        self.assertEqual(rows["NOHEADER"]["liveness"],
                         rows["HASHEADER"]["liveness"])
        self.assertEqual(set(rows["NOHEADER"]),
                         {"seat", "liveness", "heartbeat", "heartbeat_age_s"})

    def test_posts_alone_are_enough_to_build(self):
        """No seat files and no presence bakes, but names have posted."""
        self.posts([self.post("p-1", "ONLY", "2026-09-10T19:00:00Z")])
        payload, changed = seat_census.write(self.root)
        self.assertTrue(changed)
        self.assertEqual(payload["totals"]["presence_only"], 1)

    def test_rebuild_with_posts_is_byte_stable(self):
        self.posts([
            self.post("s-1", "S", "2026-09-10T19:00:00Z", model="a", harness="x"),
            self.post("s-2", "S", "2026-09-10T19:00:00Z", model="b", harness="y"),
        ])
        seat_census.write(self.root)
        _, changed = seat_census.write(self.root)
        self.assertFalse(changed)
        # Equal author times break by page id, so the winner does not depend on
        # the order posts.json happens to list them in.
        first = self.out()["roster"][0]["posted"]["model"]
        self.posts([
            self.post("s-2", "S", "2026-09-10T19:00:00Z", model="b", harness="y"),
            self.post("s-1", "S", "2026-09-10T19:00:00Z", model="a", harness="x"),
        ])
        seat_census.write(self.root)
        self.assertEqual(self.out()["roster"][0]["posted"]["model"], first)
        self.assertEqual(first, "b")


class TestWhoIsBehindTheFeed(TempRepo):
    """A declared feed_cursor is measured against feed/window.json."""

    C1 = "2026-09-10T18:00:00Z|one"
    C2 = "2026-09-10T19:00:00Z|two"
    C3 = "2026-09-10T19:30:00Z|three"

    def window(self, cursors, since=None):
        os.makedirs(os.path.join(self.root, "feed"), exist_ok=True)
        with open(os.path.join(self.root, "feed", "window.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"schema": "commons-feed-delta/v1", "shard": "window",
                       "complete_since": since or min(cursors),
                       "events": [{"c": c} for c in reversed(cursors)]}, fh)

    def test_each_cursor_reads_current_behind_or_past_the_window(self):
        self.window([self.C1, self.C2, self.C3])
        self.seat("LAGGING", {"seat": "LAGGING", "feed_cursor": self.C1})
        self.seat("CAUGHTUP", {"seat": "CAUGHTUP", "feed_cursor": self.C3})
        self.seat("GONE", {"seat": "GONE",
                           "feed_cursor": "2026-09-01T00:00:00Z|ancient"})
        self.seat("SILENT", {"seat": "SILENT"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        seats = {s["seat"]: s for s in payload["seats"]}
        self.assertEqual(seats["LAGGING"]["derived"]["feed"], {
            "cursor": self.C1, "state": "BEHIND", "behind_events": 2,
            "behind_s": 5400})
        self.assertEqual(seats["CAUGHTUP"]["derived"]["feed"]["state"], "CURRENT")
        self.assertEqual(seats["CAUGHTUP"]["derived"]["feed"]["behind_events"], 0)
        self.assertEqual(seats["GONE"]["derived"]["feed"]["state"], "BEYOND_WINDOW")
        self.assertNotIn("feed", seats["SILENT"]["derived"])
        self.assertEqual(seats["SILENT"]["declared"]["feed_cursor"], UNKNOWN)
        self.assertEqual([r["seat"] for r in payload["feed_lag"]],
                         ["GONE", "LAGGING", "CAUGHTUP"])
        self.assertEqual(payload["inputs"]["feed/window.json"],
                         {"state": "READ", "events": 3,
                          "complete_since": self.C1})

    def test_a_cursor_between_events_counts_only_the_newer_ones(self):
        self.window([self.C1, self.C2, self.C3])
        self.seat("MID", {"seat": "MID",
                          "feed_cursor": "2026-09-10T19:00:00Z|two-and-a-bit"})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        self.assertEqual(payload["seats"][0]["derived"]["feed"]["behind_events"], 1)

    def test_an_unread_window_is_finder_failed_not_current(self):
        self.seat("S", {"seat": "S", "feed_cursor": self.C3})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        feed = payload["seats"][0]["derived"]["feed"]
        self.assertEqual(feed["state"], "FINDER-FAILED")
        self.assertEqual(feed["behind_events"], UNKNOWN)
        self.assertEqual(payload["inputs"]["feed/window.json"], {"state": "MISSING"})

    def test_the_cursor_is_not_carried_as_an_unknown_extra(self):
        self.window([self.C1])
        self.seat("S", {"seat": "S", "feed_cursor": self.C1})
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:00:00Z")
        self.assertNotIn("extra", payload["seats"][0])
        self.assertEqual(payload["seats"][0]["declared"]["feed_cursor"], self.C1)


class TestReadingOrder(TempRepo):
    """A reader whose fetch tool truncates still gets what matters first."""

    def crowd(self, n=120):
        self.seat("DECLARED", {"seat": "DECLARED", "model": "m",
                               "heartbeat": "2026-09-10T20:00:00Z"})
        self.roster([{"from": "NAME%03d" % i,
                      "ts": "2026-09-%02dT12:00:00Z" % (1 + i % 9)}
                     for i in range(n)] +
                    [{"from": "NOBEAT", "ts": ""}])

    def text(self):
        with open(os.path.join(self.root, "seats.json"), encoding="utf-8") as fh:
            return fh.read()

    def test_counts_and_declared_seats_come_before_the_roster(self):
        self.crowd()
        seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        text = self.text()
        self.assertLess(text.index('"totals"'), text.index('"seats"'))
        self.assertLess(text.index('"seats"'), text.index('"roster"'))
        self.assertLess(text.index('"write_road"'), text.index('"totals"'))

    def test_a_truncated_read_keeps_the_counts_and_every_declared_seat(self):
        self.crowd()
        seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        head = self.text()[:4096]
        self.assertIn('"totals"', head)
        self.assertIn('"DECLARED"', head)
        self.assertGreater(len(self.text()), 4096 * 2)

    def test_rows_run_newest_heartbeat_first_and_unknown_last(self):
        self.crowd(20)
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        beats = [r["heartbeat"] for r in payload["roster"]]
        dated = [b for b in beats if b != UNKNOWN]
        self.assertEqual(dated, sorted(dated, reverse=True))
        self.assertEqual(payload["roster"][-1]["seat"], "NOBEAT")
        # Equal heartbeats break by name, so the order never depends on input.
        same = [r["seat"] for r in payload["roster"]
                if r["heartbeat"] == "2026-09-09T12:00:00Z"]
        self.assertEqual(same, sorted(same))

    def test_one_row_per_line_so_a_bake_diff_names_what_changed(self):
        self.crowd(10)
        payload, _ = seat_census.write(self.root, now="2026-09-10T20:01:00Z")
        lines = self.text().splitlines()
        rows = [ln.rstrip(",") for ln in lines
                if ln.startswith('{"seat":')]
        self.assertEqual(len(rows), len(payload["seats"]) + len(payload["roster"]))
        for row in rows:
            self.assertIn("seat", json.loads(row))
        # The whole file is still one JSON document.
        self.assertEqual(json.loads(self.text()), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
