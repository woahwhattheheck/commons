#!/usr/bin/env python3
"""Contract tests for WB-METRICS: the White Box metric union, pure stdlib.

Metric math is tested against hand-computed vectors; the wb_range wiring is
tested over the same loopback Range server as test_wb_range.py. Nothing
leaves the loopback interface.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

_spec_m = importlib.util.spec_from_file_location(
    "wb_metrics", ROOT / "host/wb_metrics.py")
wb_metrics = importlib.util.module_from_spec(_spec_m)
assert _spec_m.loader is not None
_spec_m.loader.exec_module(wb_metrics)

_spec_r = importlib.util.spec_from_file_location(
    "wb_range", ROOT / "host/wb_range.py")
wb_range = importlib.util.module_from_spec(_spec_r)
assert _spec_r.loader is not None
_spec_r.loader.exec_module(wb_range)

from test_wb_range import RangeHandler, RangeServer, build_safetensors


class PrimitivesTests(unittest.TestCase):
    def test_cos_and_unit(self):
        self.assertAlmostEqual(wb_metrics.cos([1, 0], [1, 0]), 1.0)
        self.assertAlmostEqual(wb_metrics.cos([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(wb_metrics.cos([1, 0], [-1, 0]), -1.0)
        self.assertEqual(wb_metrics.cos([0, 0], [1, 1]), 0.0)
        u = wb_metrics.unit([3, 4])
        self.assertAlmostEqual(wb_metrics.norm(u), 1.0)

    def test_percentile_and_histogram(self):
        vals = sorted(float(i) for i in range(101))
        self.assertAlmostEqual(wb_metrics.percentile(vals, 50), 50.0)
        self.assertAlmostEqual(wb_metrics.percentile(vals, 99), 99.0)
        hist = wb_metrics.histogram([0.0, 1.0, 2.0, 3.0], 2, 0.0, 4.0)
        self.assertEqual(hist["bins"], [2, 2])

    def test_byte_entropy(self):
        self.assertEqual(wb_metrics.byte_entropy(b""), 0.0)
        self.assertEqual(wb_metrics.byte_entropy(b"\x00" * 64), 0.0)
        uniform = bytes(range(256))
        self.assertAlmostEqual(wb_metrics.byte_entropy(uniform), 8.0)

    def test_role_and_layer(self):
        self.assertEqual(wb_metrics.role_of("blk.3.ffn_down.weight"),
                         "ffn_down")
        self.assertEqual(wb_metrics.role_of(
            "model.layers.3.mlp.down_proj.weight"), "down_proj")
        self.assertEqual(wb_metrics.layer_of("blk.17.attn_q.weight"), 17)
        self.assertEqual(wb_metrics.layer_of("model.layers.5.mlp.up_proj"), 5)
        self.assertEqual(wb_metrics.layer_of("token_embd.weight"), -1)


class TensorStatsTests(unittest.TestCase):
    def test_stats_and_stress(self):
        values = [0.0] * 96 + [1.0, -1.0] * 16
        result = wb_metrics.tensor_stats(values, block=32)
        self.assertAlmostEqual(result["mean"], 0.0)
        self.assertGreater(result["std"], 0.0)
        self.assertEqual(result["min"], -1.0)
        self.assertEqual(result["max"], 1.0)
        self.assertAlmostEqual(result["sparsity"], 96 / 128)
        self.assertEqual(result["stress"]["max"], 1.0)
        self.assertEqual(result["insane"], 0)

    def test_insane_counted(self):
        values = [1.0, float("nan"), float("inf"), -1.0]
        result = wb_metrics.tensor_stats(values, block=2)
        self.assertEqual(result["insane"], 2)

    def test_row_norm_stats(self):
        rows = [[3.0, 4.0], [0.0, 5.0], [6.0, 8.0]]
        result = wb_metrics.row_norm_stats(rows)
        self.assertAlmostEqual(result["rownorm_mean"], (5 + 5 + 10) / 3)
        self.assertGreaterEqual(result["rownorm_cv"], 0.0)


class EntropyAndMagicsTests(unittest.TestCase):
    def test_entropy_crater_flags_flat_rows(self):
        rng_rows = [bytes((i * 37 + j * 11) % 256 for j in range(384))
                    for i in range(40)]
        crater = [b"\x00" * 384] * 3
        rows = rng_rows[:10] + crater + rng_rows[10:]
        result = wb_metrics.entropy_scan(rows, drop=0.7)
        self.assertEqual(result["n_flagged"], 3)
        self.assertIn([10, 12], result["flagged_blocks"])

    def test_magic_scan(self):
        payload = b"\x00" * 100 + b"PFCGAME1" + b"\xff" * 50 + b"PFCTYPED"
        result = wb_metrics.magic_scan(payload, base_offset=1000)
        self.assertEqual(result["hits"], 2)
        self.assertEqual(result["tags"]["PFCGAME1"]["offsets"], [1100])
        self.assertNotIn(b"PFCXXXXX", result["tags"])


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        for i in range(64):
            angle = i * 0.1
            self.rows.append([math.cos(angle), math.sin(angle), 0.01 * i])

    def test_anisotropy_fields(self):
        result = wb_metrics.anisotropy(self.rows, pairs=200, seed=1)
        for key in ("random_pair_cos_mean", "p05", "p50", "p95",
                    "mean_vector_norm", "rows"):
            self.assertIn(key, result)
        self.assertEqual(result["rows"], 64)

    def test_sign_cos_pearson_bounds(self):
        result = wb_metrics.sign_cos_pearson(self.rows, pairs=200, seed=1)
        self.assertGreaterEqual(result["sign_cos_pearson_r"], -1.0)
        self.assertLessEqual(result["sign_cos_pearson_r"], 1.0)

    def test_rogue_dims(self):
        rows = [[0.0, 0.0, (i % 7) * 3.0] for i in range(40)]
        result = wb_metrics.rogue_dims(rows, frac=0.01)
        self.assertEqual(result["rogue_dim_ids"][0], 2)
        self.assertGreater(result["top1_frac_of_var"], 0.9)

    def test_requantize_row(self):
        row = [0.3, -0.7, 1.0]
        one_bit = wb_metrics.requantize_row(row, 1)
        self.assertEqual(one_bit, [1.0, -1.0, 1.0])
        sixteen = wb_metrics.requantize_row(row, 16)
        self.assertEqual(sixteen, row)

    def test_bitdepth_curve_shape(self):
        ant = [([1.0, 0.2, 0.1], [0.9, 0.3, 0.0])]
        rnd = [([1.0, 0.0], [0.0, 1.0])]
        curve = wb_metrics.bitdepth_curve(ant, rnd, {}, ks=(4, 1))
        self.assertEqual([c["bits"] for c in curve], [4, 1])
        self.assertEqual(curve[1]["levels"], 2)


class CircuitryTests(unittest.TestCase):
    def test_transistor_classification(self):
        gate = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
        up = [[0.9, 0.1], [-0.9, -0.1], [0.0, 1.0], [1.0, 1.0]]
        down = [[0.5, 0.0], [0.5, 0.0], [0.0, 0.5], [0.0, 0.0]]
        result = wb_metrics.circuitry(gate, up, down, threshold=0.15)
        self.assertEqual(result["n_ff"], 4)
        self.assertEqual(result["counts"]["amp"], 2)
        self.assertEqual(result["counts"]["inh"], 1)
        self.assertEqual(result["counts"]["pass"], 0)
        self.assertEqual(result["counts"]["dead"], 1)
        self.assertEqual(result["logic"]["latch_hold"], 3)
        self.assertEqual(result["logic"]["latch_reset"], 0)
        self.assertEqual(len(result["sample"]), 4)
        top = result["sample"][0]
        self.assertIn(top["cls"], ("amp", "inh", "pass"))

    def test_decoder_sharpness_orthogonal(self):
        rows = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        result = wb_metrics.decoder_sharpness(rows)
        self.assertAlmostEqual(result["decode_orth"], 0.0)

    def test_ipc_channels(self):
        q = [[[1.0, 0.0]], [[0.0, 2.0]]]
        o = [[[1.0], [0.0]], [[0.0], [3.0]]]
        result = wb_metrics.ipc_channels(q, o, kv_norm=5.0, gqa_group=2)
        self.assertEqual(result["n_head"], 2)
        self.assertEqual(result["chan_top"][0], 1)
        self.assertAlmostEqual(result["chan_max"], 6.0)


class ExpertAndRecipeTests(unittest.TestCase):
    def test_expert_health_finds_dead(self):
        samples = {0: [1.0, -1.0, 0.5, -0.5], 1: [0.0, 0.0, 0.0, 0.0],
                   2: [0.2, -0.2, 0.1, -0.1]}
        result = wb_metrics.expert_health(samples)
        self.assertEqual(result["experts"], 3)
        self.assertEqual(result["dead"], 1)
        self.assertTrue(result["per_expert"][1]["dead"])

    def test_precision_recipe(self):
        tensors = {
            "blk.0.ffn_down.weight": {"dtype": "Q6_K", "bytes": 100},
            "blk.1.ffn_down.weight": {"dtype": "Q4_K", "bytes": 80},
            "blk.0.attn_q.weight": {"dtype": "Q4_K", "bytes": 60},
            "token_embd.weight": {"dtype": "F32", "bytes": 200},
        }
        result = wb_metrics.precision_recipe(tensors)
        ffn = result["roles"]["ffn_down"]
        self.assertEqual(ffn["dtypes"]["Q6_K"], 100)
        self.assertEqual(ffn["protected"], "Q6_K")
        self.assertEqual(result["roles"]["token_embd"]["protected"], "F32")


class AxisAnalogyConceptTests(unittest.TestCase):
    def test_axis_purity_clean(self):
        pairs = [([0.0, 1.0], [1.0, 0.05]), ([0.1, 1.0], [1.0, 0.0])]
        result = wb_metrics.axis_with_purity(pairs)
        self.assertEqual(result["verdict"], "CLEAN AXIS")
        self.assertGreater(result["purity"], 0.9)

    def test_axis_purity_noise(self):
        pairs = [([0.0, 1.0], [1.0, 0.0]), ([1.0, 0.0], [0.0, 1.0])]
        result = wb_metrics.axis_with_purity(pairs)
        self.assertEqual(result["verdict"], "NOT an axis")

    def test_pole_readout(self):
        axis = [1.0, 0.0]
        vocab = {"hot": [0.9, 0.1], "cold": [-0.9, 0.1], "stone": [0.0, 1.0]}
        result = wb_metrics.pole_readout(axis, vocab, k=2)
        self.assertEqual(result["pos_pole"][0][0], "hot")
        self.assertEqual(result["neg_pole"][0][0], "cold")

    def test_analogy_projects_sources_out(self):
        man = [1.0, 0.0, 0.0]
        king = [1.0, 1.0, 0.0]
        woman = [0.0, 1.0, 0.0]
        queen = [0.0, 1.0, 0.2]
        result = wb_metrics.analogy(man, king, woman,
                                    {"queen": queen, "king": king,
                                     "man": man, "woman": woman})
        self.assertEqual(result["answer"], "queen")

    def test_concept_neighbors_hidden_and_cross(self):
        query = [1.0, 0.0]
        vocab = {
            "water": [0.99, 0.01],
            "水": [0.95, 0.05],
            "stone": [0.0, 1.0],
        }
        result = wb_metrics.concept_neighbors(query, vocab, k=5,
                                              query_word="water")
        tokens = [n["token"] for n in result["neighbors"]]
        self.assertNotIn("water", tokens)  # the query word skips itself
        self.assertEqual(tokens[0], "水")  # nearest other row
        self.assertIn("水", tokens)
        self.assertEqual(result["cross_script"], 1)
        hidden_tokens = [h["token"] for h in result["hidden_matches"]]
        self.assertIn("水", hidden_tokens)
        self.assertNotIn("water", hidden_tokens)

    def test_neuron_cleanliness(self):
        neurons = [[1.0, 0.0], [0.5, 0.5]]
        vocab = {"fire": [0.98, 0.02], "ice": [-0.9, 0.1],
                 "stone": [0.4, 0.6]}
        result = wb_metrics.neuron_cleanliness(neurons, vocab, k=2)
        self.assertEqual(result["neurons"], 2)
        self.assertEqual(result["cleanest"][0]["neuron"], 0)
        self.assertEqual(result["cleanest"][0]["top"][0]["token"], "fire")


class ManifoldAndClusterTests(unittest.TestCase):
    def test_value_sanity(self):
        rows = [[1.0, 2.0], [float("nan"), 1.0], [1e6, 0.0], [0.5, 0.5]]
        result = wb_metrics.value_sanity(rows)
        self.assertEqual(result["insane_count"], 2)
        self.assertIn(1, result["insane_rows"])
        self.assertIn(2, result["insane_rows"])

    def test_manifold_residual_flags_outlier(self):
        rng_rows = []
        for i in range(60):
            base = math.sin(i) * 0.01
            rng_rows.append([1.0 + base, 0.1 * base, 0.05 * base])
        rng_rows[30] = [0.0, 50.0, -50.0]
        result = wb_metrics.manifold_residual(rng_rows, k=2, sample=60,
                                              iterations=6)
        self.assertIn(30, result["flagged_rows"])

    def test_category_purity(self):
        vocab = {}
        for w in ("dog", "cat"):
            vocab[w] = [1.0, 0.05]
        for w in ("red", "blue"):
            vocab[w] = [0.0, 1.0]
        cats = {"animal": ["dog", "cat"], "color": ["red", "blue"]}
        result = wb_metrics.category_purity(vocab, cats=cats)
        self.assertEqual(result["acc"], 1.0)

    def test_order_recovery(self):
        words = ["one", "two", "three"]
        rows = {"one": [1.0, 0.0], "two": [2.0, 0.0], "three": [3.0, 0.0]}
        axis = wb_metrics.unit([1.0, 0.0])
        result = wb_metrics.order_recovery(axis, rows, words)
        self.assertEqual(result["pair_accuracy"], 1.0)
        self.assertEqual(result["order"], words)

    def test_semantic_walk_and_constellations(self):
        vocab = {"a": [1.0, 0.0], "b": [0.9, 0.1], "c": [0.0, 1.0]}
        walk = wb_metrics.semantic_walk(vocab["a"], vocab, steps=2,
                                        start_label="a")
        self.assertEqual(walk["path"][0], "a")
        self.assertTrue(walk["path"][1].startswith("b("))
        groups = wb_metrics.constellations(vocab, threshold=0.5)
        self.assertIn(["a", "b"], groups["groups"])


class DepthProfileTests(unittest.TestCase):
    def test_depth_profile(self):
        per = {0: {"std": 0.1, "zero": 0.0}, 1: {"std": 0.5, "zero": 0.1},
               2: {"std": 0.2, "zero": 0.0}}
        result = wb_metrics.depth_profile(per)
        self.assertEqual(result["std_peak_layer"], 1)
        self.assertEqual(result["std_floor_layer"], 0)
        self.assertAlmostEqual(result["std_range"], 0.4)


class WiringTests(unittest.TestCase):
    """metric_op over the loopback Range server."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.cache = self.work / "cache"
        self.cache.mkdir(parents=True)

    def _serve_index(self, tensors):
        blob = build_safetensors(tensors)
        RangeHandler.payload = blob
        server = RangeServer()
        self.addCleanup(server.__exit__)
        server.__enter__()
        reader = wb_range.RangeReader(server.url, self.cache)
        index = wb_range.parse_safetensors_index(reader, "m.safetensors")
        index["url"] = server.url
        return {"schema_version": wb_range.SCHEMA_VERSION,
                "sources": [index]}

    def test_recipe_and_stats_over_ranges(self):
        payload = struct.pack("<8f", *[0.1 * i for i in range(8)])
        full_index = self._serve_index({
            "model.layers.0.mlp.down_proj.weight": ("F32", [2, 4], payload),
        })
        archive = wb_range.Archive(self.work / "archive")
        recipe = wb_range.metric_op("recipe", full_index, archive,
                                    self.cache, {})
        roles = recipe["result"]["roles"]
        self.assertIn("down_proj", roles)
        stats = wb_range.metric_op(
            "stats", full_index, archive, self.cache,
            {"tensor": "model.layers.0.mlp.down_proj.weight", "sample": 2})
        self.assertEqual(stats["status"], "ARCHIVED")
        self.assertEqual(stats["result"]["rows_sampled"], 2)
        self.assertIn("stress", stats["result"])
        self.assertIn("entropy", stats["result"])

    def test_magics_over_ranges(self):
        body = struct.pack("<4f", 0.1, 0.2, 0.3, 0.4) + b"PFCGAME1" + b"\x00" * 8
        full_index = self._serve_index({"w": ("F32", [8, 1], body[:32])})
        archive = wb_range.Archive(self.work / "archive")
        result = wb_range.metric_op("magics", full_index, archive,
                                    self.cache, {"tensor": "w",
                                                 "max_bytes": 64})
        self.assertEqual(result["result"]["hits"], 1)
        self.assertIn("PFCGAME1", result["result"]["tags"])

    def test_circuitry_over_ranges(self):
        # safetensors numpy order: n_embd = 2, n_ff = 4:
        # gate/up [n_ff, n_embd], down [n_embd, n_ff]
        gate = struct.pack("<8f", 1, 0, 1, 0, 0, 1, 0, 0)
        up = struct.pack("<8f", .9, .1, -.9, -.1, 0, 1, 1, 1)
        down = struct.pack("<8f", .5, .5, 0, 0, 0, 0, .5, 0)
        full_index = self._serve_index({
            "blk.0.ffn_gate.weight": ("F32", [4, 2], gate),
            "blk.0.ffn_up.weight": ("F32", [4, 2], up),
            "blk.0.ffn_down.weight": ("F32", [2, 4], down),
        })
        archive = wb_range.Archive(self.work / "archive")
        result = wb_range.metric_op("circuitry", full_index, archive,
                                    self.cache, {"layer": 0, "units": 4,
                                                 "band": 2})
        r = result["result"]
        self.assertEqual(r["n_ff"], 4)
        self.assertEqual(r["counts"]["amp"], 2)
        self.assertEqual(r["counts"]["inh"], 1)
        self.assertEqual(r["counts"]["dead"], 1)
        self.assertIn("decode_orth", r["logic"])
        self.assertIn("drain_conv", r["logic"])

    def test_unknown_op_rejected(self):
        full_index = self._serve_index({
            "w": ("F32", [1, 1], struct.pack("<f", 1.0))})
        archive = wb_range.Archive(self.work / "archive")
        with self.assertRaises(wb_range.WbRangeError):
            wb_range.metric_op("bogus", full_index, archive, self.cache, {})


if __name__ == "__main__":
    unittest.main()
