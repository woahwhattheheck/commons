from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import revenue.pursuit_portfolio.core_v2 as core
from revenue.pursuit_portfolio.core import (
    AUTHORITY_SCHEMA,
    INPUT_SCHEMA,
    POLICY_SCHEMA,
    PortfolioError,
    compile_portfolio,
    load_json_bytes,
    load_regular_json,
    read_compiled_directory,
    upstream_authority_sha256,
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


def opp(oid, priority, effort, *, deadline="2026-09-16T14:00:00Z", buffer=60, revision=1, source=SHA_A, receipt=SHA_B):
    return {
        "opportunity_id": oid,
        "revision": revision,
        "source_sha256": source,
        "upstream_receipt_sha256": receipt,
        "evidence_ref": f"evidence:{oid}",
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


def authority_rows(opportunities, *, states=None, captured="2026-09-13T13:00:00Z"):
    states = states or {}
    rows = []
    for item in opportunities:
        rows.append({
            "opportunity_id": item["opportunity_id"],
            "revision": item["revision"],
            "source_sha256": item["source_sha256"],
            "upstream_receipt_sha256": item["upstream_receipt_sha256"],
            "upstream_state": states.get(item["opportunity_id"], "READY"),
            "evidence_captured_at": captured,
        })
    return {"schema": AUTHORITY_SCHEMA, "revision": 1, "generated_at": captured, "rows": rows}


def compile_ok(data, *, states=None, captured="2026-09-13T13:00:00Z", evaluated_at=NOW):
    authority = authority_rows(data["opportunities"], states=states, captured=captured)
    trusted = upstream_authority_sha256(authority)
    return compile_portfolio(data, upstream_authority=authority, trusted_upstream_authority_sha256=trusted, evaluated_at=evaluated_at)


class PortfolioTests(unittest.TestCase):
    def test_exact_optimizer_beats_naive_priority_greedy(self):
        pools = [{"pool_id": "p", "available_units": 6, "reserve_units": 0}, {"pool_id": "e", "available_units": 6, "reserve_units": 0}]
        data = source([opp("A", 9, {"p": 6, "e": 6}), opp("B", 6, {"p": 6}), opp("C", 6, {"e": 6})], pools)
        compiled = compile_ok(data)
        self.assertEqual(compiled.result["selected_opportunity_ids"], ["B", "C"])
        self.assertEqual(compiled.result["selected_priority_units"], 12)

    def test_objective_tiebreakers(self):
        pools = [{"pool_id": "p", "available_units": 2, "reserve_units": 0}]
        data = source([opp("A", 10, {"p": 2}), opp("B", 5, {"p": 1}), opp("C", 5, {"p": 1})], pools)
        self.assertEqual(compile_ok(data).result["selected_opportunity_ids"], ["B", "C"])
        lower = source([opp("A", 10, {"p": 2}), opp("B", 10, {"p": 1})], pools)
        self.assertEqual(compile_ok(lower).result["selected_opportunity_ids"], ["B"])
        lex = source([opp("B", 10, {"p": 1}), opp("A", 10, {"p": 1})], [{"pool_id": "p", "available_units": 1, "reserve_units": 0}])
        self.assertEqual(compile_ok(lex).result["selected_opportunity_ids"], ["A"])

    def test_upstream_state_comes_only_from_authority(self):
        rows = [opp("ready", 4, {"proposal": 1}), opp("curable", 3, {"proposal": 1}), opp("hold", 999, {"proposal": 1}), opp("terminal", 999, {"proposal": 1})]
        data = source(rows)
        compiled = compile_ok(data, states={"curable": "CURABLE", "hold": "HOLD", "terminal": "TERMINAL"})
        result = {x["opportunity_id"]: x for x in compiled.result["opportunities"]}
        self.assertEqual(result["ready"]["allocation_state"], "ALLOCATED_READY")
        self.assertEqual(result["curable"]["allocation_state"], "CURABLE_RECOVERY_ALLOCATED")
        self.assertEqual(result["hold"]["allocation_state"], "HOLD_UPSTREAM")
        self.assertEqual(result["terminal"]["allocation_state"], "TERMINAL")

    def test_caller_minted_ready_fields_are_rejected(self):
        row = opp("forged", 999, {"proposal": 1})
        row["upstream_state"] = "READY"
        row["evidence_captured_at"] = NOW
        data = source([row])
        authority = {"schema": AUTHORITY_SCHEMA, "revision": 1, "generated_at": NOW, "rows": []}
        trusted = upstream_authority_sha256(authority)
        with self.assertRaisesRegex(PortfolioError, "keys mismatch"):
            compile_portfolio(data, upstream_authority=authority, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)

    def test_missing_authority_cannot_allocate(self):
        data = source([opp("A", 999, {"proposal": 1})])
        authority = {"schema": AUTHORITY_SCHEMA, "revision": 1, "generated_at": NOW, "rows": []}
        trusted = upstream_authority_sha256(authority)
        compiled = compile_portfolio(data, upstream_authority=authority, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
        row = compiled.result["opportunities"][0]
        self.assertEqual(row["allocation_state"], "HOLD")
        self.assertEqual(row["reasons"], ["UPSTREAM_AUTHORITY_MISSING"])
        self.assertEqual(compiled.result["selected_opportunity_ids"], [])

    def test_authority_binding_mismatch_cannot_allocate(self):
        data = source([opp("A", 999, {"proposal": 1})])
        authority = authority_rows(data["opportunities"])
        authority["rows"][0]["source_sha256"] = SHA_C
        trusted = upstream_authority_sha256(authority)
        compiled = compile_portfolio(data, upstream_authority=authority, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
        row = compiled.result["opportunities"][0]
        self.assertEqual(row["allocation_state"], "HOLD")
        self.assertEqual(row["reasons"], ["UPSTREAM_AUTHORITY_BINDING_MISMATCH:source_sha256"])

    def test_trusted_authority_digest_is_external_and_required(self):
        data = source([opp("A", 1, {"proposal": 1})])
        authority = authority_rows(data["opportunities"])
        with self.assertRaisesRegex(PortfolioError, "trusted SHA-256 mismatch"):
            compile_portfolio(data, upstream_authority=authority, trusted_upstream_authority_sha256=SHA_C, evaluated_at=NOW)

    def test_deadline_and_evidence_time_gates(self):
        exact = source([opp("A", 1, {"proposal": 1}, deadline="2026-09-13T15:00:00Z", buffer=60)])
        self.assertEqual(compile_ok(exact).result["opportunities"][0]["allocation_state"], "ALLOCATED_READY")
        short = source([opp("A", 1, {"proposal": 1}, deadline="2026-09-13T14:59:59Z", buffer=60)])
        self.assertEqual(compile_ok(short).result["opportunities"][0]["allocation_state"], "DEADLINE_BUFFER_BREACHED")
        stale = source([opp("A", 1, {"proposal": 1})], max_age=3600)
        self.assertEqual(compile_ok(stale, captured="2026-09-13T12:59:59Z").result["opportunities"][0]["reasons"], ["STALE_UPSTREAM_EVIDENCE"])
        future = source([opp("A", 1, {"proposal": 1})])
        self.assertEqual(compile_ok(future, captured="2026-09-13T14:00:01Z").result["opportunities"][0]["reasons"], ["FUTURE_UPSTREAM_EVIDENCE"])

    def test_capacity_reserve_and_counterfactual(self):
        pools = [{"pool_id": "p", "available_units": 10, "reserve_units": 4}]
        data = source([opp("A", 10, {"p": 7}), opp("B", 6, {"p": 6})], pools)
        compiled = compile_ok(data)
        self.assertEqual(compiled.result["selected_opportunity_ids"], ["B"])
        zero = source([opp("A", 1, {"p": 2})], [{"pool_id": "p", "available_units": 3, "reserve_units": 3}])
        row = compile_ok(zero).result["opportunities"][0]
        self.assertEqual(row["individual_fit_counterfactual"], [{"additional_units": 2, "pool_id": "p"}])

    def test_input_order_invariance(self):
        pools = [{"pool_id": "p", "available_units": 2, "reserve_units": 0}]
        rows = [opp("C", 2, {"p": 1}), opp("A", 3, {"p": 1}), opp("B", 1, {"p": 1})]
        left_data = source(rows, pools)
        right_data = source(list(reversed(rows)), list(reversed(pools)))
        left_auth = authority_rows(left_data["opportunities"])
        right_auth = authority_rows(list(reversed(right_data["opportunities"])))
        trusted = upstream_authority_sha256(left_auth)
        self.assertEqual(trusted, upstream_authority_sha256(right_auth))
        left = compile_portfolio(left_data, upstream_authority=left_auth, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
        right = compile_portfolio(right_data, upstream_authority=right_auth, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
        self.assertEqual(left.result_bytes, right.result_bytes)

    def test_validation_fences(self):
        with self.assertRaisesRegex(PortfolioError, "duplicate JSON key"):
            load_json_bytes(b'{"schema":"x","schema":"y"}')
        with self.assertRaisesRegex(PortfolioError, "floating-point"):
            load_json_bytes(b'{"x":1.5}')
        data = source([opp("A", 1, {"proposal": 1})])
        data["opportunities"][0]["priority_units"] = True
        with self.assertRaisesRegex(PortfolioError, "bool forbidden"):
            compile_ok(data)
        data = source([opp("A", 1, {"proposal": 1})])
        data["opportunities"][0]["evidence_ref"] = "https://buyer.example/evidence"
        with self.assertRaisesRegex(PortfolioError, "PII/secret/network-shaped"):
            compile_ok(data)

    def test_exact_solver_bound_fails_closed(self):
        pools = [{"pool_id": "p", "available_units": 100, "reserve_units": 0}]
        data = source([opp(f"O{i:02d}", 1, {"p": 1}) for i in range(21)], pools)
        with self.assertRaisesRegex(PortfolioError, "exact solver bound exceeded"):
            compile_ok(data)

    def test_verifier_requires_same_external_authority_anchor(self):
        data = source([opp("A", 1, {"proposal": 1})])
        auth = authority_rows(data["opportunities"])
        trusted = upstream_authority_sha256(auth)
        compiled = compile_portfolio(data, upstream_authority=auth, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
        self.assertTrue(verify_compiled(compiled.result_bytes, compiled.markdown_bytes, compiled.receipt_bytes, trusted_upstream_authority_sha256=trusted)["verified"])
        with self.assertRaisesRegex(PortfolioError, "trusted SHA-256 mismatch"):
            verify_compiled(compiled.result_bytes, compiled.markdown_bytes, compiled.receipt_bytes, trusted_upstream_authority_sha256=SHA_C)

    def test_regular_file_read_is_single_descriptor_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            original = b'{"value":"original"}'
            replacement = b'{"value":"replacement"}'
            path.write_bytes(original)
            real_fstat = os.fstat
            calls = {"count": 0}

            def replacing_fstat(fd):
                info = real_fstat(fd)
                calls["count"] += 1
                if calls["count"] == 1:
                    moved = path.with_suffix(".old")
                    path.rename(moved)
                    path.write_bytes(replacement)
                return info

            with mock.patch.object(core.os, "fstat", side_effect=replacing_fstat):
                loaded = load_regular_json(path)
            self.assertEqual(loaded, {"value": "original"})
            self.assertEqual(path.read_bytes(), replacement)

    def test_regular_file_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target.json"
            target.write_text("{}")
            link = root / "link.json"
            os.symlink(target, link)
            with self.assertRaises(PortfolioError):
                load_regular_json(link)

    def test_partial_publication_is_preserved_and_foreign_replacement_not_deleted(self):
        data = source([opp("A", 1, {"proposal": 1})])
        auth = authority_rows(data["opportunities"])
        trusted = upstream_authority_sha256(auth)
        real_write = core._write_exclusive_at
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out"
            calls = {"count": 0}

            def hostile(dir_fd, name, payload):
                calls["count"] += 1
                generation = real_write(dir_fd, name, payload)
                if calls["count"] == 1:
                    os.unlink(name, dir_fd=dir_fd)
                    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
                    os.write(fd, b"FOREIGN")
                    os.close(fd)
                elif calls["count"] == 2:
                    raise OSError("late failure")
                return generation

            with mock.patch.object(core, "_write_exclusive_at", side_effect=hostile):
                with self.assertRaises(PortfolioError):
                    write_compiled(data, dest, upstream_authority=auth, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
            self.assertTrue(dest.is_dir())
            self.assertEqual((dest / "portfolio.json").read_bytes(), b"FOREIGN")
            self.assertTrue((dest / "portfolio.md").exists())

    def test_successful_publication_round_trip(self):
        data = source([opp("A", 1, {"proposal": 1})])
        auth = authority_rows(data["opportunities"])
        trusted = upstream_authority_sha256(auth)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out"
            compiled = write_compiled(data, dest, upstream_authority=auth, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)
            parts = read_compiled_directory(dest)
            self.assertEqual(parts, (compiled.result_bytes, compiled.markdown_bytes, compiled.receipt_bytes))
            self.assertTrue(verify_compiled(*parts, trusted_upstream_authority_sha256=trusted)["verified"])
            with self.assertRaisesRegex(PortfolioError, "already exists"):
                write_compiled(data, dest, upstream_authority=auth, trusted_upstream_authority_sha256=trusted, evaluated_at=NOW)

    def test_result_authority_is_all_false(self):
        result = compile_ok(source([opp("A", 1, {"proposal": 1})])).result
        self.assertTrue(result["authority"])
        self.assertTrue(all(value is False for value in result["authority"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
