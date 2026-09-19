#!/usr/bin/env python3
"""Tests for the UIOWA-105D unit vocabulary resolver.

The rule under test: a unit resolves only when both its measure and its period
are written down. Spelling differences (person/staff, underscore/hyphen) are
normalised; an unstated period is never read as one-time.
"""

import os
import unittest

import integrate
import units as u
from ledgers import ALL_LEDGERS

REVENUE = (integrate.find_component("uiowa_rfq_18649_readout_deck") or "")
REVENUE = os.path.dirname(REVENUE) if REVENUE else ""
HAVE_TREE = bool(REVENUE and os.path.isdir(REVENUE))
WHY = ("needs the sibling lanes; set UIOWA_REPO_ROOT to the revenue/ "
       "directory when running from a staging copy")


class SpellingTests(unittest.TestCase):

    def test_snake_case_and_hyphenated_spellings_are_the_same_quantity(self):
        verdict, detail = u.units_equivalent("person_hours_per_month",
                                             "staff-hours per month")
        self.assertEqual(verdict, u.EQUIVALENT, detail)

    def test_person_and_staff_and_people_all_read_as_staff_hours(self):
        for raw in ("person_hours_per_month", "staff-hours per month",
                    "people hours per month", "man-hours per month"):
            parsed = u.parse_unit(raw)
            self.assertEqual(parsed["measure"], u.M_HOURS, raw)
            self.assertEqual(parsed["period"], u.P_MONTH, raw)

    def test_underscore_does_not_hide_the_measure(self):
        """Regression: \\b treats '_' as a word character, so \\bhours?\\b never
        matched inside person_hours_per_month -- the exact snake_case spelling
        this module exists to normalise."""
        self.assertEqual(u.parse_unit("person_hours")["measure"], u.M_HOURS)
        self.assertEqual(u.parse_unit("effort_hours")["measure"], u.M_HOURS)


class UnstatedPeriodTests(unittest.TestCase):

    def test_a_bare_hours_unit_is_not_read_as_one_time(self):
        parsed = u.parse_unit("staff-hours")
        self.assertEqual(parsed["period"], u.P_UNSTATED)
        self.assertNotEqual(parsed["period"], u.P_ONE_TIME)
        self.assertFalse(parsed["resolved"])
        self.assertIn("into a one-off cost", parsed["note"])

    def test_unstated_period_gives_unresolved_not_equivalent_or_different(self):
        verdict, detail = u.units_equivalent("staff-hours", "staff-hours per month")
        self.assertEqual(verdict, u.UNRESOLVED, detail)
        self.assertIn("does not state a period", detail)

    def test_equivalent_is_never_returned_when_a_period_is_unstated(self):
        vague = ("hours", "staff-hours", "person_hours", "effort_hours", "")
        stated = ("staff-hours per month", "FTE-fraction per year",
                  "staff-hours one-time")
        for a in vague:
            for b in stated + vague:
                verdict, _ = u.units_equivalent(a, b)
                self.assertNotEqual(verdict, u.EQUIVALENT, "%r vs %r" % (a, b))

    def test_an_explicit_one_time_marker_does_resolve(self):
        parsed = u.parse_unit("hours (one-time implementation)")
        self.assertEqual(parsed["period"], u.P_ONE_TIME)
        self.assertTrue(parsed["resolved"])


class ComparisonTests(unittest.TestCase):

    def test_same_measure_different_period_is_different(self):
        verdict, detail = u.units_equivalent("staff-hours per month",
                                             "staff-hours per year")
        self.assertEqual(verdict, u.DIFFERENT, detail)

    def test_fte_and_hours_are_convertible_and_say_the_constant_is_missing(self):
        verdict, detail = u.units_equivalent("FTE-fraction per year",
                                             "staff-hours per month")
        self.assertEqual(verdict, u.CONVERTIBLE)
        self.assertIn("has not been supplied", detail)
        self.assertIn("no agreement is claimed", detail)

    def test_supplying_the_constant_names_it(self):
        verdict, detail = u.units_equivalent("FTE-fraction per year",
                                             "staff-hours per month", 2080.0)
        self.assertEqual(verdict, u.CONVERTIBLE)
        self.assertIn("2080", detail)

    def test_currency_and_hours_are_different(self):
        verdict, _ = u.units_equivalent("currency (one-time)",
                                        "hours (one-time implementation)")
        self.assertEqual(verdict, u.DIFFERENT)

    def test_empty_or_none_does_not_crash(self):
        for raw in (None, "", "   "):
            verdict, _ = u.units_equivalent(raw, "staff-hours per month")
            self.assertEqual(verdict, u.UNRESOLVED)


class VocabularyTests(unittest.TestCase):

    def test_two_spellings_of_one_quantity_group_together(self):
        out = u.resolve_vocabulary({
            "adoption_readiness": ["person_hours_per_month"],
            "readout_deck": ["staff-hours per month"]})
        monthly = [q for q in out["quantities"]
                   if q["quantity"] == "staff-hours per month"]
        self.assertEqual(len(monthly), 1)
        self.assertEqual(monthly[0]["spelling_count"], 2)
        self.assertEqual(monthly[0]["components"],
                         ["adoption_readiness", "readout_deck"])

    def test_a_measure_denominator_is_out_of_scope_not_an_unresolved_unit(self):
        """Regression: counting 'of 12 sampled changes' as an unresolved unit
        overstated the finding from 4 to 26."""
        out = u.resolve_vocabulary({"deck": ["of 12 sampled changes",
                                             "findings carrying a target",
                                             "staff-hours"]})
        self.assertEqual(out["out_of_scope_count"], 2)
        self.assertEqual([x["unit"] for x in out["unresolved"]], ["staff-hours"])

    def test_this_lane_s_own_ledger_units_all_resolve(self):
        out = u.resolve_vocabulary({"this_lane": list(ALL_LEDGERS)})
        self.assertEqual(out["unresolved"], [])
        self.assertEqual(out["out_of_scope_count"], 0)

    def test_render_lists_unresolved_units_and_the_no_inference_rule(self):
        out = u.resolve_vocabulary({"a": ["staff-hours", "staff-hours per month"]})
        text = u.render_vocabulary(out)
        self.assertIn("do not state a period", text)
        self.assertIn("not read as one-time", text)


@unittest.skipUnless(HAVE_TREE, WHY)
class AgainstLandedLanesTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.observed = u.observed_units_in_tree(REVENUE)
        cls.observed["uiowa_rfq_18649_economics_resource_adapters"] = list(ALL_LEDGERS)
        cls.resolved = u.resolve_vocabulary(cls.observed)

    def test_the_scan_finds_units_in_more_than_one_lane(self):
        self.assertGreater(len(self.observed), 1)

    def test_the_two_monthly_spellings_in_landed_lanes_are_one_quantity(self):
        monthly = [q for q in self.resolved["quantities"]
                   if q["quantity"] == "staff-hours per month"]
        self.assertEqual(len(monthly), 1)
        self.assertGreaterEqual(monthly[0]["spelling_count"], 2)

    def test_bare_hours_units_in_landed_lanes_stay_unresolved(self):
        unresolved = {x["unit"] for x in self.resolved["unresolved"]}
        self.assertTrue(unresolved, "landed lanes must exercise this")
        for unit in unresolved:
            self.assertEqual(u.parse_unit(unit)["period"], u.P_UNSTATED, unit)

    def test_the_scan_reads_only_and_reports_every_component_it_read(self):
        for component, unit_list in self.observed.items():
            self.assertTrue(component.startswith("uiowa_rfq_18649_"), component)
            self.assertTrue(unit_list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
