import tempfile
import unittest
from pathlib import Path

from host.opponent_registry import OpponentRegistryError, load_registry, read_registry, summarize


D1 = "1" * 64
D2 = "2" * 64


def opponent(name="Shop Router", source="artifact:opponent.py"):
    return {"name": name, "source": source}


def witness(wid="W1", digest=D1, observable="opening worker count at day 2"):
    return {
        "id": wid,
        "opponent_digest": digest,
        "canonical_parent": "titan/v3.1@abc",
        "intervention": "enable candidate factor only",
        "observable": observable,
        "outcome": "margin delta +12.5",
        "evidence": "artifact:receipt-sha256",
    }


def read_raw(raw):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "registry.json"
        path.write_text(raw, encoding="utf-8")
        return read_registry(str(path))


class OpponentRegistryTests(unittest.TestCase):
    def test_digest_key_and_witness_binding(self):
        out = load_registry({"version": 1, "opponents": {D1: opponent()}, "witnesses": [witness()]})
        self.assertEqual(list(out["opponents"]), [D1])
        self.assertEqual(out["witnesses"][0]["opponent_digest"], D1)
        self.assertEqual(out["witnesses"][0]["observable"], "opening worker count at day 2")

    def test_unknown_opponent_fails_closed(self):
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": 1, "opponents": {D1: opponent()}, "witnesses": [witness(digest=D2)]})
        self.assertEqual(caught.exception.code, "UNKNOWN_OPPONENT")

    def test_digest_must_be_exact_lowercase_sha256(self):
        for bad in ["abc", "A" * 64, "1" * 63, "g" * 64]:
            with self.subTest(bad=bad), self.assertRaises(OpponentRegistryError) as caught:
                load_registry({"version": 1, "opponents": {bad: opponent()}, "witnesses": []})
            self.assertEqual(caught.exception.code, "INVALID_DIGEST")

    def test_observable_is_required_and_nonempty(self):
        item = witness(observable="")
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": 1, "opponents": {D1: opponent()}, "witnesses": [item]})
        self.assertEqual(caught.exception.code, "INVALID_FIELD")
        self.assertEqual(caught.exception.details["field"], "observable")
        item = witness()
        del item["observable"]
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": 1, "opponents": {D1: opponent()}, "witnesses": [item]})
        self.assertEqual(caught.exception.code, "INVALID_WITNESS")

    def test_duplicate_witness_ids_fail_closed(self):
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": 1, "opponents": {D1: opponent()}, "witnesses": [witness("W"), witness("W")]})
        self.assertEqual(caught.exception.code, "DUPLICATE_WITNESS")

    def test_duplicate_json_members_fail_closed_before_semantic_validation(self):
        cases = {
            "opponent digest": ('{"version":1,"opponents":{"' + D1 + '":{"name":"A","source":"one"},"' + D1 + '":{"name":"B","source":"two"}},"witnesses":[]}', D1),
            "witness id": ('{"version":1,"opponents":{"' + D1 + '":{"name":"A","source":"one"}},"witnesses":[{"id":"W1","id":"W2","opponent_digest":"' + D1 + '","canonical_parent":"main@abc","intervention":"x","observable":"y","outcome":"z","evidence":"e"}]}', "id"),
            "witness opponent reference": ('{"version":1,"opponents":{"' + D1 + '":{"name":"A","source":"one"},"' + D2 + '":{"name":"B","source":"two"}},"witnesses":[{"id":"W1","opponent_digest":"' + D1 + '","opponent_digest":"' + D2 + '","canonical_parent":"main@abc","intervention":"x","observable":"y","outcome":"z","evidence":"e"}]}', "opponent_digest"),
            "witness evidence": ('{"version":1,"opponents":{"' + D1 + '":{"name":"A","source":"one"}},"witnesses":[{"id":"W1","opponent_digest":"' + D1 + '","canonical_parent":"main@abc","intervention":"x","observable":"y","outcome":"z","evidence":"old","evidence":"new"}]}', "evidence"),
        }
        for name, (raw, key) in cases.items():
            with self.subTest(name=name), self.assertRaises(OpponentRegistryError) as caught:
                read_raw(raw)
            self.assertEqual(caught.exception.code, "DUPLICATE_JSON_KEY")
            self.assertEqual(caught.exception.details["key"], key)

    def test_opponent_metadata_shape_is_exact(self):
        bad = opponent()
        bad["digest"] = D1
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": 1, "opponents": {D1: bad}, "witnesses": []})
        self.assertEqual(caught.exception.code, "INVALID_OPPONENT")

    def test_witness_shape_is_exact(self):
        item = witness()
        item["causal_score"] = 1
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": 1, "opponents": {D1: opponent()}, "witnesses": [item]})
        self.assertEqual(caught.exception.code, "INVALID_WITNESS")

    def test_summary_is_deterministic_and_counts_by_digest(self):
        registry = load_registry({"version": 1, "opponents": {D2: opponent("B"), D1: opponent("A")}, "witnesses": [witness("z", D2), witness("a", D1), witness("m", D1)]})
        out = summarize(registry)
        self.assertEqual(list(out["opponents"]), [D1, D2])
        self.assertEqual([row["id"] for row in out["witnesses"]], ["a", "m", "z"])
        self.assertEqual(out["counts"]["witnesses_by_opponent"], {D1: 2, D2: 1})

    def test_bool_version_is_rejected(self):
        with self.assertRaises(OpponentRegistryError) as caught:
            load_registry({"version": True, "opponents": {}, "witnesses": []})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_VERSION")


if __name__ == "__main__":
    unittest.main()
