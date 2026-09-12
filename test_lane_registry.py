import json
import tempfile
import unittest

from host.lane_registry import RegistryError, effective_registry, load_registry, read_registry, render_registry


def row(lane_id, state="PASSED", composes=None, **overrides):
    item = {
        "id": lane_id,
        "canonical_parent": "main@abc",
        "durable_carrier": f"pr:{lane_id}",
        "terminal_state": state,
        "next_gate": "field gate",
        "production_consumer": "v3/final",
        "composes": list(composes or []),
    }
    item.update(overrides)
    return item


def payload(*rows):
    return {"version": 1, "lanes": list(rows)}


class LaneRegistryTests(unittest.TestCase):
    def test_five_field_report_is_required(self):
        item = row("A")
        del item["next_gate"]
        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(item))
        self.assertEqual(caught.exception.code, "MISSING_FIELDS")
        self.assertEqual(caught.exception.details["fields"], ["next_gate"])

    def test_reject_propagates_transitively_only_to_dependents(self):
        lanes = load_registry(
            payload(
                row("A", state="REJECTED"),
                row("B", composes=["A"]),
                row("C", composes=["B"]),
                row("D"),
            )
        )
        effective = effective_registry(lanes)
        self.assertEqual(effective["A"].effective_state, "REJECTED")
        self.assertEqual(effective["B"].effective_state, "REJECTED_UPSTREAM")
        self.assertEqual(effective["C"].effective_state, "REJECTED_UPSTREAM")
        self.assertEqual(effective["C"].rejected_by, ("A",))
        self.assertEqual(effective["D"].effective_state, "PASSED")
        self.assertEqual(effective["D"].rejected_by, ())

    def test_multiple_rejected_roots_are_sorted_and_retained(self):
        lanes = load_registry(
            payload(
                row("z", state="REJECTED"),
                row("a", state="REJECTED"),
                row("consumer", composes=["z", "a"]),
            )
        )
        effective = effective_registry(lanes)
        self.assertEqual(effective["consumer"].rejected_by, ("a", "z"))
        self.assertEqual(effective["consumer"].effective_state, "REJECTED_UPSTREAM")

    def test_unknown_composition_fails_closed(self):
        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(row("A", composes=["missing"])))
        self.assertEqual(caught.exception.code, "UNKNOWN_COMPOSITION")
        self.assertEqual(caught.exception.details["lanes"], ["missing"])

    def test_cycle_fails_closed(self):
        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(row("A", composes=["B"]), row("B", composes=["A"])))
        self.assertEqual(caught.exception.code, "COMPOSITION_CYCLE")
        self.assertEqual(caught.exception.details["cycle"][0], "A")
        self.assertEqual(caught.exception.details["cycle"][-1], "A")

    def test_duplicate_ids_and_duplicate_edges_fail_closed(self):
        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(row("A"), row("A")))
        self.assertEqual(caught.exception.code, "DUPLICATE_LANE")

        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(row("A"), row("B", composes=["A", "A"])))
        self.assertEqual(caught.exception.code, "DUPLICATE_COMPOSITION")

    def test_non_string_factor_and_unknown_field_fail_closed(self):
        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(row("A", canonical_parent=True)))
        self.assertEqual(caught.exception.code, "INVALID_FIELD")

        item = row("A")
        item["mystery"] = "x"
        with self.assertRaises(RegistryError) as caught:
            load_registry(payload(item))
        self.assertEqual(caught.exception.code, "UNKNOWN_FIELDS")

    def test_bool_version_is_not_integer_version(self):
        with self.assertRaises(RegistryError) as caught:
            load_registry({"version": True, "lanes": []})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_VERSION")

    def test_render_is_deterministic_by_lane_id(self):
        lanes = load_registry(payload(row("z"), row("a"), row("m", state="BLOCKED")))
        rendered = render_registry(lanes)
        self.assertEqual([item["id"] for item in rendered["lanes"]], ["a", "m", "z"])
        self.assertEqual(rendered["counts"], {"BLOCKED": 1, "PASSED": 2})
        encoded1 = json.dumps(rendered, sort_keys=True, separators=(",", ":"))
        encoded2 = json.dumps(render_registry(lanes), sort_keys=True, separators=(",", ":"))
        self.assertEqual(encoded1, encoded2)

    def test_read_registry_rejects_non_json(self):
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as handle:
            handle.write("{'version': 1, 'lanes': []}")
            handle.flush()
            with self.assertRaises(RegistryError) as caught:
                read_registry(handle.name)
        self.assertEqual(caught.exception.code, "INVALID_JSON")

    def test_duplicate_lane_state_json_key_fails_before_rejection_can_be_erased(self):
        text = (
            '{"version":1,"lanes":[{'
            '"id":"A","canonical_parent":"main@abc","durable_carrier":"pr:A",'
            '"terminal_state":"REJECTED","terminal_state":"PASSED",'
            '"next_gate":"field gate","production_consumer":"v3/final","composes":[]}]}'
        )
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            with self.assertRaises(RegistryError) as caught:
                read_registry(handle.name)
        self.assertEqual(caught.exception.code, "DUPLICATE_JSON_KEY")
        self.assertEqual(caught.exception.details["key"], "terminal_state")

    def test_duplicate_top_level_json_key_fails_before_indexing(self):
        text = '{"version":1,"version":1,"lanes":[]}'
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            with self.assertRaises(RegistryError) as caught:
                read_registry(handle.name)
        self.assertEqual(caught.exception.code, "DUPLICATE_JSON_KEY")
        self.assertEqual(caught.exception.details["key"], "version")


if __name__ == "__main__":
    unittest.main()
