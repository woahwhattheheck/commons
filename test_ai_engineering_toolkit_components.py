from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from host import ai_engineering_toolkit as toolkit


IDS = ("muhlnickel", "titan", "whitebox", "subzero")


def component(identifier: str, *, role: str | None = None) -> dict:
    return {
        "id": identifier,
        "role": role or f"role-{identifier}",
        "evidence_class": "STRUCTURAL_ONLY",
        "sources": [f"sources/{identifier}.txt"],
    }


def catalog(components: object) -> dict:
    return {
        "schema": "commons-ai-engineering-toolkit-v1",
        "toolkit_id": "test-toolkit",
        "components": components,
        "build_stages": ["resolve", "compose"],
    }


class AiEngineeringToolkitComponentTests(unittest.TestCase):
    def load(self, value: dict) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return toolkit.load_catalog(path)

    def test_exact_four_canonical_components_are_accepted(self) -> None:
        value = catalog([component(identifier) for identifier in IDS])
        loaded = self.load(value)
        self.assertEqual([row["id"] for row in loaded["components"]], list(IDS))

    def test_canonical_components_may_be_reordered_without_duplication(self) -> None:
        rows = [component(identifier) for identifier in reversed(IDS)]
        loaded = self.load(catalog(rows))
        self.assertEqual([row["id"] for row in loaded["components"]], list(reversed(IDS)))

    def test_fifth_duplicate_component_is_rejected(self) -> None:
        rows = [component(identifier) for identifier in IDS]
        rows.append(component("titan", role="replacement-role"))
        with self.assertRaisesRegex(ValueError, "exactly the four canonical"):
            self.load(catalog(rows))

    def test_duplicate_replacing_a_family_is_rejected(self) -> None:
        rows = [component("muhlnickel"), component("titan"), component("titan"), component("subzero")]
        with self.assertRaisesRegex(ValueError, "exactly the four canonical"):
            self.load(catalog(rows))

    def test_unknown_component_replacing_a_family_is_rejected(self) -> None:
        rows = [component("muhlnickel"), component("titan"), component("whitebox"), component("other")]
        with self.assertRaisesRegex(ValueError, "exactly the four canonical"):
            self.load(catalog(rows))

    def test_component_rows_must_be_objects(self) -> None:
        for malformed in (None, "titan", 7, [], True):
            rows = [component(identifier) for identifier in IDS]
            rows[1] = malformed
            with self.subTest(malformed=repr(malformed)):
                with self.assertRaisesRegex(ValueError, "components must be objects"):
                    self.load(catalog(rows))

    def test_components_surface_must_be_a_list_of_exact_cardinality(self) -> None:
        malformed = (
            None,
            {},
            [component(identifier) for identifier in IDS[:3]],
            [component(identifier) for identifier in IDS] + [component("other")],
        )
        for value in malformed:
            with self.subTest(value=type(value).__name__):
                with self.assertRaisesRegex(ValueError, "exactly the four canonical"):
                    self.load(catalog(value))

    def test_valid_plan_contains_each_component_and_role_once(self) -> None:
        rows = [component(identifier) for identifier in IDS]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "sources"
            source_dir.mkdir()
            for identifier in IDS:
                (source_dir / f"{identifier}.txt").write_text(identifier, encoding="utf-8")
            path = root / "catalog.json"
            path.write_text(json.dumps(catalog(rows)), encoding="utf-8")
            loaded = toolkit.load_catalog(path)
            plan = toolkit.build_plan("compose one measured system", loaded, root)
        self.assertEqual(plan["selected_components"], list(IDS))
        self.assertEqual(set(plan["component_roles"]), set(IDS))
        self.assertEqual(len(plan["component_roles"]), 4)
        self.assertEqual([row["component"] for row in plan["source_receipts"]], list(IDS))


if __name__ == "__main__":
    unittest.main()
