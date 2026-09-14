from .test_support import *  # noqa: F401,F403

class StrictInputTests(unittest.TestCase):
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(strict.ValidationError):
            strict.strict_json_loads('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(strict.ValidationError):
            strict.strict_json_loads('{"a":NaN}')

    def test_bool_is_not_integer(self):
        with self.assertRaises(strict.ValidationError):
            strict.require_int(True, field="n")

    def test_candidate_extra_key_rejected(self):
        value = candidate()
        value["send"] = True
        with self.assertRaises(strict.ValidationError):
            gate.normalize_candidate(value)

    def test_candidate_order_is_canonical(self):
        value = candidate()
        value["declared_capabilities"] = list(reversed(value["declared_capabilities"]))
        first = gate.normalize_candidate(value)
        second = gate.normalize_candidate(candidate())
        self.assertEqual(first, second)

    def test_source_requires_exact_document_set(self):
        value = source()
        value["documents"].pop()
        with self.assertRaises(strict.ValidationError):
            gate.normalize_source_ledger(value)

    def test_source_rejects_retained_without_digest(self):
        value = source()
        value["documents"][0]["sha256"] = None
        with self.assertRaises(strict.ValidationError):
            gate.normalize_source_ledger(value)

    def test_source_generation_is_order_invariant(self):
        value = source()
        reversed_value = copy.deepcopy(value)
        reversed_value["documents"].reverse()
        self.assertEqual(
            gate.normalize_source_ledger(value)["source_generation_sha256"],
            gate.normalize_source_ledger(reversed_value)["source_generation_sha256"],
        )

    def test_verified_evidence_requires_ref_and_digest(self):
        value = authority(source())
        value["direct_clearance"]["active_top_secret_fcl"]["evidence_ref"] = None
        with self.assertRaises(strict.ValidationError):
            gate.normalize_authority(value)

    def test_nonverified_evidence_cannot_carry_authority(self):
        value = authority(source(), direct=False)
        value["direct_clearance"]["active_top_secret_fcl"]["evidence_ref"] = "forged"
        with self.assertRaises(strict.ValidationError):
            gate.normalize_authority(value)

    def test_external_authority_true_rejected(self):
        value = authority(source())
        value["owner_decisions"]["external_submission_approved"] = True
        with self.assertRaises(strict.ValidationError):
            gate.normalize_authority(value)

