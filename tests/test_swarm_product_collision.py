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


def canon(v):
    return json.dumps(
        v,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def root(search):
    payload = {
        k: search[k]
        for k in (
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
    for fam in families:
        for term in fam["terms"]:
            for provider in (
                "GITHUB_ISSUES",
                "GITHUB_PRS",
                "GITHUB_CODE",
                "SLACK",
            ):
                s = {
                    "provider": provider,
                    "family_id": fam["family_id"],
                    "query": term,
                    "observed_at": "2026-09-15T05:15:20Z",
                    "state": "COMPLETE",
                    "hits": [],
                }
                s["retained_root"] = root(s)
                searches.append(s)
    return {
        "schema": "swarm-product-collision-preflight/v1",
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
            "created_at": "2026-09-15T05:15:16Z",
            "signature": {
                "actors": ["franchisee"],
                "objects": ["royalty"],
                "actions": ["reconciliation"],
            },
        },
        "families": families,
        "searches": searches,
    }


def find_search(d, provider, fid, query):
    for s in d["searches"]:
        if (
            s["provider"] == provider
            and s["family_id"] == fid
            and s["query"] == query
        ):
            return s
    raise AssertionError((provider, fid, query))


def packet(raw):
    return json.loads(compile_preflight(raw)["packet.json"])


class Tests(unittest.TestCase):
    def test_clear(self):
        p = packet(base())
        self.assertEqual(p["status"], "CLEAR_ON_SUPPLIED_EVIDENCE")
        self.assertEqual(p["coverage"]["requiredSearchRows"], 24)

    def test_earlier_exact_collision(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["hits"] = [hit()]
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "COLLISION")
        self.assertEqual(p["canonicalPriorCarrier"]["owner"], "Z-OLD")

    def test_declared_synonym_collision(self):
        d = base()
        synonym_sig = {
            "actors": ["franchise-owner"],
            "objects": ["license-fee"],
            "actions": ["reconcile"],
        }
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchise-owner",
        )
        s["hits"] = [hit(sig=synonym_sig)]
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "COLLISION")

    def test_each_synonym_term_has_its_own_required_search(self):
        d = base()
        d["searches"] = [
            s
            for s in d["searches"]
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

    def test_github_scope_narrowing_query_rejected(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["query"] = "franchisee repo:irrelevant/empty"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_slack_scope_narrowing_query_rejected(self):
        d = base()
        s = find_search(
            d,
            "SLACK",
            "actor-franchisee",
            "franchisee",
        )
        s["query"] = "franchisee in:empty-channel"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_combined_and_query_rejected(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["query"] = "franchise-owner franchisee"
        s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_same_hit_changed_evidence_holds_even_when_semantically_unrelated(self):
        d = base()
        a = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        b = find_search(
            d,
            "GITHUB_PRS",
            "actor-franchisee",
            "franchisee",
        )
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
        a = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        b = find_search(
            d,
            "GITHUB_PRS",
            "actor-franchisee",
            "franchisee",
        )
        a["hits"] = [hit(sig={
            "actors": ["carrier"],
            "objects": ["freight"],
            "actions": ["audit"],
        })]
        b["hits"] = [hit(sig={
            "actors": ["vendor"],
            "objects": ["invoice"],
            "actions": ["settlement"],
        })]
        a["retained_root"] = root(a)
        b["retained_root"] = root(b)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn("CONFLICTING_HIT_METADATA:gh:1", p["reasons"])

    def test_identical_hit_across_searches_is_not_a_conflict(self):
        d = base()
        a = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        b = find_search(
            d,
            "GITHUB_PRS",
            "actor-franchisee",
            "franchisee",
        )
        h = hit()
        a["hits"] = [copy.deepcopy(h)]
        b["hits"] = [copy.deepcopy(h)]
        a["retained_root"] = root(a)
        b["retained_root"] = root(b)
        p = packet(d)
        self.assertEqual(p["status"], "COLLISION")
        self.assertNotIn("CONFLICTING_HIT_METADATA:gh:1", p["reasons"])
        self.assertEqual(
            len(p["earlierCollisions"][0]["evidenceOrigins"]),
            2,
        )

    def test_later_duplicate_does_not_displace(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["hits"] = [hit(created="2026-09-15T05:15:20Z")]
        s["observed_at"] = "2026-09-15T05:15:25Z"
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "CLEAR_ON_SUPPLIED_EVIDENCE")
        self.assertEqual(len(p["laterDuplicates"]), 1)

    def test_chatter_not_ownership(self):
        d = base()
        s = find_search(
            d,
            "SLACK",
            "actor-franchisee",
            "franchisee",
        )
        s["hits"] = [
            hit(
                kind="SLACK_CHATTER",
                claim="MENTION",
            )
        ]
        s["retained_root"] = root(s)
        self.assertEqual(
            packet(d)["status"],
            "CLEAR_ON_SUPPLIED_EVIDENCE",
        )

    def test_required_provider_universe_cannot_shrink(self):
        d = base()
        d["required_providers"].remove("GITHUB_CODE")
        d["searches"] = [
            s
            for s in d["searches"]
            if s["provider"] != "GITHUB_CODE"
        ]
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_omitted_family_cannot_shrink_semantic_universe(self):
        d = base()
        omitted = d["families"].pop()
        d["searches"] = [
            s
            for s in d["searches"]
            if s["family_id"] != omitted["family_id"]
        ]
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_family_must_anchor_exactly_one_candidate_token(self):
        d = base()
        d["families"][0]["terms"].append("royalty")
        for s in d["searches"]:
            if s["family_id"] == d["families"][0]["family_id"]:
                s["retained_root"] = root(s)
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_search_before_candidate_holds(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["observed_at"] = "2026-09-15T05:15:10Z"
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn(
            "SEARCH_BEFORE_CANDIDATE:GITHUB_ISSUES:actor-franchisee:franchisee",
            p["reasons"],
        )

    def test_future_hit_holds(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["hits"] = [hit(created="2026-09-15T05:16:00Z")]
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn("FUTURE_HIT:gh:1", p["reasons"])

    def test_hit_after_search_observation_holds(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["hits"] = [hit(created="2026-09-15T05:15:25Z")]
        s["retained_root"] = root(s)
        p = packet(d)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        self.assertIn(
            "HIT_AFTER_SEARCH_OBSERVATION:gh:1",
            p["reasons"],
        )

    def test_rate_limit_holds(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["state"] = "RATE_LIMITED"
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "UNKNOWN_HOLD")

    def test_stale_holds(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["observed_at"] = "2026-09-15T05:00:00Z"
        s["retained_root"] = root(s)
        self.assertEqual(packet(d)["status"], "UNKNOWN_HOLD")

    def test_root_mismatch_rejected(self):
        d = base()
        d["searches"][0]["retained_root"] = "0" * 64
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_semantically_unrelated_does_not_collide(self):
        d = base()
        s = find_search(
            d,
            "GITHUB_ISSUES",
            "actor-franchisee",
            "franchisee",
        )
        s["hits"] = [
            hit(
                sig={
                    "actors": ["carrier"],
                    "objects": ["freight"],
                    "actions": ["audit"],
                }
            )
        ]
        s["retained_root"] = root(s)
        self.assertEqual(
            packet(d)["status"],
            "CLEAR_ON_SUPPLIED_EVIDENCE",
        )

    def test_input_order_invariance(self):
        a = base()
        b = copy.deepcopy(a)
        b["families"].reverse()
        b["searches"].reverse()
        b["required_providers"].reverse()
        self.assertEqual(
            compile_preflight(a),
            compile_preflight(b),
        )

    def test_bundle_tamper_rejected(self):
        d = base()
        bundle = compile_preflight(d)
        self.assertTrue(verify_bundle(d, bundle))
        bundle = dict(bundle)
        bundle["review.md"] += b"tamper"
        self.assertFalse(verify_bundle(d, bundle))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(CollisionError):
            load_json_strict('{"a":1,"a":2}')

    def test_bool_integer_rejected(self):
        d = base()
        d["max_age_seconds"] = True
        with self.assertRaises(CollisionError):
            compile_preflight(d)

    def test_control_character_rejected(self):
        d = base()
        d["candidate"]["title"] = "bad\nline"
        with self.assertRaises(CollisionError):
            compile_preflight(d)


if __name__ == "__main__":
    unittest.main()
