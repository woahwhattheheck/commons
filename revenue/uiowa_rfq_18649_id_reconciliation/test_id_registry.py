from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from id_registry import (
    Identity,
    Registry,
    RegistryError,
    load_manifest,
    loads_strict,
)

ROOT = Path(__file__).resolve().parent
COLLISIONS = ROOT / "fixtures" / "collisions.json"
CURRENT = ROOT / "fixtures" / "current_component_shapes.json"


class RegistryTests(unittest.TestCase):
    def test_every_supported_kind_can_collide_without_silent_join(self) -> None:
        registry = Registry.from_path(COLLISIONS)
        collisions = {(row["kind"], row["original_id"]) for row in registry.collisions()}
        self.assertEqual(
            collisions,
            {
                ("source", "SRC-001"),
                ("observation", "E-001"),
                ("finding", "F-001"),
                ("recommendation", "R-001"),
                ("service", "ESS"),
            },
        )
        for kind, original_id in collisions:
            result = registry.resolve(kind=kind, original_id=original_id)
            self.assertEqual(result["status"], "ambiguous")
            self.assertEqual(len(result["candidates"]), 2)
            self.assertNotEqual(
                result["candidates"][0]["canonical_id"],
                result["candidates"][1]["canonical_id"],
            )

    def test_qualified_collision_resolves_exactly(self) -> None:
        registry = Registry.from_path(COLLISIONS)
        a = registry.resolve(
            namespace="component-a", kind="finding", original_id="F-001"
        )
        b = registry.resolve(
            namespace="component-b", kind="finding", original_id="F-001"
        )
        self.assertEqual(a["status"], "resolved")
        self.assertEqual(b["status"], "resolved")
        self.assertNotEqual(a["record"]["canonical_id"], b["record"]["canonical_id"])
        self.assertEqual(a["record"]["original_id"], "F-001")
        self.assertEqual(b["record"]["original_id"], "F-001")

    def test_explicit_equivalence_does_not_make_unqualified_lookup_silent(self) -> None:
        registry = Registry.from_path(CURRENT)
        result = registry.resolve(kind="service", original_id="ESS")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(
            result["candidates"][0]["equivalence_set_id"],
            result["candidates"][1]["equivalence_set_id"],
        )
        namespaces = {row["namespace"] for row in result["candidates"]}
        self.assertEqual(namespaces, {"traceability-rehearsal", "rating-model"})

    def test_legitimate_cross_component_mapping_is_reproducible(self) -> None:
        registry = Registry.from_path(CURRENT)
        output = registry.output()
        by_link = {link["link_id"]: link for link in output["links"]}
        self.assertEqual(
            by_link["REF-RECOMMENDATION-FINDING-01"]["from_canonical_id"],
            Identity("traceability-rehearsal", "recommendation", "R-001").canonical_id,
        )
        self.assertEqual(
            by_link["REF-RECOMMENDATION-FINDING-01"]["to_canonical_id"],
            Identity("traceability-rehearsal", "finding", "F-002").canonical_id,
        )
        source = registry.resolve(
            namespace="framework-source-register",
            kind="source",
            original_id="NIST SP 800-218",
        )
        crosswalk = registry.resolve(
            namespace="framework-crosswalk",
            kind="source",
            original_id="NIST SP 800-218",
        )
        self.assertEqual(
            source["record"]["equivalence_set_id"],
            crosswalk["record"]["equivalence_set_id"],
        )

    def test_semantic_digest_and_mapping_are_input_order_invariant(self) -> None:
        manifest = load_manifest(CURRENT)
        first = Registry(manifest)
        reordered = dict(manifest)
        reordered["records"] = list(reversed(manifest["records"]))
        reordered["links"] = list(reversed(manifest["links"]))
        second = Registry(reordered)
        self.assertEqual(first.manifest_digest, second.manifest_digest)
        self.assertEqual(first.output(), second.output())

    def test_dangling_link_is_rejected(self) -> None:
        manifest = load_manifest(CURRENT)
        manifest["links"][0]["to"]["original_id"] = "DOES-NOT-EXIST"
        with self.assertRaisesRegex(RegistryError, "to identity does not exist"):
            Registry(manifest)

    def test_equivalence_cannot_cross_kinds(self) -> None:
        manifest = load_manifest(CURRENT)
        manifest["links"][0]["to"] = {
            "namespace": "traceability-rehearsal",
            "kind": "observation",
            "original_id": "E-001",
        }
        with self.assertRaisesRegex(RegistryError, "same kind"):
            Registry(manifest)

    def test_duplicate_identity_tuple_is_rejected(self) -> None:
        manifest = load_manifest(CURRENT)
        manifest["records"].append(dict(manifest["records"][0]))
        with self.assertRaisesRegex(RegistryError, "duplicate identity tuple"):
            Registry(manifest)

    def test_canonical_id_preserves_delimiter_rich_original_id(self) -> None:
        ident = Identity("component/a:b", "source", "SRC:alpha/beta?x=1")
        self.assertEqual(
            ident.canonical_id,
            "urn:uiowa-id:v1:source:component%2Fa%3Ab:SRC%3Aalpha%2Fbeta%3Fx%3D1",
        )

    def test_duplicate_json_keys_fail_closed(self) -> None:
        with self.assertRaisesRegex(RegistryError, "duplicate JSON key"):
            loads_strict(
                '{"schema_version":"uiowa-id-map/v1","records":[],"records":[],"links":[]}'
            )


if __name__ == "__main__":
    unittest.main()
