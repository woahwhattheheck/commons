from __future__ import annotations

import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

import feature_reachability as fr


class FeatureReachabilityTests(unittest.TestCase):
    def test_variants_are_control_plus_one_drop_each(self):
        rows = fr.variant_specs(("a", "b", "c"))
        self.assertEqual([row["name"] for row in rows], ["all_enabled", "without_a", "without_b", "without_c"])
        self.assertEqual([row["disabled"] for row in rows], [None, "a", "b", "c"])

    def test_config_requires_boolean_enabled_baseline(self):
        self.assertEqual(fr.validate_config({"a": True}, ("a",)), {"a": True})
        with self.assertRaises(ValueError):
            fr.validate_config({"a": False}, ("a",))
        with self.assertRaises(TypeError):
            fr.validate_config({"a": 1}, ("a",))

    def test_source_reference_scan_binds_features_and_excludes_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text(
                "from dataclasses import dataclass\n"
                "@dataclass\n"
                "class Features:\n"
                "    seed: bool = True\n"
                "def use(self, f, config):\n"
                "    return self.features.seed and f.seed and config.get('funding', True) and getattr(self.features, 'early_capital', False)\n",
                encoding="utf-8",
            )
            (root / "checks").mkdir()
            (root / "checks" / "test_seed.py").write_text('config["seed"]\n', encoding="utf-8")
            refs = fr.find_config_references(root, ("seed", "funding", "early_capital", "crop_release"))
            self.assertEqual({row["kind"] for row in refs["seed"]}, {"Features declaration", "attribute access"})
            self.assertEqual(len(refs["seed"]), 2)
            self.assertEqual(len(refs["funding"]), 1)
            self.assertEqual(refs["funding"][0]["kind"], "mapping get")
            self.assertEqual(len(refs["early_capital"]), 1)
            self.assertEqual(refs["early_capital"][0]["kind"], "getattr access")
            self.assertEqual(refs["crop_release"], [])
            self.assertEqual(
                fr.runtime_access_factors(refs, ("seed", "funding", "early_capital", "crop_release")),
                ["seed", "funding", "early_capital"],
            )

    def test_exact_feature_forms_all_have_runtime_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            declarations = "\n".join(f"    {name}: bool = True" for name in fr.FACTORS)
            (root / "titan_runtime.py").write_text(
                "from dataclasses import dataclass\n"
                "@dataclass\n"
                "class Features:\n" + declarations + "\n"
                "def use(self, f):\n"
                "    return (self.features.seed and self.features.funding and "
                "self.features.redundant_hire and self.features.market_pressure and "
                "self.features.operating_stock and self.features.crop_release and "
                "f.idle_fertilizer and getattr(self.features, 'early_capital', False))\n",
                encoding="utf-8",
            )
            refs = fr.find_config_references(root)
            self.assertEqual(fr.runtime_access_factors(refs), list(fr.FACTORS))

    def test_declaration_alone_is_not_runtime_reachability(self):
        refs = {
            "seed": [{"kind": "Features declaration"}],
            "funding": [{"kind": "Features declaration"}, {"kind": "attribute access"}],
        }
        self.assertEqual(fr.runtime_access_factors(refs, ("seed", "funding")), ["funding"])

    def test_materialization_changes_exactly_one_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, out = root / "base", root / "out"
            base.mkdir()
            (base / "main.py").write_text("def agent(obs, cfg): return {}\n", encoding="utf-8")
            (base / "TITAN-CONFIG.json").write_text(json.dumps({"a": True, "b": True, "fixed": 7}), encoding="utf-8")
            rows, config = fr.materialize_variants(base, out, ("a", "b"))
            self.assertEqual(config["fixed"], 7)
            for row in rows:
                built = json.loads((out / row["name"] / "TITAN-CONFIG.json").read_text())
                changed = [name for name in ("a", "b") if built[name] != config[name]]
                self.assertEqual(changed, [] if row["disabled"] is None else [row["disabled"]])
                self.assertEqual(built["fixed"], 7)

    def test_safe_extract_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo("../escape")
                data = b"x"
                info.size = len(data)
                bundle.addfile(info, io.BytesIO(data))
            with self.assertRaises(ValueError):
                fr.safe_extract(archive, root / "out")

    def _game(self, variant, seat, trace, scores):
        return {
            "variant": variant,
            "opponent": "arlene",
            "seed": 7,
            "candidate_seat": seat,
            "status": "complete",
            "failure": None,
            "scores": scores,
            "steps": 9,
            "episode_steps": 10,
            "trace_sha256": trace * 64,
            "actors": [{"calls": 10}, {"calls": 10}],
        }

    def test_summary_classifies_drop_keep_and_inert(self):
        games = []
        for seat in (0, 1):
            games.append(self._game("all_enabled", seat, "a", [100, 50] if seat == 0 else [50, 100]))
            games.append(self._game("without_drop", seat, "b", [110, 50] if seat == 0 else [50, 110]))
            games.append(self._game("without_keep", seat, "c", [90, 50] if seat == 0 else [50, 90]))
            games.append(self._game("without_inert", seat, "a", [100, 50] if seat == 0 else [50, 100]))
        variants = fr.variant_specs(("drop", "keep", "inert"))
        fr.validate_games(games, variants, ["arlene"], [7])
        summary = fr.summarize(games, ("drop", "keep", "inert"), {name: [] for name in ("drop", "keep", "inert")})
        self.assertEqual(summary["factor_results"]["drop"]["classification"], "investigate_disable")
        self.assertEqual(summary["factor_results"]["keep"]["classification"], "retain_enabled")
        self.assertEqual(summary["factor_results"]["inert"]["classification"], "panel_inert")
        self.assertEqual(summary["observed_agent_calls"], 160)

    def test_hard_call_bound(self):
        self.assertEqual(fr.max_scheduled_agent_calls(19, 720), 27360)
        with self.assertRaises(ValueError):
            fr.max_scheduled_agent_calls(0, 720)

    def test_validate_games_rejects_missing_cell(self):
        games = [self._game("all_enabled", 0, "a", [1, 0])]
        with self.assertRaises(AssertionError):
            fr.validate_games(games, fr.variant_specs(("a",)), ["arlene"], [7])


if __name__ == "__main__":
    unittest.main()
