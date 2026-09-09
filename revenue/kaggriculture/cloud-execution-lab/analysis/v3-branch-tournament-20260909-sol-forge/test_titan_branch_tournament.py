#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import titan_branch_tournament as tournament

ENGINE_REF = "a" * 40
PROJECT = "lab"
RECEIPT = "runtime/integrated-selected/CURRENT-ARCHIVE.json"
MANIFEST = "runtime/integrated-selected/CURRENT-SOURCE.json"


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> bytes:
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def deterministic_tar(files: dict[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name in sorted(files):
                data = files[name]
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                archive.addfile(info, io.BytesIO(data))
    return raw.getvalue()


FAKE_EVALUATOR = r'''#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, re, sys
ENGINE_REF = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
def h(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
p = argparse.ArgumentParser()
p.add_argument("--engine-dir", required=True)
p.add_argument("--loader", required=True)
p.add_argument("--candidate", required=True)
p.add_argument("--seeds", required=True)
p.add_argument("--rng-seed", type=int, required=True)
p.add_argument("--action-timeout")
p.add_argument("--startup-timeout")
p.add_argument("--game-timeout")
p.add_argument("--episode-steps", type=int)
p.add_argument("--recheck-first", action="store_true")
p.add_argument("--output", required=True)
p.add_argument("--opponent", action="append", default=[])
a = p.parse_args()
entry, _, callable_name = a.candidate.partition("::")
source = pathlib.Path(entry).read_text()
match = re.search(r"SCORE\s*=\s*(-?\d+)", source)
score = int(match.group(1)) if match else 0
seeds = [int(v) for v in a.seeds.split(",")]
opponents = {}
for item in a.opponent:
    label, spec = item.split("=", 1)
    opponents[label] = ({"entry":"official_starter", "engine_ref":ENGINE_REF}
                        if spec == "official_starter" else
                        {"entry":pathlib.Path(spec.partition("::")[0]).name,
                         "callable":spec.partition("::")[2] or "agent",
                         "sha256":h(spec.partition("::")[0])})
games = []
for label in opponents:
    for seed in seeds:
        for seat in (0, 1):
            scores = [100.0, 100.0]
            scores[seat] += score
            games.append({"opponent":label, "seed":seed, "candidate_seat":seat,
                          "status":"complete", "scores":scores, "failure":None,
                          "steps":a.episode_steps or 720, "trace_sha256":("%064x" % (seed+seat+score))[-64:]})
engine_hashes = {path.name:h(path) for path in pathlib.Path(a.engine_dir).iterdir() if path.is_file()}
report = {"schema_version":1, "engine_ref":ENGINE_REF, "engine_sha256":engine_hashes,
          "loader_sha256":h(a.loader), "evaluator_sha256":h(__file__),
          "candidate":{"entry":pathlib.Path(entry).name,
                       "callable":callable_name or "agent", "sha256":h(entry)},
          "opponents":opponents, "seeds":seeds, "agent_rng_seed":a.rng_seed,
          "summary":{}, "games":games,
          "reproducibility":({"checked":True, "same_trace_and_scores":True,
                               "original_trace":"0"*64, "replay_trace":"0"*64}
                              if a.recheck_first else None)}
pathlib.Path(a.output).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(a.output).write_text(json.dumps(report, indent=2)+"\n")
print("SUMMARY {}")
'''.encode()

FAKE_LOADER = f'ENGINE_REF = "{ENGINE_REF}"\n'.encode()


class FixtureRepo:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="titan-tournament-test-repo-")
        self.root = Path(self.temp.name)
        run_git(self.root, "init", "-b", "main")
        run_git(self.root, "config", "user.email", "test@example.invalid")
        run_git(self.root, "config", "user.name", "Tournament Test")
        (self.root / "tools").mkdir()
        (self.root / "tools/evaluate.py").write_bytes(FAKE_EVALUATOR)
        (self.root / "tools/loader.py").write_bytes(FAKE_LOADER)
        self.project = self.root / PROJECT
        self.project.mkdir()
        self.write_candidate(score=10, dependency="baseline")
        self.baseline = self.commit("baseline")

    def close(self):
        self.temp.cleanup()

    def write_candidate(self, *, score: int, dependency: str):
        files = {
            "main.py": f"from dep import VALUE\nSCORE = {score}\ndef agent(obs, cfg=None): return {{}}\n".encode(),
            "dep.py": f"VALUE = {dependency!r}\n".encode(),
            "TITAN-CONFIG.json": b"{}\n",
        }
        for name, data in files.items():
            path = self.project / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        source = {"runtime": {
            name: {"source_path": name, "sha256": sha(data), "bytes": len(data)}
            for name, data in sorted(files.items())
        }}
        source_bytes = write_json(self.project / MANIFEST, source)
        archive = deterministic_tar(files)
        archive_path = self.project / "exports/titan-current.tar.gz"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(archive)
        receipt = {
            "path": "exports/titan-current.tar.gz",
            "entrypoint": "main.py::agent",
            "config": "TITAN-CONFIG.json",
            "sha256": sha(archive),
            "bytes": len(archive),
            "runtime_files": len(files),
            "source_manifest": MANIFEST,
            "source_manifest_sha256": sha(source_bytes),
        }
        write_json(self.project / RECEIPT, receipt)

    def commit(self, message: str) -> str:
        run_git(self.root, "add", ".")
        run_git(self.root, "commit", "-m", message)
        return run_git(self.root, "rev-parse", "HEAD")

    def evaluator_spec(self, commit: str) -> dict:
        return {
            "ref": commit,
            "commit": commit,
            "path": "tools/evaluate.py",
            "sha256": sha(FAKE_EVALUATOR),
            "loader_path": "tools/loader.py",
            "loader_sha256": sha(FAKE_LOADER),
        }

    def candidate_spec(self, name: str, commit: str, role: str) -> dict:
        return {
            "name": name,
            "role": role,
            "ref": commit,
            "commit": commit,
            "project_dir": PROJECT,
            "archive_receipt": RECEIPT,
            "source_manifest": MANIFEST,
        }


class ContractTests(unittest.TestCase):
    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        with self.assertRaises(tournament.TournamentError):
            tournament.strict_json_bytes(b'{"a":1,"a":2}', "dup")
        with self.assertRaises(tournament.TournamentError):
            tournament.strict_json_bytes(b'{"a":NaN}', "nan")

    def test_safe_rel_rejects_traversal_absolute_and_backslash(self):
        for value in ("../x", "/x", "a/../../x", r"a\b"):
            with self.subTest(value=value), self.assertRaises(tournament.TournamentError):
                tournament.safe_rel(value, "path")
        self.assertEqual(tournament.safe_rel("a/b.py", "path"), "a/b.py")

    def test_ref_move_is_rejected(self):
        fixture = FixtureRepo()
        self.addCleanup(fixture.close)
        old = fixture.baseline
        fixture.write_candidate(score=11, dependency="new")
        fixture.commit("new")
        with self.assertRaisesRegex(tournament.TournamentError, "ref moved"):
            tournament.resolve_commit(fixture.root, "main", old, "candidate")

    def test_dependency_change_with_unchanged_entrypoint_is_rejected(self):
        fixture = FixtureRepo()
        self.addCleanup(fixture.close)
        # Change only an imported dependency, deliberately leaving the source
        # manifest and archive receipt stale. Entry-file-only fingerprinting
        # would miss this exact predecessor.
        entry_before = (fixture.project / "main.py").read_bytes()
        (fixture.project / "dep.py").write_text("VALUE = 'tampered'\n")
        stale = fixture.commit("stale dependency")
        self.assertEqual(entry_before, (fixture.project / "main.py").read_bytes())
        with tempfile.TemporaryDirectory() as scratch:
            with self.assertRaisesRegex(tournament.TournamentError, "source closure mismatch"):
                tournament.prepare_candidate(
                    fixture.root,
                    fixture.candidate_spec("stale", stale, "baseline"),
                    Path(scratch), 0)

    def test_archive_traversal_and_duplicate_member_are_rejected(self):
        runtime = {"main.py": {"sha256": sha(b"x"), "bytes": 1}}
        for mode in ("traversal", "duplicate"):
            raw = io.BytesIO()
            with tarfile.open(fileobj=raw, mode="w") as archive:
                names = ["../escape"] if mode == "traversal" else ["main.py", "main.py"]
                for name in names:
                    info = tarfile.TarInfo(name)
                    info.size = 1
                    archive.addfile(info, io.BytesIO(b"x"))
            with tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / "out"
                with self.subTest(mode=mode), self.assertRaises(tournament.TournamentError):
                    tournament.verify_extract_archive(raw.getvalue(), runtime, destination, mode)

    def test_bootstrap_is_deterministic_and_groups_both_seats(self):
        low1, high1 = tournament.bootstrap_interval([4.0, 4.0, 4.0], samples=500,
                                                    confidence=0.95, seed=7)
        low2, high2 = tournament.bootstrap_interval([4.0, 4.0, 4.0], samples=500,
                                                    confidence=0.95, seed=7)
        self.assertEqual((low1, high1), (4.0, 4.0))
        self.assertEqual((low1, high1), (low2, high2))


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.fixture = FixtureRepo()
        self.addCleanup(self.fixture.close)
        self.fixture.write_candidate(score=15, dependency="challenger")
        self.challenger = self.fixture.commit("challenger")
        self.engine_temp = tempfile.TemporaryDirectory(prefix="titan-engine-")
        self.addCleanup(self.engine_temp.cleanup)
        self.engine_dir = Path(self.engine_temp.name)
        (self.engine_dir / "engine.py").write_bytes(b"pinned engine\n")
        self.output_temp = tempfile.TemporaryDirectory(prefix="titan-output-parent-")
        self.addCleanup(self.output_temp.cleanup)
        self.output = Path(self.output_temp.name) / "result"
        self.manifest_path = Path(self.output_temp.name) / "manifest.json"
        manifest = {
            "schema_version": 1,
            "tournament_id": "unit-tournament",
            "evaluator": self.fixture.evaluator_spec(self.challenger),
            "engine_ref": ENGINE_REF,
            "engine_sha256": {"engine.py": sha(b"pinned engine\n")},
            "seeds": [11, 17],
            "rng_seed": 99,
            "recheck_first": True,
            "limits": {"action_timeout": 1.0, "startup_timeout": 2.0,
                       "game_timeout": 3.0, "episode_steps": 8},
            "process_timeout_seconds": 30,
            "opponents": [{"label": "starter", "kind": "official_starter"}],
            "baseline": "baseline",
            "candidates": [
                self.fixture.candidate_spec("baseline", self.fixture.baseline, "baseline"),
                self.fixture.candidate_spec("challenger", self.challenger, "challenger"),
            ],
            "ranking": {"bootstrap_samples": 500, "confidence": 0.95,
                        "bootstrap_seed": 5, "min_mean_delta": 0,
                        "min_ci_lower_delta": 0, "min_worst_opponent_delta": 0},
        }
        write_json(self.manifest_path, manifest)

    def run_once(self):
        return tournament.run_tournament(self.manifest_path, self.fixture.root,
                                         self.engine_dir, self.output)

    def test_complete_tournament_selects_stronger_dependency_closed_candidate(self):
        report, valid = self.run_once()
        self.assertTrue(valid)
        self.assertEqual(report["champion"], "challenger")
        self.assertTrue(report["promotable_challenger"])
        challenger = next(row for row in report["ranking"] if row["name"] == "challenger")
        self.assertEqual(challenger["decision"], "ADVANCE")
        self.assertEqual(challenger["paired_vs_baseline"]["mean_margin_delta"], 5.0)
        self.assertEqual(challenger["paired_vs_baseline"]["bootstrap_ci"], [5.0, 5.0])
        verified = tournament.verify_output(self.output)
        self.assertEqual(verified["champion"], "challenger")

    def test_output_verifier_detects_candidate_report_tamper(self):
        self.run_once()
        report_path = self.output / "candidate-reports/challenger.json"
        report_path.write_bytes(report_path.read_bytes() + b" ")
        with self.assertRaisesRegex(tournament.TournamentError, "report digest/size mismatch"):
            tournament.verify_output(self.output)

    def test_incomplete_candidate_is_not_survivor_averaged_into_advance(self):
        self.run_once()
        data = json.loads((self.output / "candidate-reports/challenger.json").read_text())
        data["games"][0]["status"] = "failed"
        data["games"][0]["scores"] = None
        data["games"][0]["failure"] = {"kind": "timeout", "seat": 0}
        # Validate the ranking contract directly with an otherwise intact grid.
        # The shipped tournament itself was complete; exercise describe_execution
        # with a failed cell and prove no admitted mean is emitted.
        with tempfile.TemporaryDirectory() as temp:
            bundle = tournament.CandidateBundle(
                name="bad", commit="b"*40, ref="b"*40, role="challenger",
                bundle_root=Path(temp), entry_path=Path(temp)/"main.py", callable_name="agent",
                archive_sha256="1"*64, archive_bytes=1, source_manifest_sha256="2"*64,
                source_manifest_bytes=1, receipt_sha256="3"*64, receipt_bytes=1,
                runtime_tree_sha256="4"*64, runtime_files=1, entry_sha256="5"*64)
            cells = {}
            for game in data["games"]:
                cells[(game["opponent"], game["seed"], game["candidate_seat"])] = game
            execution = tournament.CandidateExecution(
                bundle=bundle, report_path=None, stdout_path=Path(temp)/"out",
                stderr_path=Path(temp)/"err", returncode=2, wall_seconds=0,
                report_sha256=None, report_bytes=None, stdout_sha256="0"*64,
                stderr_sha256="0"*64, cells=cells, integrity_error=None)
            description = tournament.describe_execution(
                execution, {("starter", seed, seat) for seed in (11,17) for seat in (0,1)})
            self.assertFalse(description["complete_grid"])
            self.assertIsNone(description["mean_margin"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
