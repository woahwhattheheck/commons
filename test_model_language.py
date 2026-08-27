#!/usr/bin/env python3
"""Focused tests for the CML/1 semantic envelope and opaque payload law."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

import model_language as cml


def packet(kind: str = "DELTA") -> dict[str, object]:
    return {
        "v": 1,
        "k": kind,
        "ops": [
            ["K", "capacity", "m-2"],
            ["T", "targeted_suite", "PASS"],
        ],
    }


def metadata(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "speech": "Reserve one slot while a crossing is active.",
        "model_packet": packet(),
    }
    value.update(overrides)
    return value


class PacketTests(unittest.TestCase):
    def test_packet_has_one_canonical_compact_encoding(self) -> None:
        source = '{ "ops" : [["K", "answer", 42]], "v" : 1, "k" : "RESULT" }'
        canonical = cml.canonicalize_model_packet(source)
        self.assertEqual(canonical, '{"k":"RESULT","ops":[["K","answer",42]],"v":1}')
        self.assertEqual(
            cml.validate_model_packet(canonical),
            {"k": "RESULT", "ops": [["K", "answer", 42]], "v": 1},
        )

    def test_validation_detaches_mutable_packet(self) -> None:
        source = packet()
        validated = cml.validate_model_packet(source)
        validated["ops"][0][2] = "changed"  # type: ignore[index]
        self.assertEqual(source["ops"][0][2], "m-2")  # type: ignore[index]

    def test_all_packet_kinds_and_operation_codes_are_accepted(self) -> None:
        for kind in cml.PACKET_KINDS:
            operations = [[code, f"topic_{code}"] for code in sorted(cml.OP_CODES)]
            canonical = cml.canonicalize_model_packet({"v": 1, "k": kind, "ops": operations})
            self.assertEqual(json.loads(canonical)["k"], kind)

    def test_optional_goal_obligations_references_and_confidence_are_compact(self) -> None:
        source = {
            "v": 1,
            "k": "HANDOFF",
            "g": "land CML/1",
            "ops": [],
            "open": ["run integration tests"],
            "refs": ["model_language.schema.json"],
            "conf": 0.95,
        }
        self.assertEqual(cml.validate_model_packet(source), source)
        canonical = cml.canonicalize_model_packet(source)
        self.assertNotIn(": ", canonical)
        self.assertNotIn(", ", canonical)

    def test_invalid_packet_shapes_are_rejected(self) -> None:
        invalid = {
            "not-an-object": "[]",
            "wrong-version": {"v": 2, "k": "STATE", "ops": [["B", "x"]]},
            "boolean-version": {"v": True, "k": "STATE", "ops": [["B", "x"]]},
            "wrong-kind": {"v": 1, "k": "THINK", "ops": [["B", "x"]]},
            "missing-key": {"v": 1, "k": "STATE"},
            "extra-key": {"v": 1, "k": "STATE", "ops": [["B", "x"]], "thought": "x"},
            "bad-op-code": {"v": 1, "k": "STATE", "ops": [["THINK", "x"]]},
            "short-op": {"v": 1, "k": "STATE", "ops": [["B"]]},
            "long-op": {"v": 1, "k": "STATE", "ops": [["B", "x", 1, 2, 3]]},
            "nested-atom": {"v": 1, "k": "STATE", "ops": [["B", "x", {"y": 1}]]},
            "multiline-topic": {"v": 1, "k": "STATE", "ops": [["B", "x\ny"]]},
            "multiline-atom": {"v": 1, "k": "STATE", "ops": [["B", "x", "a\nb"]]},
            "bad-goal": {"v": 1, "k": "STATE", "ops": [], "g": "a\nb"},
            "bad-open": {"v": 1, "k": "STATE", "ops": [], "open": [1]},
            "bad-refs": {"v": 1, "k": "STATE", "ops": [], "refs": ["a\nb"]},
            "bad-confidence": {"v": 1, "k": "STATE", "ops": [], "conf": 1.1},
        }
        for name, value in invalid.items():
            with self.subTest(name=name), self.assertRaises(cml.ModelLanguageError):
                cml.validate_model_packet(value)  # type: ignore[arg-type]

    def test_private_reasoning_topics_are_rejected(self) -> None:
        for topic in (
            "analysis",
            "chain-of-thought",
            "private_reasoning.trace",
            "SCRATCHPAD",
            "hidden reasoning",
            "rationale_step",
            "thoughts",
        ):
            with self.subTest(topic=topic), self.assertRaises(cml.ModelLanguageError):
                cml.validate_model_packet({"v": 1, "k": "STATE", "ops": [["B", topic, "x"]]})

    def test_duplicate_keys_nonfinite_numbers_and_oversize_packets_are_rejected(self) -> None:
        sources = (
            '{"v":1,"v":1,"k":"STATE","ops":[["B","x"]]}',
            '{"v":1,"k":"STATE","ops":[["B","x",NaN]]}',
            '{"v":1,"k":"STATE","ops":[["B","x",Infinity]]}',
        )
        for source in sources:
            with self.subTest(source=source), self.assertRaises(cml.ModelLanguageError):
                cml.validate_model_packet(source)

        too_many = {"v": 1, "k": "STATE", "ops": [["B", f"x{i}"] for i in range(65)]}
        with self.assertRaises(cml.ModelLanguageError):
            cml.validate_model_packet(too_many)
        too_long = {"v": 1, "k": "STATE", "ops": [["B", "x", "z" * 2049]]}
        with self.assertRaises(cml.ModelLanguageError):
            cml.validate_model_packet(too_long)


class EmitterTests(unittest.TestCase):
    def test_emitter_builds_complete_layer_without_mutating_inputs(self) -> None:
        body = "A normal answer.\n"
        source = metadata(extra_context="preserved")
        before = copy.deepcopy(source)
        result, returned_body = cml.canonicalize_emitter_record(source, body)

        self.assertEqual(source, before)
        self.assertIs(returned_body, body)
        self.assertEqual(returned_body, "A normal answer.\n")
        self.assertEqual(result["reasoning_mode"], "LATENT")
        self.assertEqual(result["model_protocol"], "CML/1")
        self.assertEqual(result["model_codec"], "json")
        self.assertEqual(result["payload_kind"], "prose")
        self.assertEqual(result["payload_sha256"], hashlib.sha256(body.encode()).hexdigest())
        self.assertEqual(result["language_state"], "LAYERED")
        self.assertEqual(result["extra_context"], "preserved")
        self.assertEqual(cml.projection_state(result, body), "LAYERED")

    def test_canonicalizer_accepts_normalizable_envelope_values(self) -> None:
        body = "result"
        source = metadata(
            reasoning_mode=" latent ",
            model_protocol=" cml/1 ",
            model_codec=" JSON ",
            payload_kind=" PROSE ",
            speech="  A result is ready.  ",
            model_packet='{ "ops": [["K", "answer", "ready"]], "k": "RESULT", "v": 1 }',
            payload_sha256=cml.payload_sha256(body).upper(),
            language_state="UNLAYERED",
        )
        result = cml.canonicalize_emitter_metadata(source, body)
        self.assertEqual(result["speech"], "A result is ready.")
        self.assertEqual(result["model_packet"], '{"k":"RESULT","ops":[["K","answer","ready"]],"v":1}')
        self.assertEqual(result["payload_sha256"], cml.payload_sha256(body))
        self.assertEqual(result["language_state"], "LAYERED")

    def test_emitter_rejects_missing_or_invalid_layers(self) -> None:
        body = "payload"
        cases = {
            "missing-speech": {"model_packet": packet()},
            "empty-speech": metadata(speech="  "),
            "multiline-speech": metadata(speech="line one\nline two"),
            "unicode-line-separator": metadata(speech="line one\u2028line two"),
            "missing-packet": {"speech": "plain"},
            "bad-packet": metadata(model_packet="not json"),
            "wrong-mode": metadata(reasoning_mode="EXPOSED"),
            "wrong-protocol": metadata(model_protocol="CML/2"),
            "wrong-codec": metadata(model_codec="YAML"),
            "wrong-kind": metadata(payload_kind="THOUGHTS"),
            "wrong-hash": metadata(payload_sha256="0" * 64),
        }
        for name, value in cases.items():
            with self.subTest(name=name), self.assertRaises(cml.ModelLanguageError):
                cml.canonicalize_emitter_metadata(value, body)

    def test_emitter_rejects_every_unicode_splitlines_boundary(self) -> None:
        for separator in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
            with self.subTest(separator=ascii(separator)), self.assertRaises(
                cml.ModelLanguageError
            ):
                cml.canonicalize_emitter_metadata(
                    metadata(speech=f"first{separator}second"), "payload"
                )

    def test_non_json_codecs_are_one_line_opaque_model_projections(self) -> None:
        body = "payload"
        for codec in cml.MODEL_CODECS - {"json"}:
            with self.subTest(codec=codec):
                result = cml.canonicalize_emitter_metadata(
                    metadata(model_codec=codec, model_packet="  compact:model-state  "), body
                )
                self.assertEqual(result["model_codec"], codec)
                self.assertEqual(result["model_packet"], "compact:model-state")
                self.assertEqual(cml.projection_state(result, body), "LAYERED")
        with self.assertRaises(cml.ModelLanguageError):
            cml.canonicalize_emitter_metadata(
                metadata(model_codec="tok", model_packet="two\nlines"), body
            )

    def test_every_tool_consumable_payload_is_returned_byte_for_byte(self) -> None:
        cases: tuple[tuple[str, object, str], ...] = (
            ("code", "#!/usr/bin/env python3\ndef answer():\n    return 42\n", "code"),
            ("data", '{\n  "b": 2,\n  "a": 1\n}\n', "data"),
            ("patch", "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@\n-x=1\n+x=2\n", "patch"),
            ("action", "ACTION: deploy\ntarget=staging\n", "action"),
            ("artifact", b"\x00\xffCML\r\n\x00", "artifact"),
        )
        for name, body, expected_kind in cases:
            with self.subTest(name=name):
                result, returned = cml.canonicalize_emitter_record(metadata(), body)  # type: ignore[arg-type]
                self.assertIs(returned, body)
                self.assertEqual(returned, body)
                self.assertEqual(result["payload_kind"], expected_kind)
                self.assertEqual(result["payload_sha256"], cml.payload_sha256(body))  # type: ignore[arg-type]
                self.assertTrue(cml.is_opaque_payload_kind(expected_kind))

    def test_hash_is_sensitive_to_exact_whitespace_and_line_endings(self) -> None:
        self.assertNotEqual(cml.payload_sha256("x\n"), cml.payload_sha256("x"))
        self.assertNotEqual(cml.payload_sha256("x\r\n"), cml.payload_sha256("x\n"))
        self.assertFalse(cml.is_opaque_payload_kind("prose"))


class LegacyExtractionTests(unittest.TestCase):
    def test_extracts_plain_aliases_and_model_outside_fences(self) -> None:
        body = """Before
```text
PLAIN: hidden backtick speech
MODEL: hidden backtick model
```
~~~
PLAIN ENGLISH: hidden tilde speech
MODEL: hidden tilde model
~~~
PLAIN ENGLISH: Visible summary.
MODEL: {"v":1,"k":"STATE","ops":[["B","answer",42]]}
After
"""
        self.assertEqual(
            cml.extract_legacy_layers(body),
            {
                "speech": "Visible summary.",
                "model": '{"v":1,"k":"STATE","ops":[["B","answer",42]]}',
            },
        )

    def test_shorter_fence_does_not_close_longer_fence(self) -> None:
        body = """````md
PLAIN: hidden
```
MODEL: still hidden
````
PLAIN: visible
MODEL: visible-model
"""
        self.assertEqual(
            cml.extract_legacy_layers(body),
            {"speech": "visible", "model": "visible-model"},
        )

    def test_embedded_labels_and_non_text_bodies_are_not_extracted(self) -> None:
        self.assertEqual(cml.extract_legacy_layers("prefix PLAIN: not a layer"), {})
        self.assertEqual(cml.extract_legacy_layers(b"PLAIN: bytes"), {})  # type: ignore[arg-type]


class ObserverTests(unittest.TestCase):
    def test_unlayered_legacy_record_stays_open_and_gets_plain_projection(self) -> None:
        body = "PLAIN: Human summary.\nMODEL: legacy free-form state\n\nold payload"
        source = {"from": "OLD_NODE"}
        result, returned = cml.enrich_observer_record(source, body)
        self.assertIs(returned, body)
        self.assertEqual(source, {"from": "OLD_NODE"})
        self.assertEqual(result["language_state"], "UNLAYERED")
        self.assertEqual(result["speech"], "Human summary.")
        self.assertEqual(result["model_packet"], "legacy free-form state")
        self.assertEqual(result["payload_sha256"], cml.payload_sha256(body))
        self.assertEqual(cml.projection_state(result, body), "UNLAYERED")

    def test_complete_layer_is_observed_as_layered(self) -> None:
        body = "exact payload"
        emitted = cml.canonicalize_emitter_metadata(metadata(), body)
        observed = cml.enrich_observer_metadata(emitted, body)
        self.assertEqual(observed, emitted)
        self.assertEqual(observed["language_state"], "LAYERED")

    def test_partial_malformed_noncanonical_and_hash_mismatch_are_invalid(self) -> None:
        body = "payload"
        complete = cml.canonicalize_emitter_metadata(metadata(), body)
        cases = {
            "partial": {"model_protocol": "CML/1"},
            "malformed": {**complete, "model_packet": "not json"},
            "noncanonical": {
                **complete,
                "model_packet": '{ "v": 1, "k": "STATE", "ops": [["B", "x"]] }',
            },
            "hash-mismatch": {**complete, "payload_sha256": "f" * 64},
            "false-layer-claim": {"language_state": "LAYERED"},
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                result = cml.enrich_observer_metadata(value, body)
                self.assertEqual(result["language_state"], "INVALID")

    def test_observer_never_raises_for_bad_inputs(self) -> None:
        cases = (
            (None, "body"),
            ([], "body"),
            ({"model_packet": object()}, "body"),
            ({"model_protocol": "CML/1"}, bytearray(b"body")),
            ({}, object()),
        )
        for source, body in cases:
            with self.subTest(source=source, body_type=type(body).__name__):
                result = cml.enrich_observer_metadata(source, body)  # type: ignore[arg-type]
                self.assertIn(result["language_state"], cml.LANGUAGE_STATES)


class SchemaTests(unittest.TestCase):
    def test_schema_declares_the_envelope_and_compact_packet(self) -> None:
        path = Path(__file__).with_name("model_language.schema.json")
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["reasoning_mode"]["const"], "LATENT")
        self.assertEqual(schema["properties"]["model_protocol"]["const"], "CML/1")
        self.assertEqual(set(schema["properties"]["model_codec"]["enum"]), cml.MODEL_CODECS)
        self.assertEqual(schema["properties"]["language_state"]["const"], "LAYERED")
        self.assertEqual(set(schema["$defs"]["packet"]["properties"]["k"]["enum"]), cml.PACKET_KINDS)
        self.assertEqual(
            set(schema["$defs"]["operation"]["prefixItems"][0]["enum"]), cml.OP_CODES
        )
        self.assertFalse(schema["$defs"]["packet"]["additionalProperties"])
        self.assertIn("payload_sha256", schema["required"])


if __name__ == "__main__":
    unittest.main()
