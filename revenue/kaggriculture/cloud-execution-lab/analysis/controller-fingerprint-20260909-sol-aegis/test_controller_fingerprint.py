import gzip
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

import controller_fingerprint as cf


def action(farmer=None, hands=None, market=None):
    return {
        "farmer": [] if farmer is None else farmer,
        "hands": [] if hands is None else hands,
        "market": [] if market is None else market,
    }


def make_replay(*, episode_id=1, agent_name="Bryce Muhlnickel", seat=1, steps=4):
    agents = [{"Name": "opp"}, {"Name": agent_name}]
    if seat == 0:
        agents = [{"Name": agent_name}, {"Name": "opp"}]
    out_steps = []
    for k in range(steps):
        rows = []
        for s in range(2):
            farms = [{"hands": []}, {"hands": []}]
            rows.append(
                {
                    "action": action(),
                    "info": {},
                    "observation": {"farms": farms},
                    "reward": 0,
                    "status": "ACTIVE",
                }
            )
        out_steps.append(rows)
    return {
        "id": "opaque-replay-uuid",
        "info": {"EpisodeId": episode_id, "Agents": agents},
        "steps": out_steps,
    }


def transport():
    return {"filename": "x.json.gz", "bytes": 1, "sha256": "0" * 64, "json_bytes": 1, "json_sha256": "1" * 64}


class CoreTests(unittest.TestCase):
    def test_canonical_order_is_stable(self):
        self.assertEqual(cf.canonical_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')

    def test_digest_is_sha256(self):
        self.assertEqual(cf.digest({"a": 1}), hashlib.sha256(b'{"a":1}').hexdigest())

    def test_find_agent_seat_one(self):
        self.assertEqual(cf.find_agent_seat(make_replay(), "Bryce Muhlnickel"), 1)

    def test_find_agent_seat_zero(self):
        self.assertEqual(cf.find_agent_seat(make_replay(seat=0), "Bryce Muhlnickel"), 0)

    def test_find_agent_missing_fails(self):
        with self.assertRaises(ValueError):
            cf.find_agent_seat(make_replay(), "nobody")

    def test_find_agent_duplicate_fails(self):
        replay = make_replay()
        replay["info"]["Agents"][0]["Name"] = "Bryce Muhlnickel"
        with self.assertRaises(ValueError):
            cf.find_agent_seat(replay, "Bryce Muhlnickel")

    def test_expected_seat_drift_fails(self):
        with self.assertRaises(ValueError):
            cf.fingerprint_replay(make_replay(), transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4, expected_seat=0)

    def test_step_cardinality_drift_fails(self):
        with self.assertRaises(ValueError):
            cf.fingerprint_replay(make_replay(steps=3), transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)

    def test_episode_id_must_be_true_integer(self):
        replay = make_replay()
        replay["info"]["EpisodeId"] = True
        with self.assertRaises(ValueError):
            cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)

    def test_prior_hand_orientation_uses_previous_observation(self):
        replay = make_replay()
        replay["steps"][0][1]["observation"]["farms"][1]["hands"] = [{}, {}]
        replay["steps"][1][1]["action"]["hands"] = [["NORTH"], ["PASS"], ["WATER"]]
        fp = cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(fp.component_values["prior_hand_counts"], [0, 2, 0, 0])
        self.assertEqual(fp.component_values["hands_reachable"][1], [["NORTH"], ["PASS"]])
        self.assertEqual(fp.component_values["hands_unreachable"][1], [["WATER"]])

    def test_step_zero_hands_are_unreachable_without_prior_observation(self):
        replay = make_replay()
        replay["steps"][0][1]["action"]["hands"] = [["PASS"]]
        fp = cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(fp.hand_profile["reachable_rows"], 0)
        self.assertEqual(fp.hand_profile["unreachable_rows"], 1)

    def test_move_directions_normalize_to_move_profile(self):
        replay = make_replay()
        replay["steps"][0][1]["action"]["hands"] = [["NORTH"], ["SOUTH"], ["EAST"], ["WEST"]]
        fp = cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(fp.hand_profile["unreachable_opcode_counts"], {"MOVE": 4})

    def test_market_projection_splits_sell_non_sell_and_empty(self):
        replay = make_replay()
        replay["steps"][0][1]["action"]["market"] = [
            ["SELL", "WHEAT", 2],
            [],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["HIRE", 0],
        ]
        fp = cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(fp.component_values["market_sell"][0], [["SELL", "WHEAT", 2]])
        self.assertEqual(fp.component_values["market_non_sell"][0], [["BUY_PRODUCT", "WHEAT", 1], ["HIRE", 0]])
        self.assertEqual(fp.component_values["market_empty_rows"][0], 1)

    def test_market_profile_counts_empty_row(self):
        replay = make_replay()
        replay["steps"][0][1]["action"]["market"] = [[], ["SELL", "WHEAT", 1]]
        fp = cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(fp.market_profile["opcode_counts"]["<EMPTY>"], 1)
        self.assertEqual(fp.market_profile["opcode_counts"]["SELL"], 1)

    def test_market_empty_step_count(self):
        fp = cf.fingerprint_replay(make_replay(), transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(fp.market_profile["empty_step_count"], 4)

    def test_differing_steps(self):
        a = make_replay(episode_id=1)
        b = make_replay(episode_id=2)
        b["steps"][2][1]["action"]["farmer"] = ["MOVE", 1, 0]
        fa = cf.fingerprint_replay(a, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        fb = cf.fingerprint_replay(b, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertEqual(cf.differing_steps(fa, fb, "farmer"), [2])

    def test_compare_fingerprints_counts(self):
        a = make_replay(episode_id=1)
        b = make_replay(episode_id=2)
        b["steps"][2][1]["action"]["market"] = [["SELL", "WHEAT", 1]]
        fa = cf.fingerprint_replay(a, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        fb = cf.fingerprint_replay(b, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        cmp = cf.compare_fingerprints(fa, fb)
        self.assertEqual(cmp["component_diff_counts"]["market_sell"], 1)
        self.assertEqual(cmp["component_diff_counts"]["market_non_sell"], 0)

    def test_non_sell_only_change_is_isolated(self):
        a = make_replay(episode_id=1)
        b = make_replay(episode_id=2)
        b["steps"][1][1]["action"]["market"] = [["BUY_SEED", "WHEAT", 1]]
        fa = cf.fingerprint_replay(a, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        fb = cf.fingerprint_replay(b, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        cmp = cf.compare_fingerprints(fa, fb)
        self.assertEqual(cmp["component_diff_counts"]["market_non_sell"], 1)
        self.assertEqual(cmp["component_diff_counts"]["market_sell"], 0)

    def test_empty_row_only_change_is_isolated(self):
        a = make_replay(episode_id=1)
        b = make_replay(episode_id=2)
        b["steps"][1][1]["action"]["market"] = [[]]
        fa = cf.fingerprint_replay(a, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        fb = cf.fingerprint_replay(b, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        cmp = cf.compare_fingerprints(fa, fb)
        self.assertEqual(cmp["component_diff_counts"]["market_empty_rows"], 1)
        self.assertEqual(cmp["component_diff_counts"]["market_sell"], 0)
        self.assertEqual(cmp["component_diff_counts"]["market_non_sell"], 0)

    def test_read_gzip_good(self):
        replay = make_replay()
        raw_json = cf.canonical_bytes(replay)
        raw_gz = gzip.compress(raw_json, mtime=0)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json.gz"
            path.write_bytes(raw_gz)
            loaded, tx = cf.read_replay_gzip(path, cf.sha256_bytes(raw_gz))
            self.assertEqual(loaded["info"]["EpisodeId"], 1)
            self.assertEqual(tx["bytes"], len(raw_gz))

    def test_read_gzip_bad_hash_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json.gz"
            path.write_bytes(gzip.compress(b"{}", mtime=0))
            with self.assertRaises(ValueError):
                cf.read_replay_gzip(path, "0" * 64)

    def test_read_invalid_gzip_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json.gz"
            path.write_bytes(b"not-gzip")
            with self.assertRaises(ValueError):
                cf.read_replay_gzip(path)

    def test_read_invalid_json_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json.gz"
            path.write_bytes(gzip.compress(b"not-json", mtime=0))
            with self.assertRaises(ValueError):
                cf.read_replay_gzip(path)

    def test_manifest_duplicate_episode_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            row = {"episode_id": 1, "role": "V1", "seat": 1, "filename": "a", "sha256": "0"*64}
            path.write_text(json.dumps({"schema":"titan-controller-fingerprint-corpus-v1","replays":[row,row]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_manifest_bool_seat_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            row = {"episode_id": 1, "role": "V1", "seat": True, "filename": "a", "sha256": "0"*64}
            path.write_text(json.dumps({"schema":"titan-controller-fingerprint-corpus-v1","replays":[row]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_manifest_path_traversal_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            row = {"episode_id": 1, "role": "V1", "seat": 1, "filename": "../a.json.gz", "sha256": "0"*64}
            path.write_text(json.dumps({"schema":"titan-controller-fingerprint-corpus-v1","replays":[row]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_manifest_nonhex_sha_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            row = {"episode_id": 1, "role": "V1", "seat": 1, "filename": "a.json.gz", "sha256": "z"*64}
            path.write_text(json.dumps({"schema":"titan-controller-fingerprint-corpus-v1","replays":[row]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_manifest_comparison_unknown_episode_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            row = {"episode_id": 1, "role": "V1", "seat": 1, "filename": "a.json.gz", "sha256": "0"*64}
            path.write_text(json.dumps({"schema":"titan-controller-fingerprint-corpus-v1","replays":[row],"comparisons":[[1,2]]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_manifest_bad_schema_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            path.write_text(json.dumps({"schema":"wrong","replays":[]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_manifest_empty_rows_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.json"
            path.write_text(json.dumps({"schema":"titan-controller-fingerprint-corpus-v1","replays":[]}))
            with self.assertRaises(ValueError):
                cf.load_manifest(path)

    def test_verify_evidence_detects_drift(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            replay = make_replay()
            raw = gzip.compress(json.dumps(replay).encode(), mtime=0)
            (td/"1.json.gz").write_bytes(raw)
            manifest = {
                "schema":"titan-controller-fingerprint-corpus-v1",
                "agent_name":"Bryce Muhlnickel",
                "expected_steps":4,
                "replays":[{"episode_id":1,"role":"V1","seat":1,"filename":"1.json.gz","sha256":cf.sha256_bytes(raw)}],
                "comparisons":[]
            }
            (td/"CORPUS.json").write_text(json.dumps(manifest))
            actual = cf.analyze_manifest(td/"CORPUS.json", td)
            (td/"EVIDENCE.json").write_text(json.dumps({**actual, "evidence_sha256":"bad"}))
            with self.assertRaises(ValueError):
                cf.verify_evidence(td/"CORPUS.json", td, td/"EVIDENCE.json")

    def test_report_self_seal(self):
        report = {"schema": cf.SCHEMA, "x": 1}
        report["evidence_sha256"] = cf.digest(report)
        self.assertTrue(cf.verify_report_seal(report))
        report["x"] = 2
        self.assertFalse(cf.verify_report_seal(report))

    def test_manifest_declared_transport_size_is_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            replay = make_replay()
            raw = gzip.compress(json.dumps(replay).encode(), mtime=0)
            (td/"1.json.gz").write_bytes(raw)
            manifest = {
                "schema":"titan-controller-fingerprint-corpus-v1",
                "agent_name":"Bryce Muhlnickel",
                "expected_steps":4,
                "replays":[{"episode_id":1,"role":"V1","seat":1,"filename":"1.json.gz","sha256":cf.sha256_bytes(raw),"bytes":len(raw)+1}],
                "comparisons":[]
            }
            (td/"CORPUS.json").write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                cf.analyze_manifest(td/"CORPUS.json", td)

    def test_public_dict_excludes_values_by_default(self):
        fp = cf.fingerprint_replay(make_replay(), transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertNotIn("component_values", fp.public_dict())

    def test_public_dict_can_include_values(self):
        fp = cf.fingerprint_replay(make_replay(), transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
        self.assertIn("component_values", fp.public_dict(include_component_values=True))


class RealCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        corpus = os.environ.get("AEGIS_CORPUS_DIR")
        if not corpus:
            raise unittest.SkipTest("AEGIS_CORPUS_DIR not set")
        cls.case = Path(__file__).resolve().parent
        cls.report = cf.analyze_manifest(cls.case/"CORPUS.json", Path(corpus))
        cls.by_pair = {(x["left_episode"], x["right_episode"]): x for x in cls.report["comparisons"]}

    def test_transport_hashes_all_five(self):
        self.assertEqual(len(self.report["episodes"]), 5)
        self.assertTrue(cf.verify_report_seal(self.report))

    def test_v2_vs_107142511_exact_non_sell_controller_streams(self):
        c = self.by_pair[(107140666, 107142511)]["component_diff_counts"]
        for key in ("farmer","hands_submitted","prior_hand_counts","hands_reachable","hands_unreachable","market_non_sell"):
            self.assertEqual(c[key], 0, key)

    def test_v2_vs_107150217_exact_non_sell_controller_streams(self):
        c = self.by_pair[(107140666, 107150217)]["component_diff_counts"]
        for key in ("farmer","hands_submitted","prior_hand_counts","hands_reachable","hands_unreachable","market_non_sell"):
            self.assertEqual(c[key], 0, key)

    def test_sell_and_full_market_diff_counts_match_recovered_claim(self):
        a = self.by_pair[(107140666, 107142511)]["component_diff_counts"]
        b = self.by_pair[(107140666, 107150217)]["component_diff_counts"]
        self.assertEqual((a["market_sell"], a["market_full"]), (43, 51))
        self.assertEqual((b["market_sell"], b["market_full"]), (42, 49))

    def test_shared_hand_profile_matches_recovered_claim(self):
        profiles = [self.report["episodes"][str(e)]["hand_profile"] for e in (107140666,107142511,107150217)]
        self.assertEqual(profiles[0], profiles[1])
        self.assertEqual(profiles[0], profiles[2])
        self.assertEqual(profiles[0]["submitted_rows"], 6451)
        self.assertEqual(profiles[0]["reachable_rows"], 6429)
        self.assertEqual(profiles[0]["unreachable_rows"], 22)
        self.assertEqual(profiles[0]["unreachable_opcode_counts"], {"MOVE":14,"PASS":5,"WATER":3})


class CheckedInEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = Path(__file__).resolve().parent
        cls.manifest = cf.load_manifest(cls.case / "CORPUS.json")
        cls.evidence = json.loads((cls.case / "EVIDENCE.json").read_text(encoding="utf-8"))

    def test_checked_in_evidence_self_seal_and_manifest_binding(self):
        self.assertTrue(cf.verify_report_seal(self.evidence))
        self.assertEqual(
            self.evidence["manifest_sha256"],
            cf.sha256_bytes((self.case / "CORPUS.json").read_bytes()),
        )

    def test_checked_in_transport_manifest_has_all_five_exact_episodes(self):
        rows = {row["episode_id"]: row for row in self.manifest["replays"]}
        self.assertEqual(set(rows), {107113451, 107130860, 107140666, 107142511, 107150217})
        self.assertEqual(rows[107142511]["sha256"], "a18879c53613cb90f75e6f31f8d60c9726c490fd4ec6c753d3e90e69a1555d68")
        self.assertEqual(rows[107130860]["sha256"], "9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b")

    def test_checked_in_comparison_counts_match_recovered_result(self):
        by_pair = {(x["left_episode"], x["right_episode"]): x for x in self.evidence["comparisons"]}
        a = by_pair[(107140666, 107142511)]["component_diff_counts"]
        b = by_pair[(107140666, 107150217)]["component_diff_counts"]
        self.assertEqual((a["farmer"], a["hands_submitted"], a["market_non_sell"], a["market_sell"], a["market_full"]), (0, 0, 0, 43, 51))
        self.assertEqual((b["farmer"], b["hands_submitted"], b["market_non_sell"], b["market_sell"], b["market_full"]), (0, 0, 0, 42, 49))


# Fail-closed action-shape variants are separate named tests so the test count is explicit.
def _make_missing_action_key_test(key):
    def test(self):
        replay = make_replay()
        del replay["steps"][0][1]["action"][key]
        with self.assertRaises(ValueError):
            cf.fingerprint_replay(replay, transport=transport(), agent_name="Bryce Muhlnickel", expected_steps=4)
    return test

for _key in ("farmer", "hands", "market"):
    setattr(CoreTests, f"test_missing_action_{_key}_fails", _make_missing_action_key_test(_key))


if __name__ == "__main__":
    unittest.main()
