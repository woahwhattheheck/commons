import copy
import hashlib
import json
import unittest

from tools.swarm_product_collision.engine import (
    CollisionError,
    compile_preflight,
    load_json_strict,
    verify_bundle,
)


def canon(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def root(search):
    payload = {
        key: search[key]
        for key in (
            "provider",
            "family_id",
            "query",
            "observed_at",
            "state",
            "hits",
        )
    }
    return hashlib.sha256(canon(payload)).hexdigest()


def hit(
    hid="gh:1",
    created="2026-09-15T04:00:00Z",
    kind="GITHUB_ISSUE",
    claim="TAKE",
    op="OLD-OP",
    owner="Z-OLD",
    sig=None,
    evidence="a" * 64,
):
    sig = sig or {
        "actors": ["franchisee"],
        "objects": ["royalty"],
        "actions": ["reconciliation"],
    }
    return {
        "hit_id": hid,
        "url": "https://github.com/acme/repo/issues/1",
        "created_at": created,
        "kind": kind,
        "claim_state": claim,
        "operation_id": op,
        "owner": owner,
        "signature": sig,
        "evidence_sha256": evidence,
    }


def base():
    families = [
        {
            "family_id": "actor-franchisee",
            "terms": ["franchise-owner", "franchisee"],
        },
        {
            "family_id": "object-royalty",
            "terms": ["license-fee", "royalty"],
        },
        {
            "family_id": "action-reconciliation",
            "terms": ["reconcile", "reconciliation"],
        },
    ]
    searches = []
    for family in families:
        for term in family["terms"]:
            for provider in (
                "GITHUB_ISSUES",
                "GITHUB_PRS",
                "GITHUB_CODE",
                "SLACK",
            ):
                search = {
                    "provider": provider,
                    "family_id": family["family_id"],
                    "query": term,
                    "observed_at": "2026-09-15T05:15:20Z",
                    "state": "COMPLETE",
                    "hits": [],
                }
                search["retained_root"] = root(search)
                searches.append(search)
    return {
        "schema": "swarm-product-collision-preflight/v2",
        "evaluation_time": "2026-09-15T05:15:30Z",
        "max_age_seconds": 300,
        "required_providers": [
            "GITHUB_ISSUES",
            "GITHUB_PRS",
            "GITHUB_CODE",
            "SLACK",
        ],
        "candidate": {
            "operation_id": "NEW-OP",
            "seat_id": "Z-NEW",
            "project": "commons",
            "title": "New lane",
            "signature": {
                "actors": ["franchisee"],
                "objects": ["royalty"],
                "actions": ["reconciliation"],
            },
        },
        "families": families,
        "searches": searches,
    }


def find_search(data, provider, family_id, query):
    for search in data["searches"]:
        if (
            search["provider"] == provider
            and search["family_id"] == family_id
            and search["query"] == query
        ):
            return search
    raise AssertionError((provider, family_id, query))


def packet(raw):
    return json.loads(compile_preflight(raw)["packet.json"])


class Tests(unittest.TestCase):
    def test_clear_is_explicitly_non_authoritative(self):
        p = packet(base())
        self.assertEqual(p["status"], "CENSUS_CLEAR_CALLER_TIME_UNVERIFIED")
        self.assertEqual(p["coverage"]["requiredSearchRows"], 24)
        self.assertEqual(p["timeAuthority"], "CALLER_DECLARED_SELF_CONSISTENCY_ONLY")
        self.assertEqual(p["candidateEpochAuthority"], "ABSENT_NOT_ESTABLISHED")
        self.assertFalse(p["antiRaceChronologyEstablished"])
        self.assertFalse(p["providerOriginAuthenticated"])
        self.assertFalse(p["currentOwnerEstablished"])
        self.assertFalse(p["takeAuthorized"])
        self.assertFalse(p["outboundAuthorized"])
        self.assertFalse(p["mergeAuthorized"])

    def test_any_matching_durable_carrier_collides_without_candidate_epoch(self):
        d = base()
        s = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        s["hits"] = [hit(created="2026-09-15T05:15:19Z")]
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "COLLISION")
        self.assertEqual(p["canonicalCarrier"]["owner"], "Z-OLD")

    def test_declared_synonym_collision(self):
        d = base()
        s = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchise-owner")
        s["hits"] = [hit(sig={
            "actors": ["franchise-owner"],
            "objects": ["license-fee"],
            "actions": ["reconcile"],
        })]
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "COLLISION")

    def test_same_operation_collides_even_if_signature_differs(self):
        d = base()
        s = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        s["hits"] = [hit(op="NEW-OP", sig={
            "actors": ["carrier"],
            "objects": ["freight"],
            "actions": ["audit"],
        })]
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "COLLISION")

    def test_chatter_does_not_establish_ownership(self):
        d = base()
        s = find_search(d, "SLACK", "actor-franchisee", "franchisee")
        s["hits"] = [hit(kind="SLACK_CHATTER", claim="MENTION")]
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "CENSUS_CLEAR_CALLER_TIME_UNVERIFIED")

    def test_semantically_unrelated_does_not_collide(self):
        d = base()
        s = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        s["hits"] = [hit(sig={
            "actors": ["carrier"],
            "objects": ["freight"],
            "actions": ["audit"],
        })]
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "CENSUS_CLEAR_CALLER_TIME_UNVERIFIED")

    def test_each_synonym_requires_each_provider_row(self):
        d = base()
        d["searches"] = [
            s for s in d["searches"]
            if not (
                s["provider"] == "SLACK"
                and s["family_id"] == "actor-franchisee"
                and s["query"] == "franchise-owner"
            )
        ]
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn(
            "MISSING_SEARCH:SLACK:actor-franchisee:franchise-owner",
            p["reasons"],
        )

    def test_provider_universe_cannot_shrink(self):
        d = base()
        d["required_providers"].remove("GITHUB_CODE")
        d["searches"] = [s for s in d["searches"] if s["provider"] != "GITHUB_CODE"]
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_omitted_family_cannot_shrink_semantic_universe(self):
        d = base()
        omitted = d["families"].pop()
        d["searches"] = [s for s in d["searches"] if s["family_id"] != omitted["family_id"]]
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_family_must_anchor_one_candidate_token(self):
        d = base()
        d["families"][0]["terms"].append("royalty")
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_family_terms_cannot_overlap(self):
        d = base()
        d["families"][1]["terms"].append("franchisee")
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_candidate_operator_shaped_anchor_is_rejected(self):
        d = base()
        d["candidate"]["signature"]["actors"] = ["repo:irrelevant/empty"]
        d["families"][0]["terms"] = ["repo:irrelevant/empty", "franchisee"]
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_family_operator_shaped_term_is_rejected(self):
        d = base()
        d["families"][0]["terms"].append("in:empty-channel")
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_slash_shaped_scope_term_is_rejected(self):
        d = base()
        d["families"][0]["terms"].append("repo/empty")
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_reserved_boolean_term_is_rejected(self):
        d = base()
        d["families"][0]["terms"].append("or")
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_appended_github_scope_query_is_rejected(self):
        d = base()
        s = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        s["query"] = "franchisee repo:irrelevant/empty"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_appended_slack_scope_query_is_rejected(self):
        d = base()
        s = find_search(d, "SLACK", "actor-franchisee", "franchisee")
        s["query"] = "franchisee in:empty-channel"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_combined_and_query_is_rejected(self):
        d = base()
        s = find_search(d, "GITHUB_PRS", "actor-franchisee", "franchisee")
        s["query"] = "franchise-owner franchisee"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_caller_candidate_created_at_is_rejected_not_trusted(self):
        d = base()
        d["candidate"]["created_at"] = "1900-01-01T00:00:00Z"
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_future_search_rejected(self):
        d = base()
        s = d["searches"][0]
        s["observed_at"] = "2026-09-15T05:16:00Z"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_stale_search_holds(self):
        d = base()
        s = d["searches"][0]
        s["observed_at"] = "2026-09-15T05:00:00Z"
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "UNKNOWN_HOLD")

    def test_rate_limit_holds(self):
        d = base()
        s = d["searches"][0]
        s["state"] = "RATE_LIMITED"
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "UNKNOWN_HOLD")

    def test_future_hit_holds(self):
        d = base()
        s = d["searches"][0]
        s["hits"] = [hit(created="2026-09-15T05:16:00Z")]
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn("FUTURE_HIT:gh:1", p["reasons"])

    def test_hit_after_search_observation_holds(self):
        d = base()
        s = d["searches"][0]
        s["hits"] = [hit(created="2026-09-15T05:15:25Z")]
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn("HIT_AFTER_SEARCH_OBSERVATION:gh:1", p["reasons"])

    def test_root_mismatch_rejected(self):
        d = base()
        d["searches"][0]["retained_root"] = "0" * 64
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_same_hit_changed_evidence_holds_before_semantic_filter(self):
        d = base()
        a = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        b = find_search(d, "GITHUB_PRS", "actor-franchisee", "franchisee")
        unrelated = {
            "actors": ["carrier"],
            "objects": ["freight"],
            "actions": ["audit"],
        }
        a["hits"] = [hit(sig=unrelated, evidence="a" * 64)]
        b["hits"] = [hit(sig=unrelated, evidence="b" * 64)]
        a["retained_root"] = root(a)
        b["retained_root"] = root(b)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn("CONFLICTING_HIT_METADATA:gh:1", p["reasons"])

    def test_same_hit_changed_signature_holds_before_semantic_filter(self):
        d = base()
        a = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        b = find_search(d, "GITHUB_PRS", "actor-franchisee", "franchisee")
        a["hits"] = [hit(sig={
            "actors": ["carrier"], "objects": ["freight"], "actions": ["audit"]
        })]
        b["hits"] = [hit(sig={
            "actors": ["vendor"], "objects": ["invoice"], "actions": ["settlement"]
        })]
        a["retained_root"] = root(a)
        b["retained_root"] = root(b)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn("CONFLICTING_HIT_METADATA:gh:1", p["reasons"])

    def test_identical_hit_across_searches_aggregates_origins(self):
        d = base()
        a = find_search(d, "GITHUB_ISSUES", "actor-franchisee", "franchisee")
        b = find_search(d, "GITHUB_PRS", "actor-franchisee", "franchisee")
        h = hit()
        a["hits"] = [copy.deepcopy(h)]
        b["hits"] = [copy.deepcopy(h)]
        a["retained_root"] = root(a)
        b["retained_root"] = root(b)
        p = packet(d)
        self.assertEqual(p["status"], "COLLISION")
        self.assertEqual(len(p["collisions"][0]["evidenceOrigins"]), 2)

    def test_canonical_carrier_is_earliest_provider_hit(self):
        d = base()
        a = d["searches"][0]
        b = d["searches"][1]
        a["hits"] = [hit(hid="gh:later", created="2026-09-15T04:30:00Z")]
        b["hits"] = [hit(hid="gh:earlier", created="2026-09-15T04:00:00Z", owner="Z-FIRST")]
        a["retained_root"] = root(a)
        b["retained_root"] = root(b)
        p = packet(d)
        self.assertEqual(p["canonicalCarrier"]["owner"], "Z-FIRST")

    def test_input_order_invariance(self):
        a = base()
        b = copy.deepcopy(a)
        b["families"].reverse()
        b["searches"].reverse()
        b["required_providers"].reverse()
        self.assertEqual(compile_preflight(a), compile_preflight(b))

    def test_bundle_tamper_rejected(self):
        d = base()
        bundle = compile_preflight(d)
        tampered = dict(bundle)
        tampered["review.md"] += b"x"
        self.assertFalse(verify_bundle(d, tampered))
        self.assertTrue(verify_bundle(d, bundle))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(CollisionError):
            load_json_strict('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(CollisionError):
            load_json_strict('{"a":NaN}')

    def test_control_character_rejected(self):
        d = base()
        d["candidate"]["title"] = "bad\u202etitle"
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_receipt_binds_all_output_leaves(self):
        bundle = compile_preflight(base())
        receipt = json.loads(bundle["receipt.json"])
        self.assertEqual(receipt["schema"], "swarm-product-collision-preflight/v2/receipt")
        self.assertEqual(receipt["packetSha256"], hashlib.sha256(bundle["packet.json"]).hexdigest())
        self.assertEqual(receipt["markdownSha256"], hashlib.sha256(bundle["review.md"]).hexdigest())
        self.assertEqual(receipt["csvSha256"], hashlib.sha256(bundle["collisions.csv"]).hexdigest())

    def test_markdown_truth_labels_no_take_authority(self):
        md = compile_preflight(base())["review.md"].decode()
        self.assertIn("Anti-race chronology established: **false**", md)
        self.assertIn("TAKE authority: **false**", md)
        self.assertIn("does not establish a trusted candidate epoch", md)


if __name__ == "__main__":
    unittest.main()
