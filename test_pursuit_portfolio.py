from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from revenue.pursuit_portfolio.core import (
    INPUT_SCHEMA,
    POLICY_SCHEMA,
    PortfolioError,
    compile_portfolio,
    load_json_bytes,
    verify_compiled,
    write_compiled,
)

NOW = "2026-09-13T14:00:00Z"
START = "2026-09-13T00:00:00Z"
END = "2026-09-20T00:00:00Z"
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def canon(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def make_policy(pools=None, *, max_age=86400, revision=1):
    base = {
        "schema": POLICY_SCHEMA,
        "revision": revision,
        "horizon_start": START,
        "horizon_end": END,
        "evidence_max_age_seconds": max_age,
        "pools": sorted((pools or [
            {"pool_id": "proposal", "available_units": 10, "reserve_units": 0},
            {"pool_id": "engineering", "available_units": 10, "reserve_units": 0},
        ]), key=lambda row: row["pool_id"]),
    }
    return {**base, "policy_sha256": hashlib.sha256(canon(base)).hexdigest()}


def opp(
    oid,
    priority,
    effort,
    *,
    state="READY",
    deadline="2026-09-16T14:00:00Z",
    captured="2026-09-13T13:00:00Z",
    buffer=60,
    revision=1,
    source=SHA_A,
    receipt=SHA_B,
):
    return {
        "opportunity_id": oid,
        "revision": revision,
        "source_sha256": source,
        "upstream_receipt_sha256": receipt,
        "evidence_ref": f"evidence:{oid}",
        "evidence_captured_at": captured,
        "upstream_state": state,
        "response_deadline": deadline,
        "priority_units": priority,
        "effort": [{"pool_id": pool_id, "units": units} for pool_id, units in effort.items()],
        "min_buffer_minutes": buffer,
    }


def source(opportunities, pools=None, *, max_age=86400):
    return {
        "schema": INPUT_SCHEMA,
        "portfolio_id": "portfolio:owner-review",
        "policy": make_policy(pools, max_age=max_age),
        "opportunities": opportunities,
    }


class PortfolioTests(unittest.TestCase):
    def test_exact_optimizer_beats_naive_priority_greedy(self):
        pools = [
            {"pool_id": "p", "available_units": 6, "reserve_units": 0},
            {"pool_id": "e", "available_units": 6, "reserve_units": 0},
        ]
        data = source([
            opp("A", 9, {"p": 6, "e": 6}),
            opp("B", 6, {"p": 6}),
            opp("C", 6, {"e": 6}),
        ], pools)
        compiled = compile_portfolio(data, evaluated_at=NOW)
        self.assertEqual(compiled.result["selected_opportunity_ids"], ["B", "C"])
        self.assertEqual(compiled.result["selected_priority_units"], 12)

    def test_objective_prefers_more_rows_on_priority_tie(self):
        pools = [{"pool_id": "p", "available_units": 2, "reserve_units": 0}]
        data = source([
            opp("A", 10, {"p": 2}),
            opp("B", 5, {"p": 1}),
            opp("C", 5, {"p": 1}),
        ], pools)
        self.assertEqual(compile_portfolio(data, evaluated_at=NOW).result["selected_opportunity_ids"], ["B", "C"])

    def test_objective_prefers_less_effort_then_lexicographic_ids(self):
        pools = [{"pool_id": "p", "available_units": 2, "reserve_units": 0}]
        lower_effort = source([opp("A", 10, {"p": 2}), opp("B", 10, {"p": 1})], pools)
        self.assertEqual(compile_portfolio(lower_effort, evaluated_at=NOW).result["selected_opportunity_ids"], ["B"])
        lex = source([opp("B", 10, {"p": 1}), opp("A", 10, {"p": 1})], [{"pool_id": "p", "available_units": 1, "reserve_units": 0}])
        self.assertEqual(compile_portfolio(lex, evaluated_at=NOW).result["selected_opportunity_ids"], ["A"])

    def test_upstream_state_separation(self):
        data = source([
            opp("ready", 4, {"proposal": 1}, state="READY"),
            opp("curable", 3, {"proposal": 1}, state="CURABLE"),
            opp("hold", 999, {"proposal": 1}, state="HOLD"),
            opp("terminal", 999, {"proposal": 1}, state="TERMINAL"),
        ])
        rows = {x["opportunity_id"]: x for x in compile_portfolio(data, evaluated_at=NOW).result["opportunities"]}
        self.assertEqual(rows["ready"]["allocation_state"], "ALLOCATED_READY")
        self.assertEqual(rows["curable"]["allocation_state"], "CURABLE_RECOVERY_ALLOCATED")
        self.assertEqual(rows["hold"]["allocation_state"], "HOLD_UPSTREAM")
        self.assertEqual(rows["terminal"]["allocation_state"], "TERMINAL")

    def test_deadline_buffer_exact_boundary_is_live_but_one_second_short_is_breached(self):
        exact = source([opp("A", 1, {"proposal": 1}, deadline="2026-09-13T15:00:00Z", buffer=60)])
        row = compile_portfolio(exact, evaluated_at=NOW).result["opportunities"][0]
        self.assertEqual(row["allocation_state"], "ALLOCATED_READY")
        short = source([opp("A", 1, {"proposal": 1}, deadline="2026-09-13T14:59:59Z", buffer=60)])
        row = compile_portfolio(short, evaluated_at=NOW).result["opportunities"][0]
        self.assertEqual(row["allocation_state"], "DEADLINE_BUFFER_BREACHED")

    def test_deadline_now_is_breached_even_with_zero_buffer(self):
        data = source([opp("A", 1, {"proposal": 1}, deadline=NOW, buffer=0)])
        self.assertEqual(compile_portfolio(data, evaluated_at=NOW).result["opportunities"][0]["allocation_state"], "DEADLINE_BUFFER_BREACHED")

    def test_no_deadline_can_allocate(self):
        data = source([opp("A", 1, {"proposal": 1}, deadline="NO_DEADLINE", buffer=0)])
        self.assertEqual(compile_portfolio(data, evaluated_at=NOW).result["opportunities"][0]["allocation_state"], "ALLOCATED_READY")

    def test_reserve_is_not_allocatable(self):
        pools = [{"pool_id": "p", "available_units": 10, "reserve_units": 4}]
        data = source([opp("A", 10, {"p": 7}), opp("B", 6, {"p": 6})], pools)
        compiled = compile_portfolio(data, evaluated_at=NOW)
        self.assertEqual(compiled.result["selected_opportunity_ids"], ["B"])
        cap = compiled.result["capacity"][0]
        self.assertEqual((cap["usable_units"], cap["allocated_units"], cap["headroom_units"]), (6, 6, 0))

    def test_missing_capacity_pool_holds_only_affected_candidate(self):
        pools = [{"pool_id": "p", "available_units": 4, "reserve_units": 0}]
        data = source([opp("bad", 100, {"missing": 1}), opp("good", 1, {"p": 1})], pools)
        rows = {x["opportunity_id"]: x for x in compile_portfolio(data, evaluated_at=NOW).result["opportunities"]}
        self.assertEqual(rows["bad"]["allocation_state"], "HOLD")
        self.assertIn("MISSING_CAPACITY_POOL:missing", rows["bad"]["reasons"])
        self.assertEqual(rows["good"]["allocation_state"], "ALLOCATED_READY")

    def test_zero_capacity_yields_capacity_deferral_with_counterfactual(self):
        pools = [{"pool_id": "p", "available_units": 3, "reserve_units": 3}]
        data = source([opp("A", 1, {"p": 2})], pools)
        row = compile_portfolio(data, evaluated_at=NOW).result["opportunities"][0]
        self.assertEqual(row["allocation_state"], "DEFERRED_CAPACITY")
        self.assertEqual(row["individual_fit_counterfactual"], [{"additional_units": 2, "pool_id": "p"}])

    def test_counterfactual_reports_each_currently_limiting_pool(self):
        pools = [
            {"pool_id": "a", "available_units": 5, "reserve_units": 0},
            {"pool_id": "b", "available_units": 5, "reserve_units": 0},
        ]
        data = source([
            opp("incumbent", 10, {"a": 4, "b": 2}),
            opp("deferred", 8, {"a": 3, "b": 5}),
        ], pools)
        rows = {x["opportunity_id"]: x for x in compile_portfolio(data, evaluated_at=NOW).result["opportunities"]}
        self.assertEqual(rows["deferred"]["allocation_state"], "DEFERRED_CAPACITY")
        self.assertEqual(rows["deferred"]["individual_fit_counterfactual"], [
            {"additional_units": 2, "pool_id": "a"},
            {"additional_units": 2, "pool_id": "b"},
        ])

    def test_stale_and_future_evidence_hold(self):
        stale = source([opp("stale", 1, {"proposal": 1}, captured="2026-09-13T12:59:59Z")], max_age=3600)
        self.assertEqual(compile_portfolio(stale, evaluated_at=NOW).result["opportunities"][0]["reasons"], ["STALE_UPSTREAM_EVIDENCE"])
        future = source([opp("future", 1, {"proposal": 1}, captured="2026-09-13T14:00:01Z")])
        self.assertEqual(compile_portfolio(future, evaluated_at=NOW).result["opportunities"][0]["reasons"], ["FUTURE_UPSTREAM_EVIDENCE"])

    def test_input_order_invariance(self):
        pools = [{"pool_id": "p", "available_units": 2, "reserve_units": 0}]
        rows = [opp("C", 2, {"p": 1}), opp("A", 3, {"p": 1}), opp("B", 1, {"p": 1})]
        left = compile_portfolio(source(rows, pools), evaluated_at=NOW)
        right = compile_portfolio(source(list(reversed(rows)), list(reversed(pools))), evaluated_at=NOW)
        self.assertEqual(left.result_bytes, right.result_bytes)
        self.assertEqual(left.markdown_bytes, right.markdown_bytes)
        self.assertEqual(left.receipt_bytes, right.receipt_bytes)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(PortfolioError, "duplicate JSON key"):
            load_json_bytes(b'{"schema":"x","schema":"y"}')

    def test_floats_and_bool_as_int_rejected(self):
        with self.assertRaisesRegex(PortfolioError, "floating-point"):
            load_json_bytes(b'{"x":1.5}')
        data = source([opp("A", 1, {"proposal": 1})])
        data["opportunities"][0]["priority_units"] = True
        with self.assertRaisesRegex(PortfolioError, "bool forbidden"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_unsafe_integer_rejected(self):
        data = source([opp("A", 1, {"proposal": 1})])
        data["opportunities"][0]["priority_units"] = 10**20
        with self.assertRaisesRegex(PortfolioError, "out of range"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_secret_or_network_shaped_refs_rejected(self):
        data = source([opp("A", 1, {"proposal": 1})])
        data["opportunities"][0]["evidence_ref"] = "https://buyer.example/evidence"
        with self.assertRaisesRegex(PortfolioError, "PII/secret/network-shaped"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_changed_bytes_under_same_revision_refused(self):
        a = opp("A", 1, {"proposal": 1}, source=SHA_A)
        b = deepcopy(a)
        b["source_sha256"] = SHA_C
        data = source([a, b])
        with self.assertRaisesRegex(PortfolioError, "changed bytes under A@1"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_bad_policy_digest_rejected(self):
        data = source([opp("A", 1, {"proposal": 1})])
        data["policy"]["available_extra"] = 1
        with self.assertRaisesRegex(PortfolioError, "keys mismatch"):
            compile_portfolio(data, evaluated_at=NOW)
        data = source([opp("A", 1, {"proposal": 1})])
        data["policy"]["policy_sha256"] = SHA_A
        with self.assertRaisesRegex(PortfolioError, "does not bind"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_outside_policy_horizon_rejected(self):
        data = source([opp("A", 1, {"proposal": 1})])
        with self.assertRaisesRegex(PortfolioError, "outside owner planning horizon"):
            compile_portfolio(data, evaluated_at="2026-09-21T00:00:00Z")

    def test_exact_solver_bound_fails_closed(self):
        pools = [{"pool_id": "p", "available_units": 100, "reserve_units": 0}]
        data = source([opp(f"O{i:02d}", 1, {"p": 1}) for i in range(21)], pools)
        with self.assertRaisesRegex(PortfolioError, "exact solver bound exceeded"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_verifier_rejects_result_markdown_and_receipt_tamper(self):
        compiled = compile_portfolio(source([opp("A", 1, {"proposal": 1})]), evaluated_at=NOW)
        self.assertTrue(verify_compiled(compiled.result_bytes, compiled.markdown_bytes, compiled.receipt_bytes)["verified"])
        for which in ("result", "markdown", "receipt"):
            result, md, receipt = compiled.result_bytes, compiled.markdown_bytes, compiled.receipt_bytes
            if which == "result":
                result = result.replace(b'"selected_priority_units":1', b'"selected_priority_units":2')
            elif which == "markdown":
                md += b"tamper\n"
            else:
                receipt = receipt.replace(b'"selected_priority_units":1', b'"selected_priority_units":2')
            with self.assertRaises(PortfolioError):
                verify_compiled(result, md, receipt)

    def test_create_exclusive_output_and_final_symlink_refusal(self):
        data = source([opp("A", 1, {"proposal": 1})])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "out"
            compiled = write_compiled(data, dest, evaluated_at=NOW)
            self.assertEqual((dest / "portfolio.json").read_bytes(), compiled.result_bytes)
            with self.assertRaisesRegex(PortfolioError, "already exists"):
                write_compiled(data, dest, evaluated_at=NOW)
            link = root / "dangling"
            os.symlink(root / "missing", link)
            with self.assertRaisesRegex(PortfolioError, "symlink"):
                write_compiled(data, link, evaluated_at=NOW)

    def test_policy_reserve_cannot_exceed_available(self):
        pools = [{"pool_id": "p", "available_units": 1, "reserve_units": 2}]
        # make_policy itself binds the invalid policy so validation reaches the arithmetic fence.
        data = source([opp("A", 1, {"p": 1})], pools)
        with self.assertRaisesRegex(PortfolioError, "reserve_units exceeds"):
            compile_portfolio(data, evaluated_at=NOW)

    def test_result_authority_is_all_false(self):
        result = compile_portfolio(source([opp("A", 1, {"proposal": 1})]), evaluated_at=NOW).result
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
