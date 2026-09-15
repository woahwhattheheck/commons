import hashlib
import inspect
import json
import unittest
from pathlib import Path

from alias import (
    ContractError,
    OBSERVATION_SCHEMA,
    REGISTRY_SCHEMA,
    STATUS_AMBIGUOUS,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    compile_initial_registry,
    compile_transition,
    parse_registry,
    resolve_against,
    resolve_current,
    verify_current,
    verify_result,
)


def alias_id(value):
    return {"kind": "official_id", "value": value}


def alias_url(value):
    return {"kind": "authority_url", "value": value}


def opp(key, buyer, aliases):
    return {"canonical_opportunity_key": key, "buyer_key": buyer, "aliases": aliases}


def registry(opportunities, generation=1, previous=None):
    return {
        "schema": REGISTRY_SCHEMA,
        "generation": generation,
        "previous_registry_sha256": previous,
        "opportunities": opportunities,
    }


def observation(buyer, aliases):
    return {"schema": OBSERVATION_SCHEMA, "buyer_key": buyer, "aliases": aliases}


BASE_OPPS = [
    opp(
        "opp_lacsd_04254",
        "buyer_lacsd",
        [
            alias_id("RFP 04254"),
            alias_id("LACSD-04254"),
            alias_url("https://www.lacsd.org/contracts/04254"),
            alias_url("https://lacsd.procureware.com/bids/04254"),
        ],
    ),
    opp("opp_lacsd_09999", "buyer_lacsd", [alias_id("RFP-09999")]),
]


class OpportunityIdentityAliasTests(unittest.TestCase):
    def setUp(self):
        self.raw = compile_initial_registry(registry(BASE_OPPS))

    def test_registered_id_aliases_collapse(self):
        one = resolve_against(observation("buyer_lacsd", [alias_id("RFP 04254")]), self.raw)
        two = resolve_against(observation("buyer_lacsd", [alias_id("lacsd-04254")]), self.raw)
        self.assertEqual(one["status"], STATUS_RESOLVED)
        self.assertEqual(one["canonical_opportunity_key"], "opp_lacsd_04254")
        self.assertEqual(one["canonical_opportunity_key"], two["canonical_opportunity_key"])

    def test_registered_buyer_and_portal_urls_collapse(self):
        result = resolve_against(
            observation(
                "buyer_lacsd",
                [
                    alias_url("https://WWW.LACSD.ORG/contracts/04254"),
                    alias_url("https://LACSD.PROCUREWARE.COM:443/bids/04254"),
                ],
            ),
            self.raw,
        )
        self.assertEqual(result["status"], STATUS_RESOLVED)
        self.assertEqual(result["canonical_opportunity_key"], "opp_lacsd_04254")

    def test_unknown_alias_does_not_mint_key(self):
        result = resolve_against(observation("buyer_lacsd", [alias_id("RFP-NEW")]), self.raw)
        self.assertEqual(result["status"], STATUS_UNRESOLVED)
        self.assertIsNone(result["canonical_opportunity_key"])

    def test_known_plus_unknown_is_unresolved(self):
        result = resolve_against(
            observation("buyer_lacsd", [alias_id("RFP-04254"), alias_id("RFP-NEW")]),
            self.raw,
        )
        self.assertEqual(result["status"], STATUS_UNRESOLVED)
        self.assertIsNone(result["canonical_opportunity_key"])

    def test_mixed_known_opportunities_are_ambiguous(self):
        result = resolve_against(
            observation("buyer_lacsd", [alias_id("RFP-04254"), alias_id("RFP-09999")]),
            self.raw,
        )
        self.assertEqual(result["status"], STATUS_AMBIGUOUS)
        self.assertIsNone(result["canonical_opportunity_key"])

    def test_cross_buyer_transplant_is_unresolved(self):
        result = resolve_against(observation("buyer_other", [alias_id("RFP-04254")]), self.raw)
        self.assertEqual(result["status"], STATUS_UNRESOLVED)

    def test_observation_rejects_caller_canonical_key(self):
        value = observation("buyer_lacsd", [alias_id("RFP-04254")])
        value["canonical_opportunity_key"] = "opp_lacsd_04254"
        with self.assertRaises(ContractError):
            resolve_against(value, self.raw)

    def test_observation_rejects_caller_status(self):
        value = observation("buyer_lacsd", [alias_id("RFP-04254")])
        value["status"] = STATUS_RESOLVED
        with self.assertRaises(ContractError):
            resolve_against(value, self.raw)

    def test_conflicting_alias_registry_rejected(self):
        value = registry([
            opp("opp_one", "buyer_lacsd", [alias_id("RFP-1")]),
            opp("opp_two", "buyer_lacsd", [alias_id("rfp-1")]),
        ])
        with self.assertRaises(ContractError):
            compile_initial_registry(value)

    def test_duplicate_canonical_key_rejected(self):
        value = registry([
            opp("opp_same", "buyer_one", [alias_id("A")]),
            opp("opp_same", "buyer_two", [alias_id("B")]),
        ])
        with self.assertRaises(ContractError):
            compile_initial_registry(value)

    def test_duplicate_normalized_alias_within_opportunity_rejected(self):
        value = registry([opp("opp_one", "buyer_lacsd", [alias_id("RFP 1"), alias_id("rfp-1")])])
        with self.assertRaises(ContractError):
            compile_initial_registry(value)

    def test_same_alias_can_exist_under_different_buyers(self):
        value = registry([
            opp("opp_one", "buyer_one", [alias_id("RFP-1")]),
            opp("opp_two", "buyer_two", [alias_id("RFP-1")]),
        ])
        raw = compile_initial_registry(value)
        self.assertEqual(
            resolve_against(observation("buyer_one", [alias_id("RFP-1")]), raw)["canonical_opportunity_key"],
            "opp_one",
        )
        self.assertEqual(
            resolve_against(observation("buyer_two", [alias_id("RFP-1")]), raw)["canonical_opportunity_key"],
            "opp_two",
        )

    def test_initial_generation_contract(self):
        bad = registry([], generation=2, previous="0" * 64)
        with self.assertRaises(ContractError):
            compile_initial_registry(bad)

    def test_append_alias_transition(self):
        old = self.raw
        parsed = parse_registry(old)
        value = registry(
            [
                dict(BASE_OPPS[0], aliases=BASE_OPPS[0]["aliases"] + [alias_id("COUNTY-04254")]),
                BASE_OPPS[1],
            ],
            generation=2,
            previous=hashlib.sha256(old).hexdigest(),
        )
        new = compile_transition(old, value)
        result = resolve_against(observation("buyer_lacsd", [alias_id("county-04254")]), new)
        self.assertEqual(result["canonical_opportunity_key"], "opp_lacsd_04254")
        self.assertEqual(parse_registry(new)["generation"], parsed["generation"] + 1)

    def test_append_new_opportunity_transition(self):
        old = self.raw
        value = registry(
            BASE_OPPS + [opp("opp_lacsd_12345", "buyer_lacsd", [alias_id("RFP-12345")])],
            generation=2,
            previous=hashlib.sha256(old).hexdigest(),
        )
        new = compile_transition(old, value)
        self.assertEqual(
            resolve_against(observation("buyer_lacsd", [alias_id("RFP-12345")]), new)["canonical_opportunity_key"],
            "opp_lacsd_12345",
        )

    def test_transition_rejects_generation_skip(self):
        value = registry(BASE_OPPS, generation=3, previous=hashlib.sha256(self.raw).hexdigest())
        with self.assertRaises(ContractError):
            compile_transition(self.raw, value)

    def test_transition_rejects_previous_digest_mismatch(self):
        value = registry(BASE_OPPS, generation=2, previous="0" * 64)
        with self.assertRaises(ContractError):
            compile_transition(self.raw, value)

    def test_transition_rejects_canonical_removal(self):
        value = registry([BASE_OPPS[0]], generation=2, previous=hashlib.sha256(self.raw).hexdigest())
        with self.assertRaises(ContractError):
            compile_transition(self.raw, value)

    def test_transition_rejects_alias_removal(self):
        changed = dict(BASE_OPPS[0], aliases=[alias_id("RFP-04254")])
        value = registry([changed, BASE_OPPS[1]], generation=2, previous=hashlib.sha256(self.raw).hexdigest())
        with self.assertRaises(ContractError):
            compile_transition(self.raw, value)

    def test_transition_rejects_buyer_reassignment(self):
        changed = dict(BASE_OPPS[0], buyer_key="buyer_other")
        value = registry([changed, BASE_OPPS[1]], generation=2, previous=hashlib.sha256(self.raw).hexdigest())
        with self.assertRaises(ContractError):
            compile_transition(self.raw, value)

    def test_registry_bytes_are_deterministic_under_permutation(self):
        raw_a = compile_initial_registry(registry(BASE_OPPS))
        permuted = [
            dict(BASE_OPPS[1], aliases=list(reversed(BASE_OPPS[1]["aliases"]))),
            dict(BASE_OPPS[0], aliases=list(reversed(BASE_OPPS[0]["aliases"]))),
        ]
        raw_b = compile_initial_registry(registry(permuted))
        self.assertEqual(raw_a, raw_b)

    def test_alias_set_digest_is_deterministic_under_permutation(self):
        aliases = [alias_id("RFP-04254"), alias_url("https://lacsd.procureware.com/bids/04254")]
        a = resolve_against(observation("buyer_lacsd", aliases), self.raw)
        b = resolve_against(observation("buyer_lacsd", list(reversed(aliases))), self.raw)
        self.assertEqual(a["alias_set_sha256"], b["alias_set_sha256"])

    def test_result_tamper_fails_verifier(self):
        obs = observation("buyer_lacsd", [alias_id("RFP-04254")])
        result = resolve_against(obs, self.raw)
        self.assertTrue(verify_result(obs, self.raw, result))
        tampered = dict(result, canonical_opportunity_key="opp_lacsd_09999")
        self.assertFalse(verify_result(obs, self.raw, tampered))

    def test_registry_requires_canonical_bytes(self):
        pretty = json.dumps(registry(BASE_OPPS), indent=2).encode()
        with self.assertRaises(ContractError):
            parse_registry(pretty)

    def test_duplicate_json_keys_rejected(self):
        raw = (
            b'{"generation":1,"generation":1,"opportunities":[],"previous_registry_sha256":null,'
            b'"schema":"opportunity-identity-alias-registry/v1"}'
        )
        with self.assertRaises(ContractError):
            parse_registry(raw)

    def test_nonfinite_json_rejected(self):
        raw = (
            b'{"generation":NaN,"opportunities":[],"previous_registry_sha256":null,'
            b'"schema":"opportunity-identity-alias-registry/v1"}'
        )
        with self.assertRaises(ContractError):
            parse_registry(raw)

    def test_http_authority_url_rejected(self):
        with self.assertRaises(ContractError):
            compile_initial_registry(registry([opp("opp_one", "buyer_one", [alias_url("http://example.com/rfp/1")])]))

    def test_current_api_does_not_accept_registry_path(self):
        self.assertEqual(list(inspect.signature(resolve_current).parameters), ["observation"])
        self.assertEqual(list(inspect.signature(verify_current).parameters), ["observation", "result"])

    def test_checked_in_registry_is_truthfully_empty_and_unresolved(self):
        current_path = Path(__file__).with_name("registry.json")
        current = parse_registry(current_path.read_bytes())
        self.assertEqual(current["opportunities"], [])
        obs = observation("buyer_lacsd", [alias_id("RFP-04254")])
        result = resolve_current(obs)
        self.assertEqual(result["status"], STATUS_UNRESOLVED)
        self.assertIsNone(result["canonical_opportunity_key"])
        self.assertTrue(verify_current(obs, result))

    def test_result_has_no_external_action_fields(self):
        result = resolve_against(observation("buyer_lacsd", [alias_id("RFP-04254")]), self.raw)
        forbidden = {"authorized", "approved", "permission", "send", "contact", "payment", "submission", "revenue"}
        self.assertTrue(forbidden.isdisjoint(result))


if __name__ == "__main__":
    unittest.main()
