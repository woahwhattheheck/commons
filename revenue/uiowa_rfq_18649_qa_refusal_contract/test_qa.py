"""Tests for the Q&A refusal contract. Python 3 stdlib unittest, no network.

    python3 -m unittest -v test_qa.py

The tests that matter most here assert the ABSENCE of an answer. It is easy to
test that a lookup tool returns the right answer to a question it knows. The
property that makes it trustworthy in a room is the opposite one: that a
question it does not know produces a refusal naming what would be needed,
rather than a plausible paragraph. Several tests below exist only to fail if
this kit ever starts answering.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cli  # noqa: E402
import qa  # noqa: E402
import uncertainty as unc  # noqa: E402

PACKET = os.path.join(HERE, "fixtures", "packet.json")
DEFECTIVE = os.path.join(HERE, "fixtures", "packet_defective.json")


class PacketIntegrityTests(unittest.TestCase):
    """The worked example must be internally consistent and clean."""

    @classmethod
    def setUpClass(cls):
        cls.kit = qa.load_kit(PACKET)

    def test_packet_audit_is_clean(self):
        findings = self.kit.audit()
        self.assertEqual(findings, [], "worked packet must audit clean: %s"
                         % json.dumps(findings, indent=2)[:900])

    def test_packet_is_labelled_synthetic(self):
        self.assertTrue(self.kit.packet.synthetic)
        self.assertIn("SYNTHETIC", self.kit.packet.label.upper())

    def test_every_cited_evidence_id_resolves(self):
        for rec in self.kit.packet.answers:
            for claim in rec["claims"]:
                for eid in (claim.get("evidence_ids", [])
                            + claim.get("searched_evidence_ids", [])):
                    self.assertIn(eid, self.kit.packet.evidence,
                                  "%s cites missing %s" % (rec["id"], eid))

    def test_packet_demonstrates_a_strength_and_a_real_gap(self):
        types = set()
        for rec in self.kit.packet.answers:
            for claim in rec["claims"]:
                types.add(claim["claim_type"])
        # A packet that cannot show all four states cannot exercise the
        # distinction the kit exists to enforce.
        self.assertEqual(types, set(unc.CLAIM_TYPES))

    def test_every_record_routes_to_itself(self):
        for rec in (self.kit.packet.answers + self.kit.packet.boundaries
                    + self.kit.packet.gaps):
            answer = self.kit.ask(rec["question_variants"][0])
            self.assertEqual(answer.record_id, rec["id"],
                             "%r routed to %s" % (rec["question_variants"][0],
                                                  answer.record_id))

    def test_scope_accounts_for_every_cell(self):
        scope = self.kit.packet.assessment_scope
        total = len(scope["groups"]) * len(scope["areas"])
        self.assertEqual(
            len(scope["areas_examined"]) + len(scope["deliberately_not_examined"]),
            total, "the coverage register must account for all cells; an "
                   "unaccounted cell is how a gap becomes invisible")


class NotSupportedTests(unittest.TestCase):
    """The core property: an unanswerable question is not answered."""

    @classmethod
    def setUpClass(cls):
        cls.kit = qa.load_kit(PACKET)

    def test_question_outside_the_evidence_is_refused(self):
        answer = self.kit.ask(
            "What is the uptime SLA for the student information system?")
        self.assertEqual(answer.resolution, qa.NOT_SUPPORTED)
        self.assertEqual(answer.claims, [],
                         "a refusal must carry no claims at all")

    def test_refusal_names_what_would_be_needed(self):
        answer = self.kit.ask("What does the AI tooling cost us?")
        self.assertEqual(answer.resolution, qa.NOT_SUPPORTED)
        req = answer.evidence_request["requested_evidence"]
        self.assertTrue(req, "a refusal without a request is a shrug")
        for item in req:
            for field in ("artifact", "held_by", "would_settle"):
                self.assertTrue(item.get(field),
                                "requested evidence needs %s" % field)

    def test_even_the_fallthrough_names_a_next_step(self):
        answer = self.kit.ask("zzzz qqqq vvvv unrelated nonsense tokens")
        self.assertEqual(answer.resolution, qa.NOT_SUPPORTED)
        self.assertTrue(
            answer.evidence_request["requested_evidence"],
            "the generic refusal must still tell the reader what to do next")

    def test_nearby_evidence_does_not_become_an_answer(self):
        # "mean time to recovery" shares 'recovery' and 'RIS' with the
        # restoration answer and nothing else. The evidence contains no MTTR
        # figure, so the honest output is a refusal -- this test fails the
        # moment the coverage gate is loosened enough to serve one.
        answer = self.kit.ask("what is the mean time to recovery for RIS")
        self.assertEqual(answer.resolution, qa.NOT_SUPPORTED)

    def test_empty_question_is_refused_not_crashed(self):
        for junk in ("", "   ", "the and of", "???"):
            answer = self.kit.ask(junk)
            self.assertEqual(answer.resolution, qa.NOT_SUPPORTED)

    def test_partially_covered_question_declares_what_it_misses(self):
        answer = self.kit.ask("how many ESS changes were rejected at review")
        self.assertEqual(answer.resolution, qa.ANSWERED)
        self.assertIn("rejected", answer.uncovered_terms,
                      "being routed is not being answered; the parts the "
                      "evidence does not speak to must be named")


class HostileQuestionTests(unittest.TestCase):
    """Neither deflected nor answered. Both are failures."""

    @classmethod
    def setUpClass(cls):
        cls.kit = qa.load_kit(PACKET)

    def _boundary(self, question):
        answer = self.kit.ask(question)
        self.assertEqual(answer.resolution, qa.OUT_OF_SCOPE,
                         "%r should hit a scope boundary" % question)
        self.assertTrue(answer.boundary["cannot"].strip())
        self.assertTrue(answer.boundary["requires"].strip())
        # Not a deflection: it must still say something supported.
        self.assertTrue(answer.claims,
                        "a boundary with no supported claims is a dodge")
        self.assertTrue(answer.evidence_ids,
                        "the 'what we can say' part must cite real evidence")
        return answer

    def test_peer_percentile_question(self):
        for phrasing in ("Where do we rank against peer institutions?",
                         "What percentile are we in compared to other "
                         "universities?",
                         "how do we stack up against other universities"):
            answer = self._boundary(phrasing)
            self.assertEqual(answer.record_id, "B-001")

    def test_which_team_is_worst_question(self):
        for phrasing in ("Which team is the worst?",
                         "who is the weakest group",
                         "Rank the groups from strongest to weakest."):
            answer = self._boundary(phrasing)
            self.assertEqual(answer.record_id, "B-002")

    def test_compliance_verdict_question(self):
        for phrasing in ("Does this make us compliant?",
                         "will an auditor sign off on this",
                         "Are we compliant with the NIST framework?"):
            answer = self._boundary(phrasing)
            self.assertEqual(answer.record_id, "B-003")

    def test_boundary_answers_carry_no_verdict_or_ranking_claim(self):
        for phrasing in ("Which team is the worst?",
                         "Does this make us compliant?",
                         "Where do we rank against peer institutions?"):
            answer = self.kit.ask(phrasing)
            for claim in answer.claims:
                violations = unc.check_claim_language(
                    claim["claim_type"], claim["text"],
                    search_scope=claim.get("search_scope"))
                codes = [v.code for v in violations]
                self.assertNotIn("VERDICT_OR_RANKING_LANGUAGE", codes)

    def test_a_legitimate_question_is_not_lectured(self):
        # The regression for a real defect: "strongest" is rare and appears in
        # the ranking boundary's variants, so boundary-first resolution turned
        # an answerable question into a refusal.
        answer = self.kit.ask("what is our strongest practice")
        self.assertEqual(answer.resolution, qa.ANSWERED)
        self.assertEqual(answer.record_id, "A-001")


class UncertaintyLanguageTests(unittest.TestCase):
    """'We found no evidence of X' is not 'X does not happen'."""

    def test_absence_stated_as_fact_is_rejected(self):
        for bad in ("There is no restoration testing at RIS.",
                    "RIS does not test restores.",
                    "The team lacks any restoration procedure.",
                    "They never test recovery."):
            codes = [v.code for v in unc.check_claim_language(
                unc.ABSENT_IN_SEARCHED, bad, search_scope="runbooks")]
            self.assertTrue(
                "ABSENCE_STATED_AS_FACT" in codes
                or "ABSENCE_NOT_QUALIFIED" in codes,
                "%r asserts a fact about the University and must be "
                "rejected; got %s" % (bad, codes))

    def test_properly_qualified_absence_is_accepted(self):
        good = ("We found no record of a completed restoration exercise in "
                "the 14 runbooks and 9 change records supplied.")
        self.assertEqual(
            unc.check_claim_language(unc.ABSENT_IN_SEARCHED, good,
                                     search_scope="RIS runbooks, 14 files"),
            [])

    def test_absence_without_a_named_scope_is_rejected(self):
        codes = [v.code for v in unc.check_claim_language(
            unc.ABSENT_IN_SEARCHED,
            "We found no evidence of restoration testing in the material "
            "reviewed.", search_scope="")]
        self.assertIn("ABSENCE_WITHOUT_SCOPE", codes)

    def test_not_assessed_may_not_claim_a_search_happened(self):
        codes = [v.code for v in unc.check_claim_language(
            unc.NOT_ASSESSED,
            "We found no evidence of AI readiness at IAM.")]
        self.assertIn("NOT_ASSESSED_IMPLIES_SEARCH", codes)

    def test_not_assessed_must_declare_itself(self):
        codes = [v.code for v in unc.check_claim_language(
            unc.NOT_ASSESSED, "IAM AI readiness is an open question.")]
        self.assertIn("NOT_ASSESSED_NOT_DECLARED", codes)

    def test_the_three_absence_states_are_not_interchangeable(self):
        # The same sentence is valid as one claim type and invalid as the
        # other. That is the whole distinction, asserted directly.
        sentence = ("We found no record of a restoration exercise in the 14 "
                    "runbooks supplied.")
        self.assertEqual(
            unc.check_claim_language(unc.ABSENT_IN_SEARCHED, sentence,
                                     search_scope="14 runbooks"), [])
        self.assertNotEqual(
            unc.check_claim_language(unc.NOT_ASSESSED, sentence), [])

    def test_overclaimed_coverage_is_rejected_on_partial_evidence(self):
        codes = [v.code for v in unc.check_claim_language(
            unc.OBSERVED_PRESENT,
            "All teams always follow the review policy.",
            evidence_coverage="partial")]
        self.assertIn("OVERCLAIMED_COVERAGE", codes)

    def test_same_wording_is_allowed_when_coverage_is_complete(self):
        self.assertEqual(
            [v.code for v in unc.check_claim_language(
                unc.OBSERVED_PRESENT,
                "All teams follow the review policy.",
                evidence_coverage="complete")],
            [])

    def test_contested_must_show_the_disagreement(self):
        codes = [v.code for v in unc.check_claim_language(
            unc.CONTESTED, "Secrets are rotated quarterly.")]
        self.assertIn("CONTESTED_READS_AS_SETTLED", codes)

    def test_verdict_language_is_rejected_in_any_claim(self):
        for bad in ("ESS is compliant with the framework.",
                    "This would place us in the top percentile.",
                    "RIS is the worst of the three."):
            codes = [v.code for v in unc.check_claim_language(
                unc.OBSERVED_PRESENT, bad)]
            self.assertIn("VERDICT_OR_RANKING_LANGUAGE", codes)

    def test_boundary_must_name_a_requirement_and_say_something(self):
        codes = [v.code for v in unc.check_boundary_language(
            "That is outside the scope of this engagement.", "", 0)]
        self.assertIn("BOUNDARY_WITHOUT_REQUIREMENT", codes)
        self.assertIn("BOUNDARY_WITHOUT_SUBSTANCE", codes)


class DefectivePacketTests(unittest.TestCase):
    """Every guard is proven by a record that violates it."""

    @classmethod
    def setUpClass(cls):
        cls.kit = qa.load_kit(DEFECTIVE)
        cls.findings = cls.kit.audit()
        cls.by_record = {}
        for f in cls.findings:
            cls.by_record.setdefault(f.get("record_id"), []).append(f)

    def _codes(self, record_id):
        out = []
        for f in self.by_record.get(record_id, []):
            out.append(f.get("code") or f.get("detail", ""))
        return out

    def test_audit_catches_every_planted_defect(self):
        planted = ["D-001", "D-002", "D-003", "D-004", "D-005", "D-006",
                   "D-007", "D-008", "D-009", "D-B01", "D-B02", "D-G01"]
        missed = [r for r in planted if r not in self.by_record]
        self.assertEqual(missed, [],
                         "audit missed planted defects: %s" % missed)

    def test_absence_stated_as_fact(self):
        self.assertTrue(any("ABSENCE_STATED_AS_FACT" in c
                            for c in self._codes("D-001")))

    def test_absence_with_no_searched_evidence(self):
        self.assertTrue(any("searched_evidence_ids" in c
                            for c in self._codes("D-002")))

    def test_absence_in_an_area_that_was_never_examined(self):
        # The subtle one. The claim is well-formed and well-worded; it is
        # still wrong, because you cannot report finding nothing in a place
        # you never entered.
        self.assertTrue(any("areas_examined" in c
                            for c in self._codes("D-003")),
                        "an absence claim outside the assessed scope must be "
                        "caught as NOT_ASSESSED")

    def test_not_assessed_worded_as_a_search(self):
        self.assertTrue(any("NOT_ASSESSED_IMPLIES_SEARCH" in c
                            for c in self._codes("D-004")))

    def test_positive_claim_with_no_citation(self):
        self.assertTrue(any("OBSERVED_PRESENT with no evidence" in c
                            for c in self._codes("D-005")))

    def test_dangling_evidence_citation(self):
        self.assertTrue(any("unknown evidence id E-999" in c
                            for c in self._codes("D-006")))

    def test_contested_whose_evidence_agrees(self):
        self.assertTrue(any("does not actually" in c
                            for c in self._codes("D-007")))

    def test_overclaimed_coverage(self):
        self.assertTrue(any("OVERCLAIMED_COVERAGE" in c
                            for c in self._codes("D-008")))

    def test_verdict_language(self):
        self.assertTrue(any("VERDICT_OR_RANKING_LANGUAGE" in c
                            for c in self._codes("D-009")))

    def test_deflecting_boundary(self):
        codes = self._codes("D-B01")
        self.assertTrue(any("BOUNDARY_WITHOUT_REQUIREMENT" in c for c in codes))
        self.assertTrue(any("BOUNDARY_WITHOUT_SUBSTANCE" in c for c in codes))

    def test_trigger_term_too_common_is_flagged(self):
        self.assertTrue(any("idf" in c for c in self._codes("D-B02")),
                        "a common trigger term would make ordinary questions "
                        "hit a boundary and must be caught")

    def test_gap_with_no_evidence_request(self):
        self.assertTrue(any("would fill it" in c
                            for c in self._codes("D-G01")))

    def test_a_failing_record_is_withheld_not_served(self):
        answer = self.kit.ask(
            "How strong is the ESS software delivery capability?")
        self.assertEqual(answer.resolution, qa.KIT_DEFECT)
        self.assertEqual(answer.claims, [],
                         "a record that fails verification must not have its "
                         "claims served anyway")
        self.assertTrue(answer.defects)

    def test_defect_is_reported_to_the_reader_not_swallowed(self):
        answer = self.kit.ask(
            "How strong is the ESS software delivery capability?")
        rendered = cli.render(answer, self.kit.packet)
        self.assertIn("WITHHELD", rendered)


class MalformedInputTests(unittest.TestCase):
    """Broken packets fail loudly at load, not quietly at answer time."""

    def _packet(self, mutate):
        with open(PACKET, encoding="utf-8") as handle:
            data = json.load(handle)
        mutate(data)
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                          encoding="utf-8")
        json.dump(data, tmp)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_duplicate_evidence_id_is_rejected(self):
        path = self._packet(
            lambda d: d["evidence"].append(dict(d["evidence"][0])))
        with self.assertRaises(qa.PacketError):
            qa.load_kit(path)

    def test_duplicate_record_id_is_rejected(self):
        path = self._packet(
            lambda d: d["answers"].append(dict(d["answers"][0])))
        with self.assertRaises(qa.PacketError):
            qa.load_kit(path)

    def test_record_with_no_question_variants_is_rejected(self):
        def mutate(d):
            d["answers"][0]["question_variants"] = []
        with self.assertRaises(qa.PacketError):
            qa.load_kit(self._packet(mutate))

    def test_removing_evidence_breaks_the_answer_that_cited_it(self):
        # Verification runs per lookup, not once at authoring time, so a
        # packet that loses an evidence item stops serving the answer that
        # rested on it instead of serving it unsupported.
        def mutate(d):
            d["evidence"] = [e for e in d["evidence"] if e["id"] != "E-004"]
        kit = qa.load_kit(self._packet(mutate))
        answer = kit.ask("Has RIS tested restoring from backup?")
        self.assertEqual(answer.resolution, qa.KIT_DEFECT)

    def test_malformed_json_raises(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                          encoding="utf-8")
        tmp.write("{ not json at all ")
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        with self.assertRaises(ValueError):
            qa.load_kit(tmp.name)


class DeterminismAndRenderingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kit = qa.load_kit(PACKET)

    def test_same_question_gives_a_byte_identical_answer(self):
        question = "Has RIS tested restoring from backup?"
        first = json.dumps(self.kit.ask(question).as_dict(), sort_keys=True)
        for _ in range(4):
            self.assertEqual(
                json.dumps(qa.load_kit(PACKET).ask(question).as_dict(),
                           sort_keys=True), first)

    def test_rendered_output_is_ascii_and_fits_78_columns(self):
        questions = [r["question_variants"][0] for r in
                     (self.kit.packet.answers + self.kit.packet.boundaries
                      + self.kit.packet.gaps)]
        questions.append("What is the uptime SLA for the student system?")
        for question in questions:
            rendered = cli.render(self.kit.ask(question), self.kit.packet)
            rendered.encode("ascii")  # raises if any non-ASCII slipped in
            for line in rendered.splitlines():
                self.assertLessEqual(len(line), 78, repr(line))

    def test_state_is_carried_in_marks_not_colour(self):
        rendered = cli.render(
            self.kit.ask("Has RIS tested restoring from backup?"),
            self.kit.packet)
        self.assertIn("[found]", rendered)
        self.assertIn("[none in what we searched]", rendered)
        self.assertNotIn("\033[", rendered, "no ANSI colour codes")

    def test_every_answer_exposes_its_routing_arithmetic(self):
        answer = self.kit.ask("how are API keys rotated")
        self.assertTrue(answer.trace)
        for row in answer.trace:
            self.assertIn("id", row)


class CommandLineTests(unittest.TestCase):
    """The commands in the README are the commands that run."""

    def _run(self, *args):
        return subprocess.run([sys.executable, os.path.join(HERE, "cli.py")]
                              + list(args), capture_output=True, text=True,
                              cwd=HERE)

    def test_audit_passes_on_the_worked_packet(self):
        proc = self._run("audit")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("RESULT: PASS", proc.stdout)

    def test_audit_fails_on_the_defective_packet(self):
        proc = self._run("audit", "--packet", DEFECTIVE)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("RESULT: FAIL", proc.stdout)

    def test_drill_routes_every_record(self):
        proc = self._run("drill")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertNotIn("MISROUTED", proc.stdout)

    def test_ask_json_is_machine_readable(self):
        proc = self._run("ask", "Which team is the worst?", "--json")
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["resolution"], qa.OUT_OF_SCOPE)
        self.assertTrue(payload["evidence_ids"])

    def test_ask_an_unanswerable_question_from_the_command_line(self):
        proc = self._run("ask", "What is the uptime SLA for the SIS?")
        self.assertIn("NOT SUPPORTED", proc.stdout)
        self.assertIn("WHAT WE WOULD NEED TO ANSWER IT", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
