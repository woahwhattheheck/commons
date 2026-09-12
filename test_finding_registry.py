import unittest

from host.finding_registry import FindingError, load_registry, summarize


def layer(count, state=None, search_space="13 tapes x 719 steps"):
    state = state or ("UNKNOWN" if count is None else "MEASURED")
    return {"state": state, "count": count, "search_space": search_space}


def finding(fid="F1"):
    return {
        "id": fid,
        "canonical_parent": "main@abc",
        "evidence": "artifact:sha256",
        "detector_hits": layer(3),
        "candidate_callbacks": layer(2),
        "realized_actions": layer(1),
    }


class FindingRegistryTests(unittest.TestCase):
    def test_zero_unknown_and_not_searched_are_distinct(self):
        zero = finding("zero")
        zero["realized_actions"] = layer(0)
        unknown = finding("unknown")
        unknown["realized_actions"] = layer(None, "UNKNOWN", "replay result unavailable")
        unsearched = finding("unsearched")
        unsearched["realized_actions"] = layer(None, "NOT_SEARCHED", "replay not executed")
        out = summarize(load_registry({"version": 1, "findings": [zero, unknown, unsearched]}))
        rows = {row["id"]: row for row in out["findings"]}
        self.assertEqual(rows["zero"]["zero_layers"], ["realized_actions"])
        self.assertEqual(rows["unknown"]["unknown_layers"], ["realized_actions"])
        self.assertEqual(rows["unknown"]["not_searched_layers"], [])
        self.assertEqual(rows["unsearched"]["not_searched_layers"], ["realized_actions"])
        self.assertEqual(rows["unsearched"]["unknown_layers"], [])
        self.assertEqual(rows["unknown"]["realized_actions"]["count"], rows["unsearched"]["realized_actions"]["count"])
        self.assertNotEqual(rows["unknown"]["realized_actions"]["state"], rows["unsearched"]["realized_actions"]["state"])

    def test_complete_requires_all_measured(self):
        complete = finding("complete")
        incomplete = finding("incomplete")
        incomplete["candidate_callbacks"] = layer(None, "UNKNOWN")
        out = summarize(load_registry({"version": 1, "findings": [incomplete, complete]}))
        rows = {row["id"]: row for row in out["findings"]}
        self.assertTrue(rows["complete"]["complete_census"])
        self.assertFalse(rows["incomplete"]["complete_census"])
        self.assertEqual(out["counts"], {"findings": 2, "complete": 1, "incomplete": 1})

    def test_state_count_consistency(self):
        cases = [
            ({"state": "MEASURED", "count": None, "search_space": "x"}, "INVALID_COUNT"),
            ({"state": "UNKNOWN", "count": 0, "search_space": "x"}, "INVALID_COUNT"),
            ({"state": "NOT_SEARCHED", "count": 0, "search_space": "x"}, "INVALID_COUNT"),
            ({"state": "unknown", "count": None, "search_space": "x"}, "INVALID_LAYER_STATE"),
        ]
        for bad, code in cases:
            item = finding()
            item["candidate_callbacks"] = bad
            with self.subTest(bad=bad), self.assertRaises(FindingError) as caught:
                load_registry({"version": 1, "findings": [item]})
            self.assertEqual(caught.exception.code, code)

    def test_measured_count_is_exact_nonnegative_int(self):
        for bad in (True, 1.0, -1, "1", None):
            item = finding()
            item["candidate_callbacks"] = {"state": "MEASURED", "count": bad, "search_space": "x"}
            with self.subTest(bad=bad), self.assertRaises(FindingError) as caught:
                load_registry({"version": 1, "findings": [item]})
            self.assertEqual(caught.exception.code, "INVALID_COUNT")

    def test_search_space_required_for_null_states(self):
        for state in ("UNKNOWN", "NOT_SEARCHED"):
            item = finding()
            item["realized_actions"] = {"state": state, "count": None, "search_space": ""}
            with self.subTest(state=state), self.assertRaises(FindingError) as caught:
                load_registry({"version": 1, "findings": [item]})
            self.assertEqual(caught.exception.code, "INVALID_FIELD")

    def test_layer_shape_and_all_three_layers_are_strict(self):
        item = finding()
        item["realized_actions"]["note"] = "extra"
        with self.assertRaises(FindingError) as caught:
            load_registry({"version": 1, "findings": [item]})
        self.assertEqual(caught.exception.code, "INVALID_LAYER")
        item = finding()
        del item["candidate_callbacks"]
        with self.assertRaises(FindingError) as caught:
            load_registry({"version": 1, "findings": [item]})
        self.assertEqual(caught.exception.code, "INVALID_FINDING_FIELDS")

    def test_duplicate_unknown_fields_and_version_fail_closed(self):
        with self.assertRaises(FindingError) as caught:
            load_registry({"version": 1, "findings": [finding("F"), finding("F")]})
        self.assertEqual(caught.exception.code, "DUPLICATE_FINDING")
        item = finding()
        item["verdict"] = "PASS"
        with self.assertRaises(FindingError) as caught:
            load_registry({"version": 1, "findings": [item]})
        self.assertEqual(caught.exception.code, "INVALID_FINDING_FIELDS")
        with self.assertRaises(FindingError) as caught:
            load_registry({"version": True, "findings": []})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_VERSION")

    def test_deterministic_id_order(self):
        rows = load_registry({"version": 1, "findings": [finding("z"), finding("a"), finding("m")]})
        self.assertEqual([row["id"] for row in rows], ["a", "m", "z"])


if __name__ == "__main__":
    unittest.main()
