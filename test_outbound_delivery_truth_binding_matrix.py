"""Independent synthetic consumer audit for retained outbound evidence.

ZZ-HELIOTROPE-H7Q3 / GPT-6 Astra Pro, 2026-09-19.
No real mail, contacts, provider actions or external dependencies.
Run from the Commons root: python -m unittest -v test_outbound_delivery_truth_binding_matrix
The same suite must pass under python -O and python -OO.
"""
from copy import deepcopy
from itertools import permutations, product
import hashlib
import json
import unittest

from coordination import outbound_delivery_truth as engine

AUTHORITY_KEYS = {
    "send_authorized", "retry_authorized", "alternate_route_authorized",
    "provider_action_authorized", "buyer_acceptance", "payment_authorized",
    "cash_proven", "revenue_recognized",
}


def source():
    return {
        "operation_key": "SYNTHETIC-H7Q3-BINDING-AUDIT",
        "counterparty": "Fictional audit party",
        "purpose": "Offline regression only",
        "provider": "synthetic-provider", "provider_message_id": "audit-message",
        "provider_thread_id": "audit-thread", "sender": "audit-sender-token",
        "recipient": "audit-recipient-token", "submitted_at": "2026-09-19T10:00:00Z",
        "source_ref": "synthetic:h7q3:source", "source_sha256": "a" * 64,
    }


def evidence(kind):
    category, action, status, digest = {
        "failed": ("DSN", "failed", "5.1.1", "b"),
        "delivered": ("PROVIDER_DELIVERY_CONFIRMATION", "delivered", "2.0.0", "c"),
        "delayed": ("DSN", "delayed", "4.1.1", "d"),
    }[kind]
    return {
        "id": "audit-" + kind, "kind": category, "observed_at": "2026-09-19T10:01:00Z",
        "provider": "synthetic-provider", "original_message_id": "audit-message",
        "original_thread_id": "audit-thread", "sender": "audit-sender-token",
        "recipient": "audit-recipient-token", "action": action, "status": status,
        "diagnostic_code": "Fictional audit " + kind,
        "source_ref": "synthetic:h7q3:" + kind, "source_sha256": digest * 64,
    }


def packet(origin, events=()):
    return {
        "schema": engine.INPUT_SCHEMA,
        "submission": source() if origin == "provider" else None,
        "legacy_local_sent": source() if origin == "legacy" else None,
        "events": deepcopy(list(events)),
    }


def rehash(artifact):
    """Independent JSON receipt writer, not the compiler's private digest helper."""
    unsigned = {key: value for key, value in artifact.items() if key != "receipt_sha256"}
    raw = json.dumps(unsigned, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    artifact["receipt_sha256"] = hashlib.sha256(raw).hexdigest()


class DeliveryBindingMatrixTests(unittest.TestCase):
    def check_projection(self, supplied, expected):
        before = deepcopy(supplied)
        artifact = engine.compile_delivery_truth(supplied)
        self.assertEqual(supplied, before, "compiler changed retained input")
        self.assertEqual(artifact["delivery_state"], expected)
        projection = engine.collision_projection(artifact)
        self.assertEqual(projection["delivery_state"], expected)
        self.assertIs(projection["provider_submission_observed"], supplied["submission"] is not None)
        self.assertIs(projection["same_route_dedupe_hold"],
                      supplied["submission"] is not None or supplied["legacy_local_sent"] is not None)
        self.assertIs(projection["counts_as_contacted"], expected == "DELIVERED_EVIDENCE")
        self.assertEqual(set(artifact["authority"]), AUTHORITY_KEYS)
        for value in artifact["authority"].values():
            self.assertIs(value, False)
        for key in ("same_route_resend_authorized", "alternate_route_send_authorized", "counts_as_revenue"):
            self.assertIs(projection[key], False)
        self.assertIs(engine.verify_delivery_truth(supplied, artifact)["valid"], True)
        return artifact

    def test_every_evidence_subset_and_permutation(self):
        # Eight subsets per origin; 32 total permutation cases, including empty.
        expected = {
            (): {"provider": "PROVIDER_SUBMITTED_PENDING_DELIVERY", "legacy": "DELIVERY_UNKNOWN"},
            ("failed",): "DELIVERY_FAILED", ("delivered",): "DELIVERED_EVIDENCE",
            ("delayed",): "DELIVERY_UNKNOWN", ("failed", "delivered"): "DELIVERY_UNKNOWN",
            ("failed", "delayed"): "DELIVERY_FAILED", ("delivered", "delayed"): "DELIVERED_EVIDENCE",
            ("failed", "delivered", "delayed"): "DELIVERY_UNKNOWN",
        }
        cases = 0
        for origin in ("provider", "legacy"):
            for kinds, state in expected.items():
                wanted = state[origin] if isinstance(state, dict) else state
                reference = self.check_projection(packet(origin, map(evidence, kinds)), wanted)
                for order in permutations(kinds):
                    with self.subTest(origin=origin, order=order):
                        self.assertEqual(self.check_projection(packet(origin, map(evidence, order)), wanted), reference)
                        cases += 1
        self.assertEqual(cases, 32)

    def test_all_five_field_binding_combinations(self):
        # 2 origins x 2 terminal event kinds x 32 match masks = 128 actual inputs.
        fields = ("provider", "original_message_id", "original_thread_id", "sender", "recipient")
        for origin, kind, mask in product(("provider", "legacy"), ("failed", "delivered"), product((False, True), repeat=5)):
            event = evidence(kind)
            for field, matches in zip(fields, mask):
                if not matches:
                    event[field] = "different-" + event[field]
            expected = ("DELIVERY_FAILED" if kind == "failed" else "DELIVERED_EVIDENCE") if all(mask) else "DELIVERY_UNKNOWN"
            with self.subTest(origin=origin, kind=kind, matches=mask):
                artifact = self.check_projection(packet(origin, [event]), expected)
                self.assertIs(artifact["evaluated_evidence"][0]["bound_to_submission"], all(mask))

    def test_no_origin_and_simultaneous_origins(self):
        self.check_projection(packet("none"), "UNSENT")
        with self.assertRaises(engine.DeliveryTruthError):
            engine.compile_delivery_truth(packet("none", [evidence("delivered")]))
        both = packet("provider")
        both["legacy_local_sent"] = source()
        with self.assertRaises(engine.DeliveryTruthError):
            engine.compile_delivery_truth(both)

    def test_old_shape_matches_explicit_absent_legacy(self):
        for kind in (None, "failed", "delivered", "delayed"):
            extended = packet("provider", [] if kind is None else [evidence(kind)])
            old = deepcopy(extended)
            del old["legacy_local_sent"]
            with self.subTest(kind=kind):
                self.assertEqual(engine.compile_delivery_truth(old), engine.compile_delivery_truth(extended))

    def test_receipt_rehash_does_not_validate_changed_meaning(self):
        supplied = packet("legacy", [evidence("failed")])
        for section, key, value in [
            ("collision_projection", "provider_submission_observed", True),
            ("collision_projection", "same_route_dedupe_hold", False),
            ("collision_projection", "counts_as_contacted", True),
            ("collision_projection", "counts_as_revenue", True),
            ("authority", "send_authorized", True),
            ("authority", "payment_authorized", 0),
        ]:
            with self.subTest(section=section, key=key):
                artifact = engine.compile_delivery_truth(supplied)
                artifact[section][key] = value
                rehash(artifact)
                outcome = engine.verify_delivery_truth(supplied, artifact)
                self.assertIs(outcome["valid"], False)
                self.assertEqual(outcome["reason"], "semantic_recompile_mismatch")

    def test_projection_and_source_copies_are_detached(self):
        supplied = packet("legacy", [evidence("delivered")])
        artifact = engine.compile_delivery_truth(supplied)
        baseline = deepcopy(artifact)
        projection = engine.collision_projection(artifact)
        projection["counts_as_contacted"] = False
        supplied["legacy_local_sent"]["purpose"] = "Changed caller record"
        self.assertEqual(artifact, baseline)
        self.assertIs(engine.verify_delivery_truth(supplied, artifact)["valid"], False)

    def test_legacy_transition_never_adds_a_provider_submission_stage(self):
        for kinds in ((), ("delivered",), ("failed",), ("failed", "delivered")):
            artifact = engine.compile_delivery_truth(packet("legacy", map(evidence, kinds)))
            with self.subTest(kinds=kinds):
                self.assertNotIn("PROVIDER_SUBMITTED_PENDING_DELIVERY", artifact["state_transition"])
                self.assertIs(artifact["evidence_claims"]["provider_submission_retained"], False)
                self.assertIs(artifact["evidence_claims"]["legacy_local_sent_retained"], True)

    def test_unbound_positive_cannot_cancel_bound_failure_or_reverse(self):
        for origin, terminal, unrelated in product(("provider", "legacy"), ("failed", "delivered"), ("failed", "delivered")):
            event = evidence(unrelated)
            event.update(id="unrelated-" + unrelated, original_message_id="other-message",
                         source_ref="synthetic:h7q3:unrelated", source_sha256="e" * 64)
            expected = "DELIVERY_FAILED" if terminal == "failed" else "DELIVERED_EVIDENCE"
            with self.subTest(origin=origin, terminal=terminal, unrelated=unrelated):
                self.check_projection(packet(origin, [evidence(terminal), event]), expected)


if __name__ == "__main__":
    unittest.main()
