"""Whole-generation and operator regressions for the retained Framer snapshot.

No network, private evidence or buyer action. Each CLI uses the actual source in
this checkout; temporary copies exercise missing/mismatched sibling files only.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from opportunities.invest_appalachia_framer_lms import carrier, workshare

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "opportunities" / "invest_appalachia_framer_lms"
MEMBERS = ("carrier.py", "workshare.py", "current_packet.json", "partner_workshare.json", "requirements.json", "source_generation.json")
OLD_PACKET = "13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02"
OLD_WORKSHARE = "9825e29c23028dffb23158f7b1db8fb751ba45c0ecedad681764d77bc5ac3b4d"


def independent_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def predecessor(packet, offer):
    """Undo only documented generation edits; entire predecessor digests pin
    every remaining qualification/evidence/commercial field, not just counts."""
    p, w = deepcopy(packet), deepcopy(offer)
    del p["source_generation"], p["eligibility"], p["proposal"]["pricing_state"]
    p["opportunity"]["attachments_status"] = "PARTIAL"
    p["proposal"]["platform_recommendation"] = "UNSELECTED_PENDING_ATTACHMENT_A_AND_QUALIFIED_PRIME_INPUT"
    del w["source_generation"]
    w["qualification_generation_sha256"] = OLD_PACKET
    w["qualified_prime_must_own"][0] = "at least two qualifying LMS platform implementations"
    w["qualified_prime_must_own"].pop()
    return p, w


class SourceGenerationTests(unittest.TestCase):
    def setUp(self):
        self.p = carrier.load_json(LANE / "current_packet.json")
        self.w = workshare.load_json(LANE / "partner_workshare.json")
        self.r = carrier.load_json(LANE / "requirements.json")
        self.s = carrier.load_json(LANE / "source_generation.json")

    def pair(self, p=None, w=None, r=None, s=None):
        p = self.p if p is None else p
        w = self.w if w is None else w
        r = self.r if r is None else r
        s = self.s if s is None else s
        return carrier.evaluate(p, r, s), workshare.evaluate(p, w, r, s)

    def rejects_sources(self, r, s):
        with self.assertRaises(carrier.PursuitError):
            carrier.evaluate(self.p, r, s)
        with self.assertRaises(workshare.WorkshareError):
            workshare.evaluate(self.p, self.w, r, s)

    def cli(self, name, extra=(), cwd=None, lane=LANE, module=False):
        command = [sys.executable] + (["-O"] if sys.flags.optimize else [])
        command += ["-m", "opportunities.invest_appalachia_framer_lms." + name] if module else [str(lane / (name + ".py"))]
        if name == "workshare":
            command += ["--current-packet", str(lane / "current_packet.json"), "--workshare", str(lane / "partner_workshare.json")]
        return subprocess.run(command + list(extra), cwd=cwd or ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_history_all_nine_records_and_commercial_fields_are_preserved(self):
        p, w = predecessor(self.p, self.w)
        self.assertEqual(independent_digest(p), OLD_PACKET)
        self.assertEqual(independent_digest(w), OLD_WORKSHARE)
        self.assertEqual(len(self.p["qualification"]), 9)
        self.assertEqual(self.s["previous_packet_sha256"], OLD_PACKET)
        self.assertEqual(self.s["previous_workshare_sha256"], OLD_WORKSHARE)

    def test_canonical_source_bindings_agree_in_both_receipts(self):
        binding = self.p["source_generation"]
        self.assertEqual(binding, self.w["source_generation"])
        self.assertEqual(binding["requirements_sha256"], independent_digest(self.r))
        self.assertEqual(binding["source_manifest_sha256"], independent_digest(self.s))
        for receipt in self.pair():
            self.assertEqual(receipt["source_generation"], binding)
            body = deepcopy(receipt)
            receipt_hash = body.pop("receipt_sha256")
            self.assertEqual(receipt_hash, independent_digest(body))

    def test_recovered_templates_do_not_complete_responses_or_budget(self):
        for key in ("main_rfp", "attachment_a_functional_requirements", "attachment_b_selection_rubric", "attachment_c_budget_template", "attachment_d_optional_response_template"):
            self.assertEqual(self.r["attachment_status"][key], "RECOVERED_BUYER_SOURCE")
        self.assertEqual(self.r["bidder_response"]["budget_attachment_c"], "UNFILLED")
        self.assertEqual(self.r["bidder_response"]["completed_response_evidence_refs"], [])
        p, w = self.pair()
        self.assertEqual(p["attachments_status"], "RECOVERED_BUYER_DOCUMENTS")
        self.assertEqual(w["buyer_source_status"], "RECOVERED_BUYER_DOCUMENTS")
        self.assertEqual(p["bidder_response_status"], "INCOMPLETE")
        self.assertEqual(w["bidder_response_status"], "INCOMPLETE")
        self.assertFalse(p["proposal_budget_within_cap"])
        self.assertEqual(w["specialist_price_usd"], 24000)
        self.assertEqual(w["commercial_status"], "PROPOSED_NOT_ACCEPTED")

    def test_optional_templates_and_buyer_rubric_do_not_become_required_responses(self):
        response = self.r["bidder_response"]
        self.assertEqual(response["optional_template_d"], "NOT_FILLED_OPTIONAL")
        self.assertEqual(response["detailed_attachment_a_response"], "NOT_PREPARED_OPTIONAL")
        self.assertEqual(response["buyer_rubric_b"], "NOT_A_BIDDER_RESPONSE")
        self.assertIs(self.s["buyer_documents"]["attachment_d"]["optional"], True)

    def test_named_collective_route_preserves_attribution_and_missing_evidence(self):
        rule = self.r["qualification_evidence_rules"]["two_lms_platform_implementations"]
        self.assertEqual(rule["minimum_distinct_platforms"], 2)
        self.assertIn("NAMED_SPECIALIST", rule["evidence_route"])
        self.assertIn("subcontractor", rule["accepted_attributed_roles"])
        self.assertIn("evidence locator", rule["required_attribution"])
        self.assertFalse(rule["unnamed_potential_specialist_counts_as_experience"])
        self.assertFalse(rule["recovered_buyer_source_counts_as_team_evidence"])
        self.assertIn("collectively across named key personnel", self.w["qualified_prime_must_own"][0])
        self.assertEqual(self.p["qualification"]["two_lms_platform_implementations"]["state"], "MISSING")

    def test_us_prime_and_insurance_remain_unverified(self):
        for receipt in self.pair():
            self.assertEqual(receipt["us_prime_eligibility"], "UNVERIFIED")
        insurance = self.r["qualification_evidence_rules"]["insurance"]
        self.assertFalse(insurance["adequacy_verified"])
        self.assertFalse(insurance["underlying_documentation_waived"])
        p = deepcopy(self.p)
        p["eligibility"]["us_registered_prime"]["state"] = "VERIFIED"
        for module, args in ((carrier, (p,)), (workshare, (p, self.w))):
            with self.subTest(module=module.__name__), self.assertRaises(ValueError):
                module.evaluate(*args)

    def test_blank_budget_structure_stays_unpriced(self):
        b = self.r["budget_structure"]
        self.assertEqual(len(b["line_items"]), 6)
        self.assertEqual(len(b["recurring_fields"]), 4)
        self.assertIs(b["blank_or_zero_is_priced_evidence"], False)
        self.assertIs(b["filled_bidder_budget_supplied"], False)
        self.assertEqual(self.p["proposal"]["pricing_state"], "UNPRICED_ZERO_PLACEHOLDERS")

    def test_source_identity_is_attributed_to_historical_observations(self):
        self.assertEqual(self.s["historical_recovery"]["faq_status_at_that_observation"], "FAQ_NOT_VISIBLE_YET")
        self.assertEqual(self.s["reviewed_faq"]["status"], "RECOVERED_AND_REVIEWED_20260919")
        self.assertEqual(self.s["reviewed_faq"]["sha256"], "1e68dbc5e2c748dbe7ddd24f770554a836ea5d334dfcf15aa7352aed5e74b261")
        self.assertEqual(self.s["outreach_constraints"], {"Synegen": "DNR_RETAINED", "Raccoon Gang": "DNR_RETAINED"})
        self.assertIs(self.s["source_recovery_grants_authority"], False)
        self.assertFalse(self.pair()[0]["deadline_currentness_authoritative"])

    def test_old_and_new_packet_workshare_combinations_do_not_mix(self):
        old_p, old_w = predecessor(self.p, self.w)
        for p, w in ((old_p, self.w), (self.p, old_w), (old_p, old_w)):
            with self.subTest(packet=independent_digest(p)), self.assertRaises(workshare.WorkshareError):
                workshare.evaluate(p, w)
        with self.assertRaises(carrier.PursuitError):
            carrier.evaluate(old_p)

    def test_requirements_mutations_are_rejected_by_both_evaluators(self):
        for path, value in ((('budget_cap_usd',), 999999), (('attachment_status', 'faq_20260917'), 'UNAVAILABLE'), (('bidder_response', 'status'), 'COMPLETE'), (('source_manifest_sha256',), '0' * 64), (('source_generation_id',), 'older')):
            r = deepcopy(self.r)
            target = r
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            with self.subTest(path=path):
                self.rejects_sources(r, self.s)

    def test_source_mutations_and_self_rebound_caller_digests_are_rejected(self):
        s = deepcopy(self.s)
        s["reviewed_faq"]["sha256"] = 'f' * 64
        r = deepcopy(self.r)
        r["source_manifest_sha256"] = independent_digest(s)
        self.rejects_sources(r, s)
        p = deepcopy(self.p)
        p["source_generation"]["source_manifest_sha256"] = independent_digest(s)
        p["source_generation"]["requirements_sha256"] = independent_digest(r)
        w = deepcopy(self.w)
        w["source_generation"] = deepcopy(p["source_generation"])
        w["qualification_generation_sha256"] = independent_digest(p)
        with self.assertRaises(carrier.PursuitError):
            carrier.evaluate(p, r, s)
        with self.assertRaises(workshare.WorkshareError):
            workshare.evaluate(p, w, r, s)

    def test_buyer_url_cannot_be_used_to_promote_any_qualification(self):
        for name in self.p["qualification"]:
            p = deepcopy(self.p)
            p["qualification"][name]["state"] = "VERIFIED"
            p["qualification"][name]["evidence_refs"] = [self.s["reviewed_faq"]["url"]]
            with self.subTest(name=name):
                with self.assertRaises(carrier.PursuitError):
                    carrier.evaluate(p)
                with self.assertRaises(workshare.WorkshareError):
                    workshare.evaluate(p, self.w)

    def test_literal_false_authorities_cannot_be_replaced_with_truthy_or_zero(self):
        for packet, module in ((self.p, carrier), (self.w, workshare)):
            for key in packet["authority"]:
                for replacement in (True, 0, "false", None):
                    changed = deepcopy(packet)
                    changed["authority"][key] = replacement
                    with self.subTest(module=module.__name__, key=key, value=replacement), self.assertRaises(ValueError):
                        module.evaluate(changed) if module is carrier else module.evaluate(self.p, changed)
        for receipt, packet in zip(self.pair(), (self.p, self.w)):
            for key in packet["authority"]:
                self.assertIs(receipt[key], False)

    def test_evaluations_and_returned_objects_do_not_mutate_input_or_generation(self):
        before = tuple(deepcopy(v) for v in (self.p, self.w, self.r, self.s))
        baseline = self.pair()
        changed = carrier.normalize(self.p)
        changed["qualification"].clear()
        altered_ws = workshare.validate_workshare(self.w)
        altered_ws["authority"]["submission_authorized"] = True
        for receipt in self.pair():
            receipt["source_generation"].clear()
        self.assertEqual(self.pair(), baseline)
        self.assertEqual((self.p, self.w, self.r, self.s), before)

    def test_default_and_explicit_source_arguments_agree(self):
        self.assertEqual(self.pair(), (carrier.evaluate(self.p), workshare.evaluate(self.p, self.w)))

    def test_dictionary_order_does_not_change_receipts(self):
        reverse = lambda d: dict(reversed(list(d.items())))
        self.assertEqual(self.pair(reverse(self.p), reverse(self.w), reverse(self.r), reverse(self.s)), self.pair())

    def test_carrier_public_globals_rebinding_cannot_change_captured_semantics(self):
        baseline = self.pair()[0]
        original_error = carrier.PursuitError
        names = ("CURRENT_PACKET_SHA256", "SOURCE_MANIFEST_SHA256", "REQUIREMENTS_SHA256", "GATES", "AUTH", "CAP", "DEADLINE", "OPPORTUNITY_ID", "normalize", "digest", "canon", "validate_sources", "load_json", "PursuitError")
        replacement = {name: None for name in names}
        with patch.multiple(carrier, **replacement):
            self.assertEqual(carrier.evaluate(self.p, self.r, self.s), baseline)
            p = deepcopy(self.p)
            p["authority"]["submission_authorized"] = True
            with self.assertRaises(original_error):
                carrier.evaluate(p, self.r, self.s)

    def test_workshare_new_source_constants_are_captured_at_import(self):
        baseline = self.pair()[1]
        with patch.multiple(workshare, REQUIREMENTS_SHA256='0' * 64, SOURCE_MANIFEST_SHA256='0' * 64):
            self.assertEqual(workshare.evaluate(self.p, self.w, self.r, self.s), baseline)
            self.rejects_sources({}, self.s)

    def test_strict_json_loaders_reject_invalid_and_ambiguous_inputs(self):
        cases = (b'{"a":{"b":1,"b":2}}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":"\\ud800"}', b'{"x":"\xff"}', b'{', b'')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "input.json"
            for raw in cases:
                path.write_bytes(raw)
                for module in (carrier, workshare):
                    with self.subTest(raw=raw, module=module.__name__), self.assertRaises(ValueError):
                        module.load_json(path)
            path.unlink()
            for module in (carrier, workshare):
                with self.assertRaises(ValueError):
                    module.load_json(path)

    def test_non_object_source_values_are_rejected_not_treated_as_defaults(self):
        for value in ([], False, 0, "", {}):
            with self.subTest(value=value):
                self.rejects_sources(value, self.s)
                self.rejects_sources(self.r, value)

    def test_real_direct_and_module_clis_produce_exact_api_receipts(self):
        expected = dict(zip(("carrier", "workshare"), self.pair()))
        for name in expected:
            for module in (False, True):
                result = self.cli(name, module=module)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected[name])
                self.assertEqual(result.stderr, "")

    def test_direct_clis_are_independent_of_operator_working_directory(self):
        with tempfile.TemporaryDirectory() as td:
            for name, expected in zip(("carrier", "workshare"), self.pair()):
                result = self.cli(name, cwd=td)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_real_clis_refuse_mixed_sources_without_emitting_a_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            invalid = Path(td) / "mixed.json"
            invalid.write_text('{}', encoding='utf-8')
            for name in ("carrier", "workshare"):
                for option in ("--requirements", "--source-manifest", "--current-packet"):
                    result = self.cli(name, (option, str(invalid)))
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("Traceback", result.stderr)

    def test_missing_or_altered_sibling_sources_fail_in_real_copied_cli(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            for member in MEMBERS:
                shutil.copyfile(LANE / member, target / member)
            source = target / "source_generation.json"
            source.unlink()
            for name in ("carrier", "workshare"):
                result = self.cli(name, lane=target)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
            source.write_text('{}', encoding='utf-8')
            for name in ("carrier", "workshare"):
                result = self.cli(name, lane=target)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_real_clis_do_not_rewrite_the_source_generation(self):
        before = {name: (LANE / name).read_bytes() for name in MEMBERS}
        for name in ("carrier", "workshare"):
            self.assertEqual(self.cli(name).returncode, 0)
        self.assertEqual(before, {name: (LANE / name).read_bytes() for name in MEMBERS})


if __name__ == '__main__':
    unittest.main()
