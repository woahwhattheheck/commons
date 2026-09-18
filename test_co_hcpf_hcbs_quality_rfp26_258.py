import builtins
import copy
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone

from opportunities.co_hcpf_hcbs_quality_rfp26_258 import qualification as q

A = "a" * 64
B = "b" * 64
C = "c" * 64


def source(**overrides):
    row = {
        "id": "vss-20260909-amended-2",
        "authority": "BUYER_SOURCE_SET",
        "sha256": A,
        "effective_at": "2026-09-09T12:00:00Z",
        "solicitation_id": "RFP-UHAA-2026000258-2",
        "inquiry_deadline": "2026-09-17T17:00:00Z",
        "proposal_deadline": "2026-10-13T21:00:00Z",
        "submission_route": "HCPF_BOX_GENERATION_20260909",
        "initial_cap_usd": 400000,
        "extension_cap_usd": 340000,
        "pricing_generation": "APPENDIX_E_20260909",
    }
    row.update(overrides)
    return row


def primes(org="vital-research"):
    return [
        {"id": f"{org}-{gate}", "org_id": org, "gate": gate, "sha256": B}
        for gate in q.PRIME_GATES
    ]


def work():
    return [
        {"id": f"tj-{gate}", "gate": gate, "sha256": C}
        for gate in q.WORKSHARE_GATES
    ]


def packet(sources=None, prime=None, workshare=None):
    return {
        "schema": q.PACKET_SCHEMA,
        "pursuit_id": q.PURSUIT_ID,
        "buyer_source_sets": [] if sources is None else sources,
        "prime_evidence": [] if prime is None else prime,
        "workshare_evidence": [] if workshare is None else workshare,
    }


def engine(now=None, sources=None, prime=None, workshare=None):
    now = now or datetime(2026, 9, 18, tzinfo=timezone.utc)
    return q._build_engine(
        {} if sources is None else sources,
        {} if prime is None else prime,
        {} if workshare is None else workshare,
        lambda: now,
    )


class Hcbs258Tests(unittest.TestCase):
    def test_01_production_is_research_hold_and_hard_false(self):
        out = q.compile_packet(packet())
        self.assertEqual(out["state"], "HOLD_MISSING_BUYER_SOURCE")
        self.assertEqual(out["commercial_posture"], "RESEARCH_HOLD")
        self.assertIsNone(out["official_source_set"])
        self.assertTrue(all(v is False for v in out["authority"].values()))

    def test_02_complete_source_owned_fixture_is_owner_review_only(self):
        s, p, w = source(), primes(), work()
        compile_fixture = engine(
            sources={s["id"]: s},
            prime={row["id"]: row for row in p},
            workshare={row["id"]: row for row in w},
        )
        out = compile_fixture(packet([s], p, w))
        self.assertEqual(out["state"], "PARTNER_PACKET_READY_FOR_OWNER_REVIEW")
        self.assertEqual(out["qualified_prime_org_ids"], ["vital-research"])
        self.assertTrue(all(v is False for v in out["authority"].values()))

    def test_03_prime_gates_cannot_mix_across_orgs(self):
        s = source()
        rows = []
        for i, row in enumerate(primes("seed")):
            row = dict(row)
            row["id"] = f"e-{i}"
            row["org_id"] = "org-a" if i % 2 == 0 else "org-b"
            rows.append(row)
        w = work()
        compile_fixture = engine(
            sources={s["id"]: s},
            prime={row["id"]: row for row in rows},
            workshare={row["id"]: row for row in w},
        )
        out = compile_fixture(packet([s], rows, w))
        self.assertEqual(out["state"], "HOLD_NO_QUALIFIED_PRIME")
        self.assertEqual(out["qualified_prime_org_ids"], [])

    def test_04_same_sha_relabel_is_not_buyer_authority(self):
        s = source()
        compile_fixture = engine(sources={s["id"]: s})
        cases = (
            ("proposal_deadline", "2026-11-13T21:00:00Z"),
            ("submission_route", "VSS"),
            ("pricing_generation", "OLD_PRICE"),
            ("solicitation_id", "RFP-UHAA-2026000258"),
            ("initial_cap_usd", 999999),
        )
        for key, value in cases:
            with self.subTest(key=key):
                out = compile_fixture(packet([source(**{key: value})]))
                self.assertEqual(out["state"], "HOLD_MISSING_BUYER_SOURCE")

    def test_05_equal_effective_buyer_generations_fail_ambiguous(self):
        left = source(id="left", sha256=A)
        right = source(id="right", sha256=B)
        compile_fixture = engine(sources={"left": left, "right": right})
        with self.assertRaisesRegex(q.QualificationError, "ambiguous current official buyer generation"):
            compile_fixture(packet([left, right]))

    def test_06_deadline_uses_trusted_clock(self):
        s = source()
        compile_fixture = engine(
            now=datetime(2026, 10, 13, 21, 0, tzinfo=timezone.utc),
            sources={s["id"]: s},
        )
        self.assertEqual(compile_fixture(packet([s]))["state"], "HOLD_DEADLINE")

    def test_07_incomplete_workshare_holds(self):
        s, p, w = source(), primes(), work()[:-1]
        compile_fixture = engine(
            sources={s["id"]: s},
            prime={row["id"]: row for row in p},
            workshare={row["id"]: row for row in w},
        )
        out = compile_fixture(packet([s], p, w))
        self.assertEqual(out["state"], "HOLD_WORKSHARE_EVIDENCE")
        self.assertEqual(out["missing_workshare_gates"], [q.WORKSHARE_GATES[-1]])

    def test_08_untrusted_prime_labels_do_not_qualify(self):
        s, p = source(), primes()
        out = engine(sources={s["id"]: s})(packet([s], p, []))
        self.assertEqual(out["state"], "HOLD_NO_QUALIFIED_PRIME")

    def test_09_direct_input_is_detached_before_semantics(self):
        s, p, w = source(), primes(), work()
        compile_fixture = engine(
            sources={s["id"]: s},
            prime={row["id"]: row for row in p},
            workshare={row["id"]: row for row in w},
        )
        original = packet([copy.deepcopy(s)], copy.deepcopy(p), copy.deepcopy(w))
        out = compile_fixture(original)
        original["buyer_source_sets"][0]["submission_route"] = "ATTACKER_ROUTE"
        original["prime_evidence"].clear()
        self.assertEqual(out["official_source_set"]["submission_route"], "HCPF_BOX_GENERATION_20260909")
        self.assertEqual(out["state"], "PARTNER_PACKET_READY_FOR_OWNER_REVIEW")

    def test_10_shared_container_rejected(self):
        shared = []
        p = packet()
        p["buyer_source_sets"] = shared
        p["prime_evidence"] = shared
        with self.assertRaisesRegex(q.QualificationError, "shared/cyclic"):
            q.compile_packet(p)

    def test_11_strict_raw_rejects_duplicate_float_giant_int(self):
        for raw in (
            '{"schema":"x","schema":"y"}',
            '{"x":1.5}',
            '{"x":99999999999999999}',
        ):
            with self.subTest(raw=raw), self.assertRaises(q.QualificationError):
                q.compile_json(raw)

    def test_12_bounds_reject_huge_string_and_depth(self):
        p = packet()
        p["junk"] = "x" * (q.MAX_JSON_BYTES + 1)
        with self.assertRaises(q.QualificationError):
            q.compile_packet(p)
        deep = packet()
        cursor = []
        deep["buyer_source_sets"] = cursor
        for _ in range(q.MAX_JSON_DEPTH + 2):
            child = []
            cursor.append(child)
            cursor = child
        with self.assertRaises(q.QualificationError):
            q.compile_packet(deep)

    def test_13_receipt_binds_packet(self):
        a = q.compile_packet(packet())
        b = q.compile_packet(packet(workshare=[
            {"id": "x", "gate": "sample_validation_automation", "sha256": A}
        ]))
        self.assertNotEqual(a["input_digest_sha256"], b["input_digest_sha256"])
        self.assertNotEqual(a["receipt_sha256"], b["receipt_sha256"])

    def test_14_public_api_survives_ordinary_global_rebind(self):
        p = packet()
        baseline = q.compile_packet(p)
        saved = {
            "_PRODUCTION_ENGINE": q._PRODUCTION_ENGINE,
            "loads_strict": q.loads_strict,
            "_snapshot_direct": q._snapshot_direct,
            "canonical_bytes": q.canonical_bytes,
            "PACKET_SCHEMA": q.PACKET_SCHEMA,
            "PURSUIT_ID": q.PURSUIT_ID,
            "MAX_JSON_BYTES": q.MAX_JSON_BYTES,
            "datetime": q.datetime,
        }
        try:
            q._PRODUCTION_ENGINE = lambda _: {"state": "ATTACK"}
            q.loads_strict = lambda _: p
            q._snapshot_direct = lambda x: x
            q.canonical_bytes = lambda _: b"attack"
            q.PACKET_SCHEMA = "attack"
            q.PURSUIT_ID = "attack"
            q.MAX_JSON_BYTES = 10**9
            q.datetime = object
            for out in (q.compile_packet(p), q.compile_json(json.dumps(p))):
                for key in baseline:
                    if key not in {"evaluated_at", "receipt_sha256"}:
                        self.assertEqual(out[key], baseline[key], key)
                self.assertTrue(all(v is False for v in out["authority"].values()))
        finally:
            for name, value in saved.items():
                setattr(q, name, value)

    def test_15_builtin_shadowing_cannot_bypass_bounds_or_mint_prime(self):
        s, w = source(), work()
        compile_fixture = engine(
            sources={s["id"]: s},
            prime={},
            workshare={row["id"]: row for row in w},
        )
        baseline = compile_fixture(packet([s], [], w))
        self.assertEqual(baseline["state"], "HOLD_NO_QUALIFIED_PRIME")
        self.assertEqual(baseline["qualified_prime_org_ids"], [])

        names = ("len", "set", "sorted", "type", "isinstance", "dict", "abs", "enumerate", "frozenset")
        sentinel = object()
        saved = {name: q.__dict__.get(name, sentinel) for name in names}
        try:
            q.len = lambda _: 0
            oversized = packet()
            oversized["pursuit_id"] = "x" * (q.MAX_JSON_BYTES + 1)
            raw = json.dumps(oversized, separators=(",", ":"))
            with self.assertRaisesRegex(q.QualificationError, "JSON input exceeds byte limit"):
                q.compile_json(raw)

            q.set = lambda *_: builtins.set(q.PRIME_GATES)
            q.sorted = lambda *_: ["synthetic-prime"]
            q.type = lambda *_: str
            q.isinstance = lambda *_: True
            q.dict = lambda *_args, **_kwargs: {"state": "ATTACK"}
            q.abs = lambda *_: 0
            q.enumerate = lambda *_: ()
            q.frozenset = lambda *_: builtins.frozenset()
            out = compile_fixture(packet([s], [], w))
            self.assertEqual(out["state"], "HOLD_NO_QUALIFIED_PRIME")
            self.assertEqual(out["qualified_prime_org_ids"], [])
            self.assertTrue(all(v is False for v in out["authority"].values()))
        finally:
            for name, value in saved.items():
                if value is sentinel:
                    q.__dict__.pop(name, None)
                else:
                    setattr(q, name, value)

    def test_16_json_class_rebind_does_not_change_captured_codec(self):
        left = packet()
        right = packet(workshare=[
            {"id": "x", "gate": "sample_validation_automation", "sha256": A}
        ])
        raw_left = json.dumps(left, separators=(",", ":"))
        left_before = q.compile_packet(left)
        right_before = q.compile_packet(right)
        raw_before = q.compile_json(raw_left)
        self.assertNotEqual(
            left_before["input_digest_sha256"],
            right_before["input_digest_sha256"],
        )

        encoder_before = q.json.JSONEncoder
        decoder_before = q.json.JSONDecoder

        class DisabledEncoder:
            def __init__(self, *args, **kwargs):
                raise AssertionError("live JSONEncoder must not be used")

        class DisabledDecoder:
            def __init__(self, *args, **kwargs):
                raise AssertionError("live JSONDecoder must not be used")

        try:
            q.json.JSONEncoder = DisabledEncoder
            q.json.JSONDecoder = DisabledDecoder
            left_after = q.compile_packet(left)
            right_after = q.compile_packet(right)
            raw_after = q.compile_json(raw_left)
        finally:
            q.json.JSONEncoder = encoder_before
            q.json.JSONDecoder = decoder_before

        self.assertEqual(
            left_after["input_digest_sha256"],
            left_before["input_digest_sha256"],
        )
        self.assertEqual(
            right_after["input_digest_sha256"],
            right_before["input_digest_sha256"],
        )
        self.assertNotEqual(
            left_after["input_digest_sha256"],
            right_after["input_digest_sha256"],
        )
        self.assertEqual(
            raw_after["input_digest_sha256"],
            raw_before["input_digest_sha256"],
        )
        self.assertEqual(raw_after["state"], raw_before["state"])

    def test_17_public_api_rejects_dependency_kwargs(self):
        with self.assertRaises(TypeError):
            q.compile_packet(packet(), _engine=lambda _: {})
        with self.assertRaises(TypeError):
            q.compile_json("{}", _loader=lambda _: packet())

    def test_18_bool_is_not_price(self):
        bad = source(initial_cap_usd=True)
        with self.assertRaises(q.QualificationError):
            q._build_engine({bad["id"]: bad}, {}, {}, lambda: datetime.now(timezone.utc))

    def test_19_real_python_O(self):
        if not sys.flags.optimize:
            proc = subprocess.run(
                [sys.executable, "-O", "-m", "unittest", "-v", __file__],
                cwd=".",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
