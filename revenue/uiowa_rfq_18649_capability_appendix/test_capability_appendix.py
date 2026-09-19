#!/usr/bin/env python3
"""Tests for the UIOWA-137 capability appendix generator.

The ones that matter are the ones that would fail if an unbacked claim could
ever reach the appendix body:

  * a claim with no observed run must not print as a capability
  * a claim whose artifact changed after it was demonstrated must demote itself
  * a claim whose wording asserts quality without offering anything to check
    must be rejected rather than softened
  * going over the page budget must be reported, never fixed by dropping a claim

Run:  python3 -m unittest -v test_capability_appendix
"""

import json
import os
import shutil
import tempfile
import unittest

import capability_appendix as ca


HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER = os.path.join(HERE, "capabilities.json")
OBSERVATIONS = os.path.join(HERE, "observed_runs.json")
DEMO_REGISTER = os.path.join(HERE, "fixtures", "rejection_demo_register.json")
DEMO_OBSERVATIONS = os.path.join(HERE, "fixtures", "rejection_demo_observations.json")
# Resolve artifact paths against the repository root. In this workspace the
# checkout lives at /home/user/commons; in a plain checkout the lane sits two
# levels below the root, which is what DEFAULT_BASE computes.
REPO_BASE = ("/home/user/commons" if os.path.isdir("/home/user/commons/revenue")
             else ca.DEFAULT_BASE)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def evaluate(register_path, observations_path, base):
    return ca.evaluate(load(register_path), load(observations_path), base)


class RejectionGuards(unittest.TestCase):
    """Every guard fires, and each names its own reason."""

    @classmethod
    def setUpClass(cls):
        demo, notdemo = evaluate(DEMO_REGISTER, DEMO_OBSERVATIONS, HERE)
        cls.demonstrated = demo
        cls.blocked = {c["claim_id"]: c for c in notdemo}

    def test_nothing_in_the_broken_fixture_is_demonstrated(self):
        self.assertEqual(self.demonstrated, [])
        self.assertEqual(len(self.blocked), 7)

    def test_marketing_adjective_is_rejected(self):
        blockers = " ".join(self.blocked["BAD-01"]["blockers"])
        self.assertIn("marketing language", blockers)
        self.assertIn("robust", blockers)
        self.assertIn("seamlessly", blockers)

    def test_certification_and_guarantee_language_is_rejected(self):
        blockers = " ".join(self.blocked["BAD-02"]["blockers"])
        self.assertIn("certified", blockers)
        self.assertIn("compliant", blockers)
        self.assertIn("guaranteed", blockers)

    def test_missing_artifact_file_blocks_and_names_the_file(self):
        blockers = " ".join(self.blocked["BAD-03"]["blockers"])
        self.assertIn("tool_that_does_not_exist.py", blockers)

    def test_absent_observation_blocks(self):
        self.assertIn("no observed run recorded",
                      " ".join(self.blocked["BAD-04"]["blockers"]))

    def test_nonzero_exit_blocks(self):
        self.assertIn("exited 2", " ".join(self.blocked["BAD-05"]["blockers"]))

    def test_digest_drift_blocks_and_says_why(self):
        blockers = " ".join(self.blocked["BAD-06"]["blockers"])
        self.assertIn("changed since it was demonstrated", blockers)
        self.assertIn("capability_appendix.py", blockers)

    def test_instruction_pointing_outside_the_claim_blocks(self):
        blockers = " ".join(self.blocked["BAD-07"]["blockers"])
        self.assertIn("some_other_script.py", blockers)
        self.assertIn("does not cite", blockers)

    def test_every_blocked_claim_states_a_reason(self):
        for claim_id, claim in self.blocked.items():
            self.assertTrue(claim["blockers"],
                            "%s was blocked with no reason given" % claim_id)

    def test_no_blocked_statement_reaches_the_appendix_body(self):
        register = load(DEMO_REGISTER)
        text = ca.render_appendix(register, [], list(self.blocked.values()))
        for claim in self.blocked.values():
            self.assertNotIn(claim["statement"], text,
                             "%s's statement leaked into the body"
                             % claim["claim_id"])


class LanguageCheck(unittest.TestCase):

    def test_word_boundaries_do_not_produce_false_positives(self):
        # 'complaint' is not 'compliant'; 'descale' is not 'scalable'.
        self.assertEqual(ca.language_violations("A complaint was logged."), [])
        self.assertEqual(ca.language_violations("Descale the equipment."), [])
        self.assertEqual(ca.language_violations("Robustness testing."), [])

    def test_banned_terms_fire_regardless_of_case(self):
        self.assertTrue(ca.language_violations("A ROBUST approach"))
        self.assertTrue(ca.language_violations("Seamlessly integrated"))

    def test_unquantified_intensifier_is_rejected(self):
        found = ca.language_violations("significantly faster")
        self.assertIn("unquantified intensifier", [c for c, _t in found])

    def test_business_use_is_checked_not_just_the_statement(self):
        claim = {
            "statement": "Records are indexed by an offline tool.",
            "business_use": "Delivers guaranteed retention.",
            "artifact_paths": ["capability_appendix.py"],
            "demonstration": {"cwd": ".", "command": "python3 capability_appendix.py"},
        }
        ok, blockers, _detail = ca.bind_claim(claim, None, HERE)
        self.assertFalse(ok)
        self.assertTrue(any("guaranteed" in b for b in blockers))

    def test_the_real_appendix_passes_its_own_language_check(self):
        demo, notdemo = evaluate(REGISTER, OBSERVATIONS, REPO_BASE)
        text = ca.render_appendix(load(REGISTER), demo, notdemo)
        self.assertEqual(ca.language_violations(text), [],
                         "the generated appendix contains language it would "
                         "reject in a claim")


class CommandTargets(unittest.TestCase):

    def test_direct_script_invocation(self):
        self.assertEqual(ca.command_targets("python3 validate_trace.py"),
                         ["validate_trace.py"])

    def test_unittest_module_invocation(self):
        self.assertEqual(ca.command_targets("python3 -m unittest test_closeout"),
                         ["test_closeout.py"])

    def test_unittest_itself_is_not_treated_as_a_target(self):
        self.assertNotIn("unittest.py",
                         ca.command_targets("python3 -m unittest test_x"))

    def test_verbose_flag_is_not_treated_as_a_target(self):
        self.assertEqual(ca.command_targets("python3 -m unittest -v test_x"),
                         ["test_x.py"])


class RealRegister(unittest.TestCase):
    """The shipped register, bound against the actual repository."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(REPO_BASE):
            raise unittest.SkipTest("repository base %s not present" % REPO_BASE)
        cls.demonstrated, cls.not_demonstrated = evaluate(
            REGISTER, OBSERVATIONS, REPO_BASE)

    def test_five_claims_are_demonstrated(self):
        self.assertEqual(len(self.demonstrated), 5)

    def test_the_unrun_claim_is_held_back(self):
        ids = [c["claim_id"] for c in self.not_demonstrated]
        self.assertEqual(ids, ["CAP-06"])
        self.assertIn("no executable demonstration command",
                      " ".join(self.not_demonstrated[0]["blockers"]))

    def test_all_four_capability_areas_are_covered(self):
        areas = {c["capability_area"] for c in self.demonstrated}
        for area in ("evidence organization", "traceability", "comparison",
                     "report preparation"):
            self.assertIn(area, areas)

    def test_every_demonstrated_claim_carries_verbatim_output(self):
        for claim in self.demonstrated:
            output = claim["bind_detail"].get("output_verbatim") or ""
            self.assertTrue(output.strip(),
                            "%s has no output to show" % claim["claim_id"])
            self.assertEqual(claim["bind_detail"]["exit_code"], 0)

    def test_claims_span_both_swarms(self):
        # The appendix cites artifacts from GPT seats and Claude seats alike;
        # the binding rule is the same for both.
        seats = " ".join(c.get("contributing_seat", "") for c in self.demonstrated)
        self.assertIn("GPT", seats)
        self.assertIn("Claude", seats)

    def test_reported_commits_are_marked_as_unverified(self):
        # A SHA copied from a channel message is not evidence this seat
        # produced. It must never be presented as verified.
        for claim in self.demonstrated + self.not_demonstrated:
            status = claim.get("reported_commit_status", "")
            self.assertIn("not independently verified", status)

    def test_appendix_fits_its_stated_page_budget(self):
        text = ca.render_appendix(load(REGISTER), self.demonstrated,
                                  self.not_demonstrated)
        budget = ca.budget_check(load(REGISTER), text)
        self.assertTrue(budget["within_budget"],
                        "appendix is %d words over" % budget["over_by"])
        self.assertLessEqual(budget["estimated_pages"], 2.0)


class Budget(unittest.TestCase):

    def test_over_budget_is_reported_and_no_claim_is_dropped(self):
        register = load(REGISTER)
        register["page_budget"] = {"pages": 1, "words_per_page": 50}
        demo, notdemo = evaluate(REGISTER, OBSERVATIONS, REPO_BASE)
        text = ca.render_appendix(register, demo, notdemo)
        budget = ca.budget_check(register, text)
        self.assertFalse(budget["within_budget"])
        self.assertGreater(budget["over_by"], 0)
        # The document must still contain every demonstrated claim. Silently
        # truncating to fit is the failure this guard exists to prevent.
        for claim in demo:
            self.assertIn(claim["claim_id"], text)

    def test_word_count_ignores_blank_padding(self):
        self.assertEqual(ca.count_words("  a   b \n\n c  "), 3)


class BuildIsPure(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_executes_nothing(self):
        # A register whose command would create a file. If build ever executed
        # a demonstration, the marker would appear.
        marker = os.path.join(self.tmp, "SHOULD_NOT_EXIST")
        register = {
            "page_budget": {"pages": 2, "words_per_page": 500},
            "claims": [{
                "claim_id": "X1", "capability_area": "test",
                "statement": "A tool writes a record.",
                "business_use": "A record is written.",
                "artifact_dir": ".", "artifact_paths": ["marker.py"],
                "demonstration": {"cwd": ".",
                                  "command": "python3 marker.py"},
            }],
        }
        with open(os.path.join(self.tmp, "marker.py"), "w") as handle:
            handle.write("open(%r, 'w').write('x')\n" % marker)
        reg_path = os.path.join(self.tmp, "reg.json")
        with open(reg_path, "w") as handle:
            json.dump(register, handle)
        obs_path = os.path.join(self.tmp, "obs.json")
        with open(obs_path, "w") as handle:
            json.dump({"observations": []}, handle)

        ca.main(["--register", reg_path, "--observations", obs_path,
                 "--base", self.tmp, "build", "--outdir",
                 os.path.join(self.tmp, "out"), "--quiet"])
        self.assertFalse(os.path.exists(marker),
                         "build executed a demonstration command")

    def test_build_with_no_observations_file_demotes_everything(self):
        code = ca.main(["--register", REGISTER,
                        "--observations", os.path.join(self.tmp, "absent.json"),
                        "--base", REPO_BASE, "build",
                        "--outdir", os.path.join(self.tmp, "out"), "--quiet"])
        self.assertEqual(code, 0)
        result = load(os.path.join(self.tmp, "out", "capability_appendix.json"))
        self.assertEqual(result["demonstrated"], [])
        self.assertEqual(len(result["not_demonstrated"]), 6)

    def test_malformed_register_is_refused(self):
        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w") as handle:
            handle.write("{not json")
        with self.assertRaises(SystemExit):
            ca.main(["--register", bad, "--base", self.tmp, "build",
                     "--outdir", self.tmp, "--quiet"])

    def test_two_builds_produce_identical_output(self):
        for _ in range(2):
            ca.main(["--register", REGISTER, "--observations", OBSERVATIONS,
                     "--base", REPO_BASE, "build",
                     "--outdir", os.path.join(self.tmp, "a"), "--quiet"])
        with open(os.path.join(self.tmp, "a", "capability_appendix.md")) as fh:
            first = fh.read()
        ca.main(["--register", REGISTER, "--observations", OBSERVATIONS,
                 "--base", REPO_BASE, "build",
                 "--outdir", os.path.join(self.tmp, "b"), "--quiet"])
        with open(os.path.join(self.tmp, "b", "capability_appendix.md")) as fh:
            second = fh.read()
        self.assertEqual(first, second)

    def test_csv_never_leaves_a_cell_blank(self):
        ca.main(["--register", REGISTER, "--observations", OBSERVATIONS,
                 "--base", REPO_BASE, "build",
                 "--outdir", os.path.join(self.tmp, "out"), "--quiet"])
        import csv as csv_mod
        path = os.path.join(self.tmp, "out", "capability_claims.csv")
        with open(path, encoding="utf-8", newline="") as handle:
            rows = list(csv_mod.DictReader(handle))
        self.assertEqual(len(rows), 6)
        for row in rows:
            for column, value in row.items():
                self.assertNotEqual(str(value).strip(), "",
                                    "blank %s for %s" % (column, row["claim_id"]))


class DriftEndToEnd(unittest.TestCase):
    """Record a real run, then change the artifact. The claim must demote
    itself with no human deciding to."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.lane = os.path.join(self.tmp, "lane")
        os.makedirs(self.lane)
        self.script = os.path.join(self.lane, "demo_tool.py")
        with open(self.script, "w") as handle:
            handle.write("print('records checked: 3')\n")
        self.register = {
            "page_budget": {"pages": 2, "words_per_page": 500},
            "claims": [{
                "claim_id": "D1", "capability_area": "comparison",
                "statement": "Records are checked and the count is printed.",
                "business_use": "The figure can be regenerated from its inputs.",
                "artifact_dir": "lane",
                "artifact_paths": ["lane/demo_tool.py"],
                "demonstration": {"cwd": "lane", "command": "python3 demo_tool.py"},
            }],
        }
        self.reg_path = os.path.join(self.tmp, "reg.json")
        with open(self.reg_path, "w") as handle:
            json.dump(self.register, handle)
        self.obs_path = os.path.join(self.tmp, "obs.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self):
        ca.main(["--register", self.reg_path, "--observations", self.obs_path,
                 "--base", self.tmp, "record", "--observed-on", "2026-09-19"])

    def test_claim_is_demonstrated_before_the_artifact_changes(self):
        self._record()
        demo, notdemo = ca.evaluate(self.register, load(self.obs_path), self.tmp)
        self.assertEqual(len(demo), 1)
        self.assertEqual(notdemo, [])
        self.assertIn("records checked: 3", demo[0]["bind_detail"]["output_verbatim"])

    def test_claim_demotes_itself_after_the_artifact_changes(self):
        self._record()
        with open(self.script, "a") as handle:
            handle.write("print('and something else')\n")
        demo, notdemo = ca.evaluate(self.register, load(self.obs_path), self.tmp)
        self.assertEqual(demo, [])
        self.assertEqual(len(notdemo), 1)
        self.assertIn("changed since it was demonstrated",
                      " ".join(notdemo[0]["blockers"]))

    def test_claim_demotes_when_the_artifact_is_deleted(self):
        self._record()
        os.unlink(self.script)
        demo, notdemo = ca.evaluate(self.register, load(self.obs_path), self.tmp)
        self.assertEqual(demo, [])
        self.assertIn("not found", " ".join(notdemo[0]["blockers"]))

    def test_a_failing_demonstration_is_recorded_as_failing(self):
        with open(self.script, "w") as handle:
            handle.write("import sys\nsys.exit(3)\n")
        self._record()
        obs = load(self.obs_path)["observations"][0]
        self.assertEqual(obs["exit_code"], 3)
        demo, notdemo = ca.evaluate(self.register, load(self.obs_path), self.tmp)
        self.assertEqual(demo, [])
        self.assertIn("exited 3", " ".join(notdemo[0]["blockers"]))


class Determinism(unittest.TestCase):

    def test_record_requires_an_explicit_date(self):
        # No wall clock anywhere, so 'record' cannot default the date.
        with self.assertRaises(SystemExit):
            ca.main(["record"])

    def test_source_reads_no_clock(self):
        with open(os.path.join(HERE, "capability_appendix.py"),
                  encoding="utf-8") as handle:
            source = handle.read()
        for banned in ("datetime.now", "date.today", "time.time", "random."):
            self.assertNotIn(banned, source,
                             "%s would make the output irreproducible" % banned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
