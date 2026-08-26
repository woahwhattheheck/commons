#!/usr/bin/env python3
"""Focused tests for the synthetic GGUF v3 rollback fixture."""
from __future__ import annotations

import contextlib
from datetime import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "gguf_rollback_fixture.py"
SCHEMA = ROOT / "revenue" / "payment_ready" / "gguf_rollback_fixture.schema.json"
PROOF = (
    ROOT
    / "revenue"
    / "production_survival"
    / "proofs"
    / "commons-self-action-recovery-27427a8c-20260826-01.json"
)
FORBIDDEN_LABELS = (
    "AT1",
    "AT2",
    "AT3",
    "AT4",
    "AT5",
    "AT6",
    "DELIVERED",
    "CUSTOMER_READY",
    "RECEIPT_EMITTED",
)


class SchemaError(AssertionError):
    """A value does not satisfy the local JSON Schema subset."""


class MiniSchemaValidator:
    """Draft 2020-12 subset used by this fixture schema."""

    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, value) -> None:
        self._validate(value, self.schema, self.schema, "$")

    def _resolve(self, ref: str, root):
        if not ref.startswith("#/"):
            raise SchemaError("unsupported ref %r" % ref)
        node = root
        for raw in ref[2:].split("/"):
            key = raw.replace("~1", "/").replace("~0", "~")
            node = node[key]
        return node

    def _matches(self, value, schema, root, at):
        try:
            self._validate(value, schema, root, at)
            return True
        except SchemaError:
            return False

    @staticmethod
    def _type_ok(value, wanted):
        if wanted == "object":
            return isinstance(value, dict)
        if wanted == "array":
            return isinstance(value, list)
        if wanted == "string":
            return isinstance(value, str)
        if wanted == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if wanted == "boolean":
            return isinstance(value, bool)
        raise SchemaError("validator does not implement type %r" % wanted)

    def _validate(self, value, schema, root, at: str) -> None:
        if "$ref" in schema:
            self._validate(value, self._resolve(schema["$ref"], root), root, at)
            return
        if "const" in schema and value != schema["const"]:
            raise SchemaError("%s is not const %r" % (at, schema["const"]))
        if "enum" in schema and value not in schema["enum"]:
            raise SchemaError("%s is not in enum" % at)
        wanted = schema.get("type")
        if wanted is not None:
            choices = wanted if isinstance(wanted, list) else [wanted]
            if not any(self._type_ok(value, item) for item in choices):
                raise SchemaError("%s has wrong type; need %r" % (at, wanted))
        if isinstance(value, str):
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                raise SchemaError("%s does not match %s" % (at, schema["pattern"]))
            if schema.get("format") == "date-time":
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise SchemaError("%s date-time has no timezone" % at)
        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    raise SchemaError("%s missing %s" % (at, key))
            props = schema.get("properties", {})
            extra = sorted(set(value) - set(props))
            if schema.get("additionalProperties", True) is False and extra:
                raise SchemaError("%s has extra keys %r" % (at, extra))
            for key, child in props.items():
                if key in value:
                    self._validate(value[key], child, root, "%s.%s" % (at, key))
        if isinstance(value, list) and "items" in schema:
            for index, item in enumerate(value):
                self._validate(item, schema["items"], root, "%s[%d]" % (at, index))


def load_fixture():
    spec = importlib.util.spec_from_file_location("gguf_rollback_fixture", HOST)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["gguf_rollback_fixture"] = module
    spec.loader.exec_module(module)
    return module


fixture = load_fixture()
SCHEMA_DOC = json.loads(SCHEMA.read_text(encoding="utf-8"))
VALIDATOR = MiniSchemaValidator(SCHEMA_DOC)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GgufRollbackFixtureTests(unittest.TestCase):
    def test_two_independent_runs_emit_the_same_public_receipt(self):
        first = fixture.run_fixture()
        second = fixture.run_fixture()
        self.assertEqual(first, second)
        self.assertEqual(fixture.canonical_json(first), fixture.canonical_json(second))
        runs = []
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, str(HOST)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            runs.append(result.stdout)
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(json.loads(runs[0]), first)
        VALIDATOR.validate(first)

    def test_parse_locates_tensor_from_metadata_not_a_constant_offset(self):
        canonical = fixture.build_synthetic_gguf()
        shifted = fixture.build_synthetic_gguf(extra_kv=(("fixture.pad", "x" * 64),))
        aligned = fixture.build_synthetic_gguf(alignment=64)
        parsed_a, tensor_a, start_a = fixture.inspect_fixture(canonical)
        parsed_b, tensor_b, start_b = fixture.inspect_fixture(shifted)
        parsed_c, tensor_c, start_c = fixture.inspect_fixture(aligned)
        self.assertNotEqual(start_a, start_b)
        self.assertNotEqual(start_a, start_c)
        self.assertNotEqual(parsed_a.data_section_start, parsed_b.data_section_start)
        self.assertEqual(start_a, parsed_a.data_section_start + tensor_a.relative_offset)
        self.assertEqual(start_b, parsed_b.data_section_start + tensor_b.relative_offset)
        self.assertEqual(start_c, parsed_c.data_section_start + tensor_c.relative_offset)
        self.assertEqual(canonical[start_a : start_a + 32], fixture.F32_ONES)
        self.assertEqual(shifted[start_b : start_b + 32], fixture.F32_ONES)
        self.assertEqual(aligned[start_c : start_c + 32], fixture.F32_ONES)
        source = HOST.read_text(encoding="utf-8")
        self.assertIn("data_section_start + tensor.relative_offset", source)
        self.assertIsNone(re.search(r"payload_(?:abs|offset|start)\s*=\s*\d+", source))
        self.assertNotIn("PAYLOAD_OFFSET", source)

    def test_original_differs_from_zeroed_and_restored_equals_original(self):
        blob = fixture.build_synthetic_gguf()
        parsed, tensor, start = fixture.inspect_fixture(blob)
        zeroed = bytearray(blob)
        zeroed[start : start + tensor.payload_bytes] = b"\x00" * tensor.payload_bytes
        restored = bytearray(zeroed)
        restored[start : start + tensor.payload_bytes] = blob[start : start + tensor.payload_bytes]
        original_sha = sha256_hex(blob)
        zeroed_sha = sha256_hex(zeroed)
        restored_sha = sha256_hex(restored)
        self.assertNotEqual(original_sha, zeroed_sha)
        self.assertEqual(original_sha, restored_sha)
        receipt = fixture.rollback_from_bytes(blob)
        self.assertEqual(receipt["fixture_original"]["sha256"], original_sha)
        self.assertEqual(receipt["fixture_zeroed"]["sha256"], zeroed_sha)
        self.assertTrue(receipt["fixture_zeroed"]["differs_from_original"])
        self.assertEqual(receipt["fixture_restored"]["sha256"], original_sha)
        self.assertTrue(receipt["fixture_restored"]["equals_original"])
        self.assertEqual(receipt["label"], fixture.PASS_LABEL)

    def test_forced_one_byte_restore_corruption_fails_without_pass_label(self):
        blob = fixture.build_synthetic_gguf()
        with self.assertRaises(fixture.FixtureError) as ctx:
            fixture.rollback_from_bytes(blob, corrupt_restore=True)
        self.assertIn("restored hash differs from original", str(ctx.exception))
        self.assertNotIn(fixture.PASS_LABEL, str(ctx.exception))

        def boom(*_args, **_kwargs):
            raise fixture.FixtureError("restored hash differs from original")

        original = fixture.run_fixture
        fixture.run_fixture = boom
        try:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = fixture.main()
            self.assertEqual(code, 1)
            self.assertNotIn(fixture.PASS_LABEL, stdout.getvalue())
            self.assertNotIn(fixture.PASS_LABEL, stderr.getvalue())
            self.assertNotIn(fixture.PASS_LABEL, stdout.getvalue() + stderr.getvalue())
        finally:
            fixture.run_fixture = original

    def test_bad_magic_unsupported_version_truncation_missing_tensor_invalid_architecture_fail_closed(self):
        good = fixture.build_synthetic_gguf()
        parsed, tensor, start = fixture.inspect_fixture(good)
        nonzero_padding = bytearray(good)
        nonzero_padding[parsed.tensor_info_end] = 1
        alignment_type = bytearray(good)
        alignment_key_at = good.index(b"general.alignment")
        alignment_type_at = alignment_key_at + len(b"general.alignment")
        alignment_type[alignment_type_at : alignment_type_at + 4] = struct.pack(
            "<I", fixture.GGUF_TYPE_INT32
        )
        cases = {
            "bad magic": fixture.build_synthetic_gguf(magic=b"XXXX"),
            "unsupported version": fixture.build_synthetic_gguf(version=2),
            "truncated header": good[:23],
            "truncated metadata": good[: parsed.tensor_info_end - 1],
            "truncated payload": good[: start + tensor.payload_bytes - 1],
            "trailing fixture bytes": good + b"\x00",
            "missing tensor": fixture.build_synthetic_gguf(include_tensor=False),
            "invalid architecture grammar": fixture.build_synthetic_gguf(architecture="Llama"),
            "invalid architecture value": fixture.build_synthetic_gguf(architecture="llama"),
            "invalid fixture name": fixture.build_synthetic_gguf(name="other-fixture"),
            "misaligned tensor offset": fixture.build_synthetic_gguf(relative_offset=1),
            "duplicate metadata key": fixture.build_synthetic_gguf(
                extra_kv=(("general.name", fixture.FIXTURE_NAME),)
            ),
            "empty metadata key": fixture.build_synthetic_gguf(extra_kv=(("", "x"),)),
            "invalid metadata key grammar": fixture.build_synthetic_gguf(
                extra_kv=(("Bad Key", "x"),)
            ),
            "duplicate tensor name": fixture.build_synthetic_gguf(
                extra_tensor_names=(fixture.TENSOR_NAME,)
            ),
            "nonzero tensor-data padding": bytes(nonzero_padding),
            "wrong alignment metadata type": bytes(alignment_type),
        }
        with self.assertRaises(fixture.FixtureError):
            fixture.build_synthetic_gguf(alignment=4)
        with self.assertRaises(fixture.FixtureError):
            fixture.build_synthetic_gguf(alignment=24)
        for label, blob in cases.items():
            with self.subTest(label):
                with self.assertRaises(fixture.FixtureError):
                    fixture.rollback_from_bytes(blob)
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    try:
                        receipt = fixture.rollback_from_bytes(blob)
                    except fixture.FixtureError as exc:
                        stderr.write(str(exc))
                        receipt = None
                self.assertIsNone(receipt)
                combined = stdout.getvalue() + stderr.getvalue()
                self.assertNotIn(fixture.PASS_LABEL, combined)

    def test_arbitrary_json_and_generic_rollback_receipt_are_not_gguf_evidence(self):
        arbitrary = {"hello": "world", "schema_version": "gguf-rollback-fixture/v1"}
        with self.assertRaises(fixture.FixtureError):
            fixture.parse_gguf_v3(json.dumps(arbitrary).encode("utf-8"))
        with self.assertRaises(SchemaError):
            VALIDATOR.validate(arbitrary)
        proof = json.loads(PROOF.read_text(encoding="utf-8"))
        self.assertEqual(proof["schema_version"], "production-survival-proof/v1")
        with self.assertRaises(fixture.FixtureError):
            fixture.parse_gguf_v3(json.dumps(proof, sort_keys=True).encode("utf-8"))
        with self.assertRaises(SchemaError):
            VALIDATOR.validate(proof)

    def test_no_input_path_network_surface_and_no_checked_in_gguf(self):
        source = HOST.read_text(encoding="utf-8")
        schema_text = SCHEMA.read_text(encoding="utf-8")
        test_source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("--input", source)
        self.assertNotIn("argparse", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("socket", source)
        self.assertNotIn("http.client", source)
        self.assertNotIn("allowlist", source)
        self.assertNotIn("denylist", source)
        self.assertNotIn("path_allowed", source)
        self.assertNotIn("allowed_path", source)
        self.assertNotIn("validate_path", source)
        self.assertIn("TemporaryDirectory", source)
        self.assertNotIn("sys.argv", source)
        self.assertEqual(HOST.suffix, ".py")
        self.assertEqual(SCHEMA.suffix, ".json")
        self.assertEqual(Path(__file__).suffix, ".py")
        self.assertFalse((ROOT / "commons-gguf-rollback-fixture.gguf").exists())
        self.assertFalse((ROOT / "host" / "commons-gguf-rollback-fixture.gguf").exists())
        tracked = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "*.gguf"],
            text=True,
        )
        self.assertEqual(tracked.strip(), "")
        for text in (source, schema_text):
            self.assertIsNone(re.search(r"\bAT[1-6]\b", text))
            for label in ("DELIVERED", "CUSTOMER_READY", "RECEIPT_EMITTED"):
                self.assertNotIn(label, text)
        self.assertIn("AT1", test_source)

    def test_emitted_truth_stays_noncommercial_and_avoids_customer_labels(self):
        receipt = fixture.run_fixture()
        VALIDATOR.validate(receipt)
        self.assertFalse(receipt["buyer"])
        self.assertFalse(receipt["acceptance"])
        self.assertFalse(receipt["delivery"])
        self.assertEqual(receipt["cash_usd"], 0)
        self.assertFalse(receipt["cash_claimed"])
        self.assertFalse(receipt["program_submission"])
        self.assertEqual(receipt["eligibility"], "NOT_CLAIMED")
        self.assertEqual(receipt["demand"], "UNKNOWN")
        self.assertEqual(receipt["titan"], "NOT_WRITTEN")
        self.assertFalse(receipt["binaries_published"])
        self.assertFalse(receipt["network_used"])
        self.assertEqual(receipt["fixture"], "SYNTHETIC")
        self.assertFalse(receipt["nonclaims"]["customer_gguf"])
        self.assertFalse(receipt["nonclaims"]["customer_delivery"])
        self.assertFalse(receipt["nonclaims"]["titan_write"])
        self.assertFalse(receipt["nonclaims"]["buyer_signal"])
        self.assertFalse(receipt["nonclaims"]["program_submission"])
        self.assertFalse(receipt["nonclaims"]["award"])
        self.assertFalse(receipt["nonclaims"]["cash"])
        dumped = fixture.canonical_json(receipt)
        self.assertIsNone(re.search(r"\bAT[1-6]\b", dumped))
        for label in ("DELIVERED", "CUSTOMER_READY", "RECEIPT_EMITTED"):
            self.assertNotIn(label, dumped)
        self.assertNotIn("production-survival-proof/v1", dumped)
        self.assertEqual(receipt["schema_version"], "gguf-rollback-fixture/v1")
        self.assertEqual(receipt["kind"], "SYNTHETIC_GGUF_ROLLBACK_FIXTURE")


if __name__ == "__main__":
    unittest.main()
