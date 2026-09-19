"""Independent exact-source acceptance of Framer #16383, not a runtime engine.

Run with --lane (published candidate component) and --baseline (original component).
The historical SOURCE_MANIFEST is a deliberately wrong input to the new manifest
contract, not an assertion that the historical recovery was wrong when recorded.
All code and input buffers are captured, pinned and copied before execution.
"""
from __future__ import annotations
import argparse
import contextlib
import copy
import hashlib
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

CANDIDATE_BLOBS = {
    "carrier.py": "898b485120177231c0c50280d778571fa9b63e37",
    "workshare.py": "67ddd683a26facac11a48112919189a92c6b9ae2",
    "current_packet.json": "1dc2f6517ac21f61f97ffc0820731b7ec25db880",
    "requirements.json": "7356e2e41d61efd8c82759171b827d4337cfa027",
    "source_generation.json": "77444206a24dfc12585a5c8224c3edab698f9d89",
    "partner_workshare.json": "70715ca48a93ffd7b92eba2ec84db1e7a25e15d8",
    "recovered_20260916/SOURCE_MANIFEST.json": "b4037931103a52e51eddbf8b671fdab3254d39f2",
}
BASELINE_BLOBS = {
    "current_packet.json": "8e24ca9ea6adb91213180c49972a07585740ed4c",
    "requirements.json": "adfe3fab1f648771b4b92255932860e7629ee15d",
    "partner_workshare.json": "04b072fa272f0ed2c3902c9fbfbfb1931b902ae6",
}
QUALIFICATION_SHA = "c66135fa1e4e08acf14e6985aaaef339d703d7e9bd9922b5016b72090c8d7630"
PURSUIT_RECEIPT_SHA = "c1ed7e5eef24a49618046d13e9d77eecfb97d293943c86c69a35c673360e5060"
WORKSHARE_RECEIPT_SHA = "082898666e70c0e862151e081d718c55b461d6c19666b42ef9aa35a3e4f20582"


def git_blob(body: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, allow_nan=False,
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def capture(folder: Path, expected: dict[str, str]) -> dict[str, bytes]:
    captured = {}
    for name, expected_blob in expected.items():
        body = (folder / name).read_bytes()
        if git_blob(body) != expected_blob:
            raise RuntimeError(f"Unreviewed source bytes: {name}; expected {expected_blob}, got {git_blob(body)}")
        captured[name] = body
    return captured


def leaves(value, prefix=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, prefix + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, prefix + (index,))
    else:
        yield prefix, value


def changed(value, keys, replacement):
    out = copy.deepcopy(value)
    node = out
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = replacement
    return out


class BoundGenerationTests(unittest.TestCase):
    candidate: dict[str, bytes]
    baseline: dict[str, bytes]

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="framer-independent-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.lane = self.root / "candidate"
        self.old = self.root / "baseline"
        for folder, buffers in ((self.lane, self.candidate), (self.old, self.baseline)):
            for name, data in buffers.items():
                p = folder / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
        self.packet = json.loads(self.candidate["current_packet.json"])
        self.offer = json.loads(self.candidate["partner_workshare.json"])
        self.requirements = json.loads(self.candidate["requirements.json"])
        self.manifest = json.loads(self.candidate["source_generation.json"])
        self.historical = json.loads(self.candidate["recovered_20260916/SOURCE_MANIFEST.json"])
        self.carrier = self.module("carrier")
        self.workshare = self.module("workshare")

    def module(self, name):
        module = types.ModuleType("review_" + name)
        module.__file__ = str(self.lane / (name + ".py"))
        code = compile(self.candidate[name + ".py"], module.__file__, "exec")
        exec(code, module.__dict__)
        return module

    def evaluate(self, which, packet=None, offer=None, requirements=None, manifest=None):
        p = self.packet if packet is None else packet
        r = self.requirements if requirements is None else requirements
        m = self.manifest if manifest is None else manifest
        if which == "carrier":
            return self.carrier.evaluate(p, r, m)
        return self.workshare.evaluate(p, self.offer if offer is None else offer, r, m)

    def rejects(self, which, **kwargs):
        error = self.carrier.PursuitError if which == "carrier" else self.workshare.WorkshareError
        with self.assertRaises(error):
            self.evaluate(which, **kwargs)

    def cli(self, which, packet=None, offer=None, requirements=None, manifest=None, optimized=None):
        flag = bool(sys.flags.optimize) if optimized is None else optimized
        command = [sys.executable, *( ["-O"] if flag else [] ), str(self.lane / (which + ".py")),
                   "--current-packet", str(packet or self.lane / "current_packet.json"),
                   "--requirements", str(requirements or self.lane / "requirements.json"),
                   "--source-manifest", str(manifest or self.lane / "source_generation.json")]
        if which == "workshare":
            command.extend(["--workshare", str(offer or self.lane / "partner_workshare.json")])
        return subprocess.run(command, cwd=self.root, capture_output=True, timeout=20)

    def assert_cli_rejects(self, proc):
        self.assertEqual(proc.returncode, 2, proc.stderr.decode(errors="replace"))
        self.assertEqual(proc.stdout, b"")
        self.assertIn(b"error:", proc.stderr)
        self.assertNotIn(b"Traceback", proc.stderr)

    def test_preserved_qualification_is_anchored_to_old_evidence(self):
        self.assertEqual(self.packet["qualification"], json.loads(self.baseline["current_packet.json"])["qualification"])
        self.assertEqual(digest(self.packet["qualification"]), QUALIFICATION_SHA)

    def test_all_four_generation_bindings_agree_independently(self):
        expected = {"generation_id": self.manifest["generation_id"],
                    "requirements_sha256": digest(self.requirements),
                    "source_manifest_sha256": digest(self.manifest)}
        self.assertEqual(self.packet["source_generation"], expected)
        self.assertEqual(self.offer["source_generation"], expected)
        self.assertEqual(self.offer["qualification_generation_sha256"], digest(self.packet))
        self.assertEqual(self.requirements["source_manifest_sha256"], digest(self.manifest))

    def test_historical_identities_are_retained_not_rewritten(self):
        fields = [("main_rfp", self.historical["first_party_files"]["rfp_pdf"]),
                  ("attachments_zip", self.historical["first_party_files"]["zipped_rfp_docs"])]
        for key, old_key in (("attachment_a", "A_functional_requirements"),
                             ("attachment_b", "B_selection_rubric"),
                             ("attachment_c", "C_budget_template"),
                             ("attachment_d", "D_optional_response_template")):
            fields.append((key, self.historical["attachments"][old_key]))
        for key, retained in fields:
            with self.subTest(source=key):
                for field in ("bytes", "sha256"):
                    self.assertEqual(self.manifest["buyer_documents"][key][field], retained[field])
        self.assertEqual(self.historical["buyer_page"]["faq_classification"], "FAQ_NOT_VISIBLE_YET")
        self.assertEqual(self.manifest["historical_recovery"]["faq_status_at_that_observation"], "FAQ_NOT_VISIBLE_YET")
        self.assertEqual(self.manifest["historical_recovery"]["git_blob"], CANDIDATE_BLOBS["recovered_20260916/SOURCE_MANIFEST.json"])

    def test_faq_record_points_to_the_reviewed_source_not_new_download(self):
        faq = self.manifest["reviewed_faq"]
        self.assertEqual(faq["sha256"], "1e68dbc5e2c748dbe7ddd24f770554a836ea5d334dfcf15aa7352aed5e74b261")
        self.assertEqual(faq["bytes"], 287153)
        self.assertEqual(faq["source_review_git_blob"], "02daad58dc80bd818cb3d5f8726e8579f150af75")
        self.assertEqual(faq["qualification_review_git_blob"], "b08dabc8ed699030c16ae407eb8fb05faeb4461e")
        self.assertEqual(faq["observed_at_utc"], "2026-09-19T14:43:26Z")

    def test_named_experience_is_not_an_unnamed_role_or_buyer_document(self):
        rule = self.requirements["qualification_evidence_rules"]["two_lms_platform_implementations"]
        self.assertEqual(rule["minimum_distinct_platforms"], 2)
        self.assertIs(rule["unnamed_potential_specialist_counts_as_experience"], False)
        self.assertIs(rule["recovered_buyer_source_counts_as_team_evidence"], False)
        self.assertIn("named person", rule["required_attribution"])
        self.assertIn("reference basis", rule["required_attribution"])
        self.assertEqual(self.packet["eligibility"]["us_registered_prime"]["state"], "HOLD")
        self.assertEqual(self.packet["eligibility"]["us_registered_prime"]["evidence_refs"], [])

    def test_recovered_templates_are_not_completed_bidder_responses(self):
        self.assertEqual(self.manifest["buyer_documents"]["attachment_c"]["evidence_role"], "BLANK_BUYER_BUDGET_TEMPLATE")
        self.assertEqual(self.requirements["bidder_response"]["status"], "INCOMPLETE")
        self.assertEqual(self.requirements["bidder_response"]["completed_response_evidence_refs"], [])
        self.assertIs(self.packet["proposal"]["attachments_complete"], False)
        self.assertIs(self.requirements["budget_structure"]["filled_bidder_budget_supplied"], False)
        self.assertIs(self.requirements["budget_structure"]["blank_or_zero_is_priced_evidence"], False)

    def test_api_receipts_are_exact_deterministic_and_non_authorizing(self):
        for which, expected in (("carrier", PURSUIT_RECEIPT_SHA), ("workshare", WORKSHARE_RECEIPT_SHA)):
            with self.subTest(evaluator=which):
                receipt = self.evaluate(which)
                self.assertEqual(receipt["receipt_sha256"], expected)
                unsigned = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
                self.assertEqual(digest(unsigned), expected)
                self.assertEqual(self.evaluate(which), receipt)
                self.assertEqual(receipt["bidder_response_status"], "INCOMPLETE")
                self.assertEqual(receipt["us_prime_eligibility"], "UNVERIFIED")
                for key, value in receipt.items():
                    if key.endswith("_authorized") or key == "award_or_revenue_asserted":
                        self.assertIs(value, False)
        self.assertIs(self.evaluate("carrier")["proposal_budget_within_cap"], False)
        self.assertEqual(self.evaluate("workshare")["commercial_status"], "PROPOSED_NOT_ACCEPTED")

    def test_default_and_explicit_sources_have_same_meaning(self):
        self.assertEqual(self.carrier.evaluate(self.packet), self.evaluate("carrier"))
        self.assertEqual(self.workshare.evaluate(self.packet, self.offer), self.evaluate("workshare"))
        self.assertEqual(self.carrier.evaluate(self.packet, None, None), self.evaluate("carrier"))

    def test_all_eight_packet_requirements_manifest_api_mixes(self):
        old_p, old_r = (json.loads(self.baseline[name]) for name in ("current_packet.json", "requirements.json"))
        for bits in itertools.product((0, 1), repeat=3):
            p, r, m = [pair[bit] for pair, bit in zip(((old_p, self.packet), (old_r, self.requirements), (self.historical, self.manifest)), bits)]
            with self.subTest(current_bits=bits):
                if all(bits):
                    self.assertEqual(self.carrier.evaluate(p, r, m)["receipt_sha256"], PURSUIT_RECEIPT_SHA)
                else:
                    with self.assertRaises(self.carrier.PursuitError):
                        self.carrier.evaluate(p, r, m)

    def test_all_sixteen_workshare_api_mixes(self):
        old_p, old_r, old_w = (json.loads(self.baseline[name]) for name in ("current_packet.json", "requirements.json", "partner_workshare.json"))
        for bits in itertools.product((0, 1), repeat=4):
            p, r, m, w = [pair[bit] for pair, bit in zip(((old_p, self.packet), (old_r, self.requirements), (self.historical, self.manifest), (old_w, self.offer)), bits)]
            with self.subTest(current_bits=bits):
                if all(bits):
                    self.assertEqual(self.workshare.evaluate(p, w, r, m)["receipt_sha256"], WORKSHARE_RECEIPT_SHA)
                else:
                    with self.assertRaises(self.workshare.WorkshareError):
                        self.workshare.evaluate(p, w, r, m)

    def test_all_eight_carrier_cli_mixes(self):
        for bits in itertools.product((0, 1), repeat=3):
            p = (self.old, self.lane)[bits[0]] / "current_packet.json"
            r = (self.old, self.lane)[bits[1]] / "requirements.json"
            m = (self.lane / "recovered_20260916/SOURCE_MANIFEST.json", self.lane / "source_generation.json")[bits[2]]
            with self.subTest(current_bits=bits):
                proc = self.cli("carrier", packet=p, requirements=r, manifest=m)
                if all(bits):
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(json.loads(proc.stdout)["receipt_sha256"], PURSUIT_RECEIPT_SHA)
                else:
                    self.assert_cli_rejects(proc)

    def test_all_sixteen_workshare_cli_mixes(self):
        for bits in itertools.product((0, 1), repeat=4):
            p = (self.old, self.lane)[bits[0]] / "current_packet.json"
            r = (self.old, self.lane)[bits[1]] / "requirements.json"
            m = (self.lane / "recovered_20260916/SOURCE_MANIFEST.json", self.lane / "source_generation.json")[bits[2]]
            w = (self.old, self.lane)[bits[3]] / "partner_workshare.json"
            with self.subTest(current_bits=bits):
                proc = self.cli("workshare", packet=p, offer=w, requirements=r, manifest=m)
                if all(bits):
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    self.assertEqual(json.loads(proc.stdout)["receipt_sha256"], WORKSHARE_RECEIPT_SHA)
                else:
                    self.assert_cli_rejects(proc)

    def test_every_requirements_and_manifest_leaf_change_rejects(self):
        for argument, original in (("requirements", self.requirements), ("manifest", self.manifest)):
            for keys, value in leaves(original):
                replacement = (not value) if type(value) is bool else "unreviewed:" + repr(value)
                mutated = changed(original, keys, replacement)
                for which in ("carrier", "workshare"):
                    with self.subTest(input=argument, path=keys, evaluator=which):
                        self.rejects(which, **{argument: mutated})

    def test_qualification_us_eligibility_and_price_changes_reject(self):
        changes = [("qualification", gate, "state") for gate in self.packet["qualification"]]
        changes += [("eligibility", "us_registered_prime", "state"), ("proposal", "attachments_complete"),
                    ("proposal", "platform_recommendation"), ("proposal", "proposed_total_usd")]
        for keys in changes:
            for which in ("carrier", "workshare"):
                with self.subTest(field=keys, evaluator=which):
                    self.rejects(which, packet=changed(self.packet, keys, "VERIFIED"))

    def test_authority_flags_require_literal_false(self):
        for key in self.packet["authority"]:
            for value in (True, 0, None, "false"):
                for which in ("carrier", "workshare"):
                    with self.subTest(field=key, value=value, evaluator=which):
                        self.rejects(which, packet=changed(self.packet, ("authority", key), value))
        for key in self.offer["authority"]:
            for value in (True, 0, None, "false"):
                with self.subTest(workshare_flag=key, value=value):
                    self.rejects("workshare", offer=changed(self.offer, ("authority", key), value))

    def test_packet_and_receipt_mutation_do_not_change_future_results(self):
        before = copy.deepcopy((self.packet, self.offer, self.requirements, self.manifest))
        for which in ("carrier", "workshare"):
            receipt = self.evaluate(which)
            receipt["source_generation"]["generation_id"] = "mutated"
            self.assertEqual(self.evaluate(which)["source_generation"]["generation_id"], self.manifest["generation_id"])
        normalized = self.carrier.normalize(self.packet)
        normalized["qualification"]["w9_available"]["state"] = "VERIFIED"
        self.assertEqual((self.packet, self.offer, self.requirements, self.manifest), before)
        self.assertEqual(self.evaluate("carrier")["receipt_sha256"], PURSUIT_RECEIPT_SHA)

    def test_runtime_public_rebinding_cannot_replace_captured_semantics(self):
        for which, module in (("carrier", self.carrier), ("workshare", self.workshare)):
            evaluate = module.evaluate
            error = module.PursuitError if which == "carrier" else module.WorkshareError
            args = (self.packet, self.requirements, self.manifest) if which == "carrier" else (self.packet, self.offer, self.requirements, self.manifest)
            expected = evaluate(*args)
            for name in list(module.__dict__):
                if name.isupper():
                    setattr(module, name, "unreviewed")
            for name in ("digest", "canon", "canonical_json", "normalize", "validate_sources", "validate_qualification_generation", "validate_workshare", "load_json"):
                if hasattr(module, name):
                    setattr(module, name, lambda *a, **k: None)
            self.assertEqual(evaluate(*args), expected)
            bad = changed(self.packet, ("authority", "submission_authorized"), True)
            with self.assertRaises(error):
                evaluate(bad, *args[1:])

    def test_main_captures_evaluator_and_loader_at_import(self):
        for which, module, expected in (("carrier", self.carrier, PURSUIT_RECEIPT_SHA), ("workshare", self.workshare, WORKSHARE_RECEIPT_SHA)):
            module.evaluate = lambda *a, **k: {"incorrect": "replacement"}
            module.load_json = lambda *a, **k: {"incorrect": "replacement"}
            args = ["--current-packet", str(self.lane / "current_packet.json")]
            if which == "workshare":
                args += ["--workshare", str(self.lane / "partner_workshare.json")]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(module.main(args), 0)
            self.assertEqual(json.loads(output.getvalue())["receipt_sha256"], expected)

    def test_default_files_are_revalidated_after_import(self):
        for filename in ("requirements.json", "source_generation.json"):
            p = self.lane / filename
            p.write_text("{}", encoding="utf-8")
            with self.assertRaises(self.carrier.PursuitError):
                self.carrier.evaluate(self.packet)
            with self.assertRaises(self.workshare.WorkshareError):
                self.workshare.evaluate(self.packet, self.offer)
            p.write_bytes(self.candidate[filename])
        self.assertEqual(self.carrier.evaluate(self.packet)["receipt_sha256"], PURSUIT_RECEIPT_SHA)

    def test_bad_direct_cli_inputs_produce_no_receipt_or_traceback(self):
        for filename in ("current_packet.json", "requirements.json", "source_generation.json", "partner_workshare.json"):
            for body in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":"\\ud800"}', b'\xff', b'null', b'{'):
                p = self.lane / filename
                p.write_bytes(body)
                for which in (("workshare",) if filename == "partner_workshare.json" else ("carrier", "workshare")):
                    with self.subTest(file=filename, body=body, evaluator=which):
                        self.assert_cli_rejects(self.cli(which))
                p.write_bytes(self.candidate[filename])

    def test_missing_source_files_and_typed_wrong_inputs_reject(self):
        for filename in ("requirements.json", "source_generation.json"):
            p = self.lane / filename
            p.unlink()
            for which in ("carrier", "workshare"):
                with self.subTest(missing=filename, evaluator=which):
                    self.assert_cli_rejects(self.cli(which))
            p.write_bytes(self.candidate[filename])
        for value in ([], {}, False, 0, "", "null"):
            for which in ("carrier", "workshare"):
                with self.subTest(value=value, evaluator=which):
                    self.rejects(which, requirements=value)
                    self.rejects(which, manifest=value)

    def test_canonical_reformat_is_not_semantic_generation_movement(self):
        for filename in ("current_packet.json", "requirements.json", "source_generation.json", "partner_workshare.json"):
            value = json.loads(self.candidate[filename])
            (self.lane / filename).write_text(json.dumps(value, sort_keys=True, indent=4, ensure_ascii=True), encoding="utf-8")
        for which, expected in (("carrier", PURSUIT_RECEIPT_SHA), ("workshare", WORKSHARE_RECEIPT_SHA)):
            proc = self.cli(which)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["receipt_sha256"], expected)

    def test_manifest_recovery_is_not_outbound_permission(self):
        self.assertIs(self.manifest["source_recovery_grants_authority"], False)
        self.assertEqual(self.manifest["outreach_constraints"], {"Synegen": "DNR_RETAINED", "Raccoon Gang": "DNR_RETAINED"})
        self.assertIs(self.requirements["submission"]["external_send_authorized_by_repository_artifact"], False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    candidate = capture(args.lane, CANDIDATE_BLOBS)
    baseline = capture(args.baseline, BASELINE_BLOBS)
    BoundGenerationTests.candidate, BoundGenerationTests.baseline = candidate, baseline
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BoundGenerationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if capture(args.lane, CANDIDATE_BLOBS) != candidate or capture(args.baseline, BASELINE_BLOBS) != baseline:
        raise RuntimeError("Original input/source changed during acceptance")
    return 0 if result.wasSuccessful() and result.testsRun > 0 and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
