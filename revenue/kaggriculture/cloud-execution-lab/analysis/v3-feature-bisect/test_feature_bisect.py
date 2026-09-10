# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("feature_bisect", HERE / "feature_bisect.py")
assert SPEC and SPEC.loader
fb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fb)

BASE_CONFIG = {
    "consumer": "frozen",
    "seed": True,
    "funding": True,
    "terminal_route": False,
    "committed": True,
    "budget_seconds": 1.0,
    "reserve_seconds": 0.01,
    "terminal_history": False,
    "redundant_hire": True,
    "fourth_quadrant": False,
    "market_pressure": True,
    "committed_seed_retry": False,
    "operating_stock": True,
    "idle_fertilizer": True,
    "crop_release": True,
    "early_capital": True,
}


def archive_bytes(
    members: dict[str, bytes],
    *,
    symlink: tuple[str, str] | None = None,
    duplicate: str | None = None,
) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(data))
            if duplicate is not None:
                data = members[duplicate]
                info = tarfile.TarInfo(duplicate)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(data))
            if symlink is not None:
                info = tarfile.TarInfo(symlink[0])
                info.type = tarfile.SYMTYPE
                info.linkname = symlink[1]
                archive.addfile(info)
    return output.getvalue()


def write_archive(
    path: Path,
    config: dict | None = None,
    *,
    marker: bytes = b"baseline",
    extras: dict[str, bytes] | None = None,
) -> str:
    config = dict(BASE_CONFIG if config is None else config)
    members = {
        "main.py": b"def agent(observation, configuration=None):\n    return {'farmer':['PASS'],'hands':[],'market':[]}\n",
        "TITAN-CONFIG.json": (json.dumps(config, indent=2) + "\n").encode(),
        "dependency.py": b"MARKER = " + repr(marker).encode() + b"\n",
        "nested/data.txt": b"unchanged\n",
    }
    if extras:
        members.update(extras)
    data = archive_bytes(members)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def make_prepare_args(
    tmp: Path,
    *,
    controls: list[str] | None = None,
    pairs: list[str] | None = None,
    toggles: list[str] | None = None,
) -> argparse.Namespace:
    archive = tmp / "current.tar.gz"
    digest = write_archive(archive)
    return argparse.Namespace(
        output_dir=tmp / "matrix",
        baseline=f"current={archive}@{digest}",
        control=controls or [],
        toggle=toggles if toggles is not None else ["early_capital", "operating_stock"],
        pair=pairs if pairs is not None else ["early_capital,operating_stock"],
        variant=[],
    )


def make_evaluator_report(
    candidate: Path,
    opponents: list[str],
    seeds: list[int],
    *,
    mode: str,
    engine_ref: str = "engine",
) -> dict:
    config = json.loads((candidate.parent / "TITAN-CONFIG.json").read_text())
    games = []
    for opponent in opponents:
        for seed in seeds:
            for seat in (0, 1):
                if mode == "positive":
                    own = 90.0 if config["early_capital"] else 120.0
                    rival = 100.0
                elif mode == "interaction":
                    off_a = not config["early_capital"]
                    off_b = not config["operating_stock"]
                    own = 100.0 + 2 * off_a + 3 * off_b + 7 * (off_a and off_b)
                    rival = 100.0
                else:
                    own = rival = 100.0
                scores = [own, rival] if seat == 0 else [rival, own]
                trace = hashlib.sha256(f"{config}|{opponent}|{seed}|{seat}".encode()).hexdigest()
                games.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "scores": scores,
                        "failure": None,
                        "trace_sha256": trace,
                        "wall_seconds": 0.1,
                        "actors": [{"max_call_seconds": 0.001}, {"max_call_seconds": 0.001}],
                    }
                )
    candidate_sha = fb.sha256_file(candidate)
    opponent_map = {
        name: {"entry": name, "sha256": hashlib.sha256(name.encode()).hexdigest()}
        for name in opponents
    }
    first = games[0]
    return {
        "schema_version": 1,
        "engine_ref": engine_ref,
        "engine_sha256": {"engine.py": hashlib.sha256(engine_ref.encode()).hexdigest()},
        "loader_sha256": "1" * 64,
        "evaluator_sha256": "2" * 64,
        "candidate": {"entry": "main.py", "callable": "agent", "sha256": candidate_sha},
        "opponents": opponent_map,
        "seeds": seeds,
        "agent_rng_seed": 20260907,
        "limits": {"action_rpc_seconds": 1.0},
        "games": games,
        "reproducibility": {
            "checked": True,
            "same_trace_and_scores": True,
            "original_trace": first["trace_sha256"],
            "replay_trace": first["trace_sha256"],
        },
    }


def create_runs(matrix_path: Path, results: Path, *, mode: str = "positive", mutate=None) -> Path:
    matrix = json.loads(matrix_path.read_text())
    results.mkdir()
    run_rows = {}
    opponents = ["arlene"]
    seeds = [11, 13]
    for item in matrix["variants"]:
        candidate = matrix_path.parent / item["root"] / "main.py"
        report = make_evaluator_report(candidate, opponents, seeds, mode=mode)
        if mutate:
            mutate(item["name"], report)
        report_path = results / f"{item['name']}.report.json"
        report_path.write_bytes(fb.pretty_bytes(report))
        run_rows[item["name"]] = {
            "exit_code": 0,
            "report": report_path.name,
            "report_sha256": fb.sha256_file(report_path),
        }
    runs = fb.seal_payload(
        {
            "schema_version": 1,
            "matrix": os.path.relpath(matrix_path, results),
            "matrix_sha256": matrix["matrix_sha256"],
            "contract": {},
            "contract_sha256": "3" * 64,
            "variants": run_rows,
            "all_evaluators_succeeded": True,
            "truth_boundary": "test",
        },
        field="run_sha256",
    )
    path = results / "runs.json"
    path.write_bytes(fb.pretty_bytes(runs))
    return path


class ArchiveSafetyTests(unittest.TestCase):
    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.tar.gz"
            path.write_bytes(
                archive_bytes(
                    {
                        "main.py": b"pass\n",
                        "TITAN-CONFIG.json": b"{}\n",
                        "../escape": b"x",
                    }
                )
            )
            with self.assertRaisesRegex(fb.EvidenceError, "unsafe archive member"):
                fb.read_archive(path)

    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.tar.gz"
            path.write_bytes(
                archive_bytes(
                    {"main.py": b"pass\n", "TITAN-CONFIG.json": b"{}\n"},
                    symlink=("link", "main.py"),
                )
            )
            with self.assertRaisesRegex(fb.EvidenceError, "non-regular"):
                fb.read_archive(path)

    def test_rejects_duplicate_member(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.tar.gz"
            path.write_bytes(
                archive_bytes(
                    {"main.py": b"pass\n", "TITAN-CONFIG.json": b"{}\n"},
                    duplicate="main.py",
                )
            )
            with self.assertRaisesRegex(fb.EvidenceError, "duplicate member"):
                fb.read_archive(path)

    def test_rejects_wrong_archive_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent.tar.gz"
            write_archive(path)
            with self.assertRaisesRegex(fb.EvidenceError, "SHA-256 mismatch"):
                fb.read_archive(path, "0" * 64)


class MatrixTests(unittest.TestCase):
    def test_config_only_singles_and_pair(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args = make_prepare_args(tmp)
            self.assertEqual(fb.prepare_matrix(args), 0)
            matrix, root = fb.load_matrix(args.output_dir / "matrix.json")
            self.assertEqual(
                [item["name"] for item in matrix["variants"]],
                [
                    "current",
                    "without-early-capital",
                    "without-operating-stock",
                    "without-early-capital+operating-stock",
                ],
            )
            baseline = json.loads((root / "manifests/current.json").read_text())
            for item in matrix["variants"][1:]:
                manifest = json.loads((root / item["manifest"]).read_text())
                self.assertEqual(manifest["changed_members"], ["TITAN-CONFIG.json"])
                self.assertEqual(manifest["non_config_tree_sha256"], baseline["non_config_tree_sha256"])
                self.assertEqual(
                    manifest["member_sha256"]["dependency.py"],
                    baseline["member_sha256"]["dependency.py"],
                )

    def test_unknown_toggle_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args = make_prepare_args(tmp, toggles=["does_not_exist"], pairs=[])
            with self.assertRaisesRegex(fb.EvidenceError, "unknown toggle"):
                fb.prepare_matrix(args)

    def test_disabled_toggle_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            archive = tmp / "current.tar.gz"
            config = dict(BASE_CONFIG)
            config["early_capital"] = False
            digest = write_archive(archive, config)
            args = argparse.Namespace(
                output_dir=tmp / "matrix",
                baseline=f"current={archive}@{digest}",
                control=[],
                toggle=["early_capital"],
                pair=[],
                variant=[],
            )
            with self.assertRaisesRegex(fb.EvidenceError, "not enabled"):
                fb.prepare_matrix(args)

    def test_control_archive_is_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            current = tmp / "current.tar.gz"
            current_sha = write_archive(current, marker=b"current")
            control_tmp = tmp / "control.tmp.tar.gz"
            control_sha = write_archive(control_tmp, marker=b"control")
            control = tmp / f"titan-{control_sha}.tar.gz"
            control_tmp.rename(control)
            args = argparse.Namespace(
                output_dir=tmp / "matrix",
                baseline=f"current={current}@{current_sha}",
                control=[f"submitted-v2={control}"],
                toggle=["early_capital"],
                pair=[],
                variant=[],
            )
            self.assertEqual(fb.prepare_matrix(args), 0)
            matrix, root = fb.load_matrix(args.output_dir / "matrix.json")
            self.assertEqual(matrix["controls"], ["submitted-v2"])
            by_name = {item["name"]: item for item in matrix["variants"]}
            self.assertNotEqual(
                by_name["current"]["candidate_tree_sha256"],
                by_name["submitted-v2"]["candidate_tree_sha256"],
            )
            self.assertEqual(
                (root / "variants/submitted-v2/dependency.py").read_bytes(),
                b"MARKER = b'control'\n",
            )

    def test_candidate_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            args = make_prepare_args(tmp, toggles=["early_capital"], pairs=[])
            fb.prepare_matrix(args)
            target = args.output_dir / "variants/current/dependency.py"
            target.chmod(0o644)
            target.write_text("tampered\n")
            with self.assertRaisesRegex(fb.EvidenceError, "candidate member hash mismatch"):
                fb.load_matrix(args.output_dir / "matrix.json")

    def test_sealed_artifact_tamper_is_detected(self):
        payload = fb.seal_payload({"schema_version": 1, "value": 7}, field="matrix_sha256")
        fb.verify_sealed(payload, "matrix_sha256")
        payload["value"] = 8
        with self.assertRaisesRegex(fb.EvidenceError, "mismatch"):
            fb.verify_sealed(payload, "matrix_sha256")


class AnalysisTests(unittest.TestCase):
    def _prepare(self, tmp: Path, *, pairs=None) -> Path:
        args = make_prepare_args(
            tmp,
            toggles=["early_capital", "operating_stock"],
            pairs=[] if pairs is None else pairs,
        )
        fb.prepare_matrix(args)
        return args.output_dir / "matrix.json"

    def test_positive_single_ablation_is_nominated(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)
            runs = create_runs(matrix, tmp / "results", mode="positive")
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "analysis.json",
                markdown=tmp / "analysis.md",
                overwrite=False,
            )
            self.assertEqual(fb.analyze_runs(args), 0)
            result = json.loads(args.output.read_text())
            self.assertEqual(result["decision"], "ESCALATE_FULL_PANEL")
            self.assertIn("without-early-capital", result["full_panel_candidates"])
            row = result["comparisons"]["without-early-capital"]
            self.assertEqual(row["delta"]["wins"], 4)
            self.assertEqual(row["delta"]["losses"], -4)
            self.assertEqual(row["screen"], "ESCALATE_FULL_PANEL")
            self.assertIn("Full-panel nominees", args.markdown.read_text())

    def test_missing_cell_is_rejected_not_ranked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)

            def mutate(name, report):
                if name == "without-early-capital":
                    report["games"].pop()

            runs = create_runs(matrix, tmp / "results", mutate=mutate)
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "a.json",
                markdown=None,
                overwrite=False,
            )
            with self.assertRaisesRegex(fb.EvidenceError, "missing cells"):
                fb.analyze_runs(args)

    def test_duplicate_cell_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)

            def mutate(name, report):
                if name == "without-early-capital":
                    report["games"].append(dict(report["games"][0]))

            runs = create_runs(matrix, tmp / "results", mutate=mutate)
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "a.json",
                markdown=None,
                overwrite=False,
            )
            with self.assertRaisesRegex(fb.EvidenceError, "duplicate cell"):
                fb.analyze_runs(args)

    def test_failed_cell_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)

            def mutate(name, report):
                if name == "without-early-capital":
                    report["games"][0]["status"] = "failed"
                    report["games"][0]["failure"] = {"kind": "timeout"}

            runs = create_runs(matrix, tmp / "results", mutate=mutate)
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "a.json",
                markdown=None,
                overwrite=False,
            )
            with self.assertRaisesRegex(fb.EvidenceError, "incomplete cell"):
                fb.analyze_runs(args)

    def test_engine_identity_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)

            def mutate(name, report):
                if name == "without-operating-stock":
                    report["engine_ref"] = "other-engine"

            runs = create_runs(matrix, tmp / "results", mutate=mutate)
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "a.json",
                markdown=None,
                overwrite=False,
            )
            with self.assertRaisesRegex(fb.EvidenceError, "identity drift"):
                fb.analyze_runs(args)

    def test_candidate_report_swap_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)

            def mutate(name, report):
                if name == "without-early-capital":
                    report["candidate"]["sha256"] = "f" * 64

            runs = create_runs(matrix, tmp / "results", mutate=mutate)
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "a.json",
                markdown=None,
                overwrite=False,
            )
            with self.assertRaisesRegex(fb.EvidenceError, "candidate identity mismatch"):
                fb.analyze_runs(args)

    def test_pair_interaction_is_exact(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp, pairs=["early_capital,operating_stock"])
            runs = create_runs(matrix, tmp / "results", mode="interaction")
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "analysis.json",
                markdown=None,
                overwrite=False,
            )
            fb.analyze_runs(args)
            result = json.loads(args.output.read_text())
            self.assertEqual(len(result["pair_interactions"]), 1)
            self.assertEqual(
                result["pair_interactions"][0]["mean_margin_interaction"],
                7.0,
            )

    def test_partial_grid_simpson_trap_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            matrix = self._prepare(tmp)

            def mutate(name, report):
                if name == "without-early-capital":
                    report["games"] = [
                        game for game in report["games"] if game["candidate_seat"] == 0
                    ]

            runs = create_runs(matrix, tmp / "results", mutate=mutate)
            args = argparse.Namespace(
                runs=runs,
                baseline=None,
                output=tmp / "a.json",
                markdown=None,
                overwrite=False,
            )
            with self.assertRaisesRegex(fb.EvidenceError, "missing cells"):
                fb.analyze_runs(args)


FAKE_EVALUATOR = r"""#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--engine-dir')
p.add_argument('--candidate')
p.add_argument('--seeds')
p.add_argument('--rng-seed', type=int)
p.add_argument('--action-timeout', type=float)
p.add_argument('--startup-timeout', type=float)
p.add_argument('--game-timeout', type=float)
p.add_argument('--output')
p.add_argument('--recheck-first', action='store_true')
p.add_argument('--loader')
p.add_argument('--episode-steps')
p.add_argument('--opponent', action='append', default=[])
a = p.parse_args()
source = Path(a.candidate)
config = json.loads((source.parent / 'TITAN-CONFIG.json').read_text())
counter = Path(__file__).with_suffix('.count')
counter.write_text(str(int(counter.read_text()) + 1) if counter.exists() else '1')
seeds = [int(x) for x in a.seeds.split(',')]
opponents = {}
for value in a.opponent:
    label, spec = value.split('=', 1)
    opponents[label] = {'entry': spec, 'sha256': hashlib.sha256(spec.encode()).hexdigest()}
games = []
for opponent in opponents:
    for seed in seeds:
        for seat in (0, 1):
            own = 90.0 if config['early_capital'] else 120.0
            rival = 100.0
            scores = [own, rival] if seat == 0 else [rival, own]
            trace = hashlib.sha256(f'{config}|{opponent}|{seed}|{seat}'.encode()).hexdigest()
            games.append({
                'opponent': opponent,
                'seed': seed,
                'candidate_seat': seat,
                'status': 'complete',
                'scores': scores,
                'failure': None,
                'trace_sha256': trace,
                'wall_seconds': 0.01,
                'actors': [{'max_call_seconds': 0.001}, {'max_call_seconds': 0.001}],
            })
report = {
    'schema_version': 1,
    'engine_ref': 'fake-engine',
    'engine_sha256': {'engine.py': 'a' * 64},
    'loader_sha256': 'b' * 64,
    'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'candidate': {
        'entry': 'main.py',
        'callable': 'agent',
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    },
    'opponents': opponents,
    'seeds': seeds,
    'agent_rng_seed': a.rng_seed,
    'limits': {'action_rpc_seconds': a.action_timeout},
    'games': games,
    'reproducibility': {
        'checked': True,
        'same_trace_and_scores': True,
        'original_trace': games[0]['trace_sha256'],
        'replay_trace': games[0]['trace_sha256'],
    },
}
Path(a.output).write_text(json.dumps(report, indent=2) + '\n')
"""


class RunTests(unittest.TestCase):
    def test_runner_hash_binds_and_resumes(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            prepare = make_prepare_args(tmp, toggles=["early_capital"], pairs=[])
            fb.prepare_matrix(prepare)
            evaluator = tmp / "fake_eval.py"
            evaluator.write_text(FAKE_EVALUATOR)
            evaluator.chmod(evaluator.stat().st_mode | stat.S_IXUSR)
            engine = tmp / "engine"
            engine.mkdir()
            (engine / "engine.py").write_text("# fixed\n")
            opponent = tmp / "opponent.py"
            opponent.write_text("def agent(obs, cfg=None): return {}\n")
            run_args = argparse.Namespace(
                matrix=prepare.output_dir / "matrix.json",
                evaluator=evaluator,
                engine_dir=engine,
                loader=None,
                opponent=[f"arlene={opponent}::agent"],
                seeds="11,13",
                rng_seed=20260907,
                action_timeout=1.0,
                startup_timeout=10.0,
                game_timeout=120.0,
                process_timeout=30.0,
                episode_steps=None,
                results_dir=tmp / "results",
                no_resume=False,
            )
            self.assertEqual(fb.run_matrix(run_args), 0)
            first_count = int(evaluator.with_suffix(".count").read_text())
            self.assertEqual(first_count, 2)
            self.assertEqual(fb.run_matrix(run_args), 0)
            self.assertEqual(int(evaluator.with_suffix(".count").read_text()), first_count)
            runs = json.loads((run_args.results_dir / "runs.json").read_text())
            self.assertTrue(all(row["reused"] for row in runs["variants"].values()))
            analyze = argparse.Namespace(
                runs=run_args.results_dir / "runs.json",
                baseline=None,
                output=tmp / "analysis.json",
                markdown=tmp / "analysis.md",
                overwrite=False,
            )
            self.assertEqual(fb.analyze_runs(analyze), 0)
            result = json.loads(analyze.output.read_text())
            self.assertEqual(result["full_panel_candidates"], ["without-early-capital"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
