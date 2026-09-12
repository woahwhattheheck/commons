#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import re
import subprocess

BASE = "f9ce7bc96c2fdc040bd63e5ff66d1cef14fe2cee"
BRANCH = "astra/v5-v31-v4-gauntlet-reducer-20260912"
ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
DIR = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/archive-version-bridge"
REDUCER = DIR / "reduce_gauntlet.py"
TEST = DIR / "test_reduce_gauntlet.py"
README = DIR / "README.md"
CANONICAL_MANIFEST = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/gauntlet-top30-union/manifest.json"
CANONICAL_MATERIALIZER = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/gauntlet-top30-union/corpus.py"
EXPECTED_MANIFEST_SHA256 = "510ca5c5438fb65d29755f2009f07bb85bbf3e8963054b88c4abe3ec3737924e"
EXPECTED_MATERIALIZER_BLOB = "2384453aa3b3bbab3a299ca2aa693dd6215276ae"
TRANSIENT = {
    ".github/workflows/titan-v5-gauntlet-canonical-universe-one-shot.yml",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v5/archive-version-bridge/apply_canonical_universe_v4.py",
}


def run(*args: str) -> str:
    return subprocess.check_output(list(args), cwd=ROOT, text=True)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one regex match, found {count}")
    return updated


def git_blob_id(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


if subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT).returncode:
    raise SystemExit("claimed #13415 source head is no longer an ancestor")
if hashlib.sha256(CANONICAL_MANIFEST.read_bytes()).hexdigest() != EXPECTED_MANIFEST_SHA256:
    raise SystemExit("canonical gauntlet manifest moved; re-audit instead of auto-rebinding")
if git_blob_id(CANONICAL_MATERIALIZER) != EXPECTED_MATERIALIZER_BLOB:
    raise SystemExit("canonical gauntlet materializer moved; re-audit instead of auto-rebinding")

text = REDUCER.read_text(encoding="utf-8")
text = replace_once(
    text,
    'import sys\nimport uuid\n',
    'import sys\nimport tempfile\nimport uuid\n',
    "tempfile import",
)
text = replace_once(
    text,
    'SCHEMA = "titan.v5.v31-v4-gauntlet-reduction/v3"',
    'SCHEMA = "titan.v5.v31-v4-gauntlet-reduction/v4"',
    "reducer schema",
)
text = replace_once(
    text,
    '''EXACT = {\n    "v31": "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361",\n    "v4": "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b",\n}\n_CELL_RE = re.compile''',
    '''EXACT = {\n    "v31": "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361",\n    "v4": "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b",\n}\nCANONICAL_MANIFEST_SHA256 = "510ca5c5438fb65d29755f2009f07bb85bbf3e8963054b88c4abe3ec3737924e"\nCANONICAL_MATERIALIZER_GIT_BLOB = "2384453aa3b3bbab3a299ca2aa693dd6215276ae"\nCANONICAL_UNIQUE_SUBMISSIONS = 41\nCANONICAL_FIXTURE_COUNT = 123\nCANONICAL_REPLAYS_PER_SUBMISSION = 3\nCANONICAL_MANIFEST_SCHEMA = "titan.gauntlet.top30-union.v1"\nCANONICAL_INDEX_SCHEMA = "titan.gauntlet.recorded-opponents.v1"\nCANONICAL_PROVENANCE = "public_recorded_actions"\nCANONICAL_INTERPRETATION = (\n    "Counterfactual recorded-action opponent; seat swap or new seed is a synthetic stress case."\n)\nCANONICAL_PACKAGE = Path(__file__).resolve().parent.parent / "gauntlet-top30-union"\nCANONICAL_MANIFEST_PATH = CANONICAL_PACKAGE / "manifest.json"\nCANONICAL_MATERIALIZER_PATH = CANONICAL_PACKAGE / "corpus.py"\n_CELL_RE = re.compile''',
    "canonical authority constants",
)

authority_block = r'''
def _git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def _captured_materializer():
    raw = _read_regular_bytes(CANONICAL_MATERIALIZER_PATH)
    actual = _git_blob_id(raw)
    if actual != CANONICAL_MATERIALIZER_GIT_BLOB:
        raise ReductionError(
            "canonical corpus materializer Git blob drifted: "
            f"{actual} != {CANONICAL_MATERIALIZER_GIT_BLOB}"
        )
    namespace: dict[str, Any] = {
        "__name__": "_titan_v5_gauntlet_corpus_authority",
        "__file__": str(CANONICAL_MATERIALIZER_PATH),
    }
    try:
        exec(
            compile(raw, str(CANONICAL_MATERIALIZER_PATH), "exec"),
            namespace,
        )
    except Exception as exc:
        raise ReductionError(
            f"cannot load captured canonical materializer: {exc}"
        ) from exc
    materialize = namespace.get("materialize")
    if not callable(materialize):
        raise ReductionError("canonical corpus materializer lacks materialize()")
    return materialize


def _runtime_row_projection(
    row: Any,
    source_pos: int,
) -> dict[str, Any]:
    if type(row) is not dict:
        raise ReductionError(
            f"index opponent {source_pos} must be an object"
        )
    required = {
        "id",
        "kind",
        "provenance",
        "executable",
        "family",
        "submission_id",
        "team_id",
        "team_name",
        "memberships",
        "episode_id",
        "seed",
        "recorded_opponent_seat",
        "candidate_seat_for_recorded_orientation",
        "entry",
        "entry_sha256",
        "actions_sha256",
        "replay_sha256",
        "decisions",
        "adaptive",
        "interpretation",
    }
    if set(row) != required:
        raise ReductionError(
            f"index opponent {source_pos} fields differ from canonical materializer"
        )
    opponent = row.get("id")
    if not isinstance(opponent, str) or not opponent:
        raise ReductionError(f"index opponent {source_pos} has invalid id")
    if row.get("kind") != "recorded_trace":
        raise ReductionError(f"index.{opponent}.kind must be recorded_trace")
    if row.get("provenance") != CANONICAL_PROVENANCE:
        raise ReductionError(
            f"index.{opponent}.provenance differs from canonical corpus"
        )
    if row.get("adaptive") is not False or row.get("executable") is not False:
        raise ReductionError(
            f"index.{opponent} must be non-adaptive and non-executable"
        )
    submission_id = _plain_int(
        row.get("submission_id"),
        f"index.{opponent}.submission_id",
        1,
    )
    team_id = _plain_int(
        row.get("team_id"),
        f"index.{opponent}.team_id",
        1,
    )
    team_name = row.get("team_name")
    family = row.get("family")
    memberships = row.get("memberships")
    episode_id = _plain_int(
        row.get("episode_id"),
        f"index.{opponent}.episode_id",
        1,
    )
    seed = _plain_int(row.get("seed"), f"index.{opponent}.seed")
    recorded_seat = row.get("recorded_opponent_seat")
    candidate_seat = row.get("candidate_seat_for_recorded_orientation")
    if not isinstance(team_name, str) or not team_name:
        raise ReductionError(f"index.{opponent}.team_name must be nonempty")
    if family != f"recorded-submission:{submission_id}":
        raise ReductionError(f"index.{opponent}.family is not canonical")
    if not isinstance(memberships, list):
        raise ReductionError(f"index.{opponent}.memberships must be a list")
    if type(recorded_seat) is not int or recorded_seat not in (0, 1):
        raise ReductionError(
            f"index.{opponent}.recorded_opponent_seat must be 0 or 1"
        )
    if candidate_seat != 1 - recorded_seat:
        raise ReductionError(
            f"index.{opponent}.candidate seat is not the recorded-seat complement"
        )
    entry = row.get("entry")
    if (
        not isinstance(entry, str)
        or not entry
        or not Path(entry).is_absolute()
    ):
        raise ReductionError(f"index.{opponent}.entry must be an absolute path")
    entry_sha256 = _sha256(
        row.get("entry_sha256"),
        f"index.{opponent}.entry_sha256",
    )
    actions_sha256 = _sha256(
        row.get("actions_sha256"),
        f"index.{opponent}.actions_sha256",
    )
    replay_sha256 = _sha256(
        row.get("replay_sha256"),
        f"index.{opponent}.replay_sha256",
    )
    decisions = _plain_int(
        row.get("decisions"),
        f"index.{opponent}.decisions",
        1,
    )
    if decisions != EXPECTED_CALLBACKS:
        raise ReductionError(
            f"index.{opponent}.decisions must be {EXPECTED_CALLBACKS}"
        )
    if row.get("interpretation") != CANONICAL_INTERPRETATION:
        raise ReductionError(
            f"index.{opponent}.interpretation differs from canonical materializer"
        )
    return {
        "id": opponent,
        "kind": "recorded_trace",
        "provenance": CANONICAL_PROVENANCE,
        "executable": False,
        "family": family,
        "submission_id": submission_id,
        "team_id": team_id,
        "team_name": team_name,
        "memberships": memberships,
        "episode_id": episode_id,
        "seed": seed,
        "recorded_opponent_seat": recorded_seat,
        "candidate_seat_for_recorded_orientation": candidate_seat,
        "entry_sha256": entry_sha256,
        "actions_sha256": actions_sha256,
        "replay_sha256": replay_sha256,
        "decisions": decisions,
        "adaptive": False,
        "interpretation": CANONICAL_INTERPRETATION,
        "recorded_index": source_pos,
    }


def _canonical_materialization(
    corpus: Path | None,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    if corpus is None:
        raise ReductionError(
            "canonical corpus root is required for authorizing reduction"
        )
    root = Path(corpus).resolve(strict=True)
    if not root.is_dir():
        raise ReductionError("canonical corpus root must be a directory")
    manifest_path = (root / "manifest.json").resolve(strict=True)
    if not manifest_path.is_relative_to(root):
        raise ReductionError("canonical manifest escaped corpus root")
    manifest_raw = _read_regular_bytes(manifest_path)
    manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
    if manifest_sha256 != CANONICAL_MANIFEST_SHA256:
        raise ReductionError(
            "canonical corpus manifest SHA256 drifted: "
            f"{manifest_sha256} != {CANONICAL_MANIFEST_SHA256}"
        )
    manifest = _parse_json_bytes(manifest_raw, str(manifest_path))
    if type(manifest) is not dict:
        raise ReductionError("canonical corpus manifest must be an object")
    if manifest.get("schema") != CANONICAL_MANIFEST_SCHEMA:
        raise ReductionError("canonical corpus manifest schema drifted")
    if manifest.get("submission_hold") is not True:
        raise ReductionError("canonical corpus manifest lost submission hold")
    if (
        _plain_int(
            manifest.get("unique_submission_targets"),
            "canonical unique_submission_targets",
            1,
        )
        != CANONICAL_UNIQUE_SUBMISSIONS
    ):
        raise ReductionError("canonical corpus target count drifted")
    targets = manifest.get("targets")
    if type(targets) is not list or len(targets) != CANONICAL_UNIQUE_SUBMISSIONS:
        raise ReductionError("canonical corpus targets are incomplete")

    materialize = _captured_materializer()
    seen_replays: set[Path] = set()
    fixture_count = 0
    with tempfile.TemporaryDirectory(
        prefix="titan-v5-gauntlet-authority-"
    ) as temporary:
        private_root = Path(temporary) / "corpus"
        private_root.mkdir()
        (private_root / "manifest.json").write_bytes(manifest_raw)
        for target_pos, target in enumerate(targets):
            if type(target) is not dict or target.get("status") != "complete":
                raise ReductionError(
                    f"canonical target {target_pos} is incomplete"
                )
            replays = target.get("replays")
            if (
                type(replays) is not list
                or len(replays) != CANONICAL_REPLAYS_PER_SUBMISSION
            ):
                raise ReductionError(
                    f"canonical target {target_pos} lacks three replays"
                )
            for replay_pos, fixture in enumerate(replays):
                if type(fixture) is not dict:
                    raise ReductionError(
                        f"canonical replay {target_pos}/{replay_pos} is not an object"
                    )
                rel_text = fixture.get("path")
                if not isinstance(rel_text, str) or not rel_text:
                    raise ReductionError("canonical replay path is invalid")
                rel = Path(rel_text)
                if rel.is_absolute() or ".." in rel.parts:
                    raise ReductionError("canonical replay path escapes corpus root")
                source = (root / rel).resolve(strict=True)
                if not source.is_relative_to(root):
                    raise ReductionError("canonical replay resolved outside corpus root")
                if source in seen_replays:
                    raise ReductionError("canonical replay path is duplicated")
                seen_replays.add(source)
                raw = _read_regular_bytes(source)
                expected_sha = _sha256(
                    fixture.get("sha256"),
                    f"canonical replay {target_pos}/{replay_pos} sha256",
                )
                actual_sha = hashlib.sha256(raw).hexdigest()
                if actual_sha != expected_sha:
                    raise ReductionError(
                        "canonical replay digest differs from manifest: "
                        f"{rel_text}"
                    )
                destination = private_root.joinpath(*rel.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                fixture_count += 1
        if fixture_count != CANONICAL_FIXTURE_COUNT:
            raise ReductionError(
                f"canonical corpus has {fixture_count} fixtures; "
                f"expected {CANONICAL_FIXTURE_COUNT}"
            )
        output = Path(temporary) / "materialized"
        try:
            result = materialize(private_root, output)
        except Exception as exc:
            raise ReductionError(
                f"captured canonical materialization failed: {exc}"
            ) from exc
        if type(result) is not dict:
            raise ReductionError("canonical materializer returned a non-object")
        if set(result) != {
            "schema",
            "source_manifest_sha256",
            "submission_hold",
            "opponents",
            "targets",
        }:
            raise ReductionError("canonical materializer result fields drifted")
        if result.get("schema") != CANONICAL_INDEX_SCHEMA:
            raise ReductionError("canonical materializer index schema drifted")
        if result.get("source_manifest_sha256") != CANONICAL_MANIFEST_SHA256:
            raise ReductionError("canonical materializer lost manifest binding")
        if result.get("submission_hold") is not True:
            raise ReductionError("canonical materializer lost submission hold")
        if result.get("targets") != CANONICAL_UNIQUE_SUBMISSIONS:
            raise ReductionError("canonical materializer target count drifted")
        opponents = result.get("opponents")
        if type(opponents) is not list or len(opponents) != CANONICAL_FIXTURE_COUNT:
            raise ReductionError("canonical materializer fixture count drifted")
        rows = [
            _runtime_row_projection(row, source_pos)
            for source_pos, row in enumerate(opponents)
        ]
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ReductionError("canonical materializer produced duplicate fixture IDs")
    materialization_sha256 = _digest(rows)
    authority = {
        "source_manifest_sha256": CANONICAL_MANIFEST_SHA256,
        "materializer_git_blob": CANONICAL_MATERIALIZER_GIT_BLOB,
        "unique_submission_targets": CANONICAL_UNIQUE_SUBMISSIONS,
        "recorded_fixture_count": CANONICAL_FIXTURE_COUNT,
        "fixtures_per_submission": CANONICAL_REPLAYS_PER_SUBMISSION,
        "materialization_manifest_sha256": materialization_sha256,
        "captured_replay_count": fixture_count,
    }
    return rows, by_id, authority


def _load_index(
    path: Path,
    canonical_rows: list[dict[str, Any]],
    canonical_authority: dict[str, Any],
) -> tuple[
    str,
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    index, _raw, index_sha256 = _read_json(path)
    if type(index) is not dict or set(index) != {
        "schema",
        "source_manifest_sha256",
        "submission_hold",
        "opponents",
        "targets",
    }:
        raise ReductionError(
            "runtime corpus index fields differ from canonical materializer"
        )
    if index.get("schema") != CANONICAL_INDEX_SCHEMA:
        raise ReductionError("runtime corpus index schema drifted")
    if index.get("source_manifest_sha256") != CANONICAL_MANIFEST_SHA256:
        raise ReductionError(
            "runtime corpus index does not bind the canonical source manifest"
        )
    if index.get("submission_hold") is not True:
        raise ReductionError("runtime corpus index lost submission hold")
    if index.get("targets") != CANONICAL_UNIQUE_SUBMISSIONS:
        raise ReductionError("runtime corpus index target count drifted")
    opponents = index.get("opponents")
    if type(opponents) is not list:
        raise ReductionError("runtime corpus index must contain opponents list")
    if len(opponents) != CANONICAL_FIXTURE_COUNT:
        raise ReductionError(
            f"runtime corpus index has {len(opponents)} fixtures; "
            f"canonical universe requires {CANONICAL_FIXTURE_COUNT}"
        )
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    entry_paths: list[str] = []
    for source_pos, (row, canonical) in enumerate(
        zip(opponents, canonical_rows, strict=True)
    ):
        projection = _runtime_row_projection(row, source_pos)
        if projection != canonical:
            raise ReductionError(
                "runtime corpus index differs from canonical materialization at "
                f"fixture {source_pos}: {projection['id']}"
            )
        opponent = projection["id"]
        if opponent in by_id:
            raise ReductionError(
                f"duplicate recorded opponent id in runtime index: {opponent}"
            )
        rows.append(projection)
        by_id[opponent] = projection
        entry_paths.append(row["entry"])
    materialization_sha256 = _digest(rows)
    if (
        materialization_sha256
        != canonical_authority["materialization_manifest_sha256"]
    ):
        raise ReductionError(
            "runtime corpus materialization digest differs from canonical corpus"
        )
    authority = {
        "index_sha256": index_sha256,
        "source_manifest_sha256": CANONICAL_MANIFEST_SHA256,
        "recorded_fixture_count": len(rows),
        "materialization_manifest_sha256": materialization_sha256,
        "entry_paths_sha256": _digest(entry_paths),
    }
    return index_sha256, rows, by_id, authority


def _load_indexes(
    index: Path | Iterable[Path],
    *,
    corpus: Path | None,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    canonical_rows, _canonical_by_id, canonical_authority = (
        _canonical_materialization(corpus)
    )
    if isinstance(index, (str, Path)):
        paths = [Path(index)]
    else:
        paths = [Path(path) for path in index]
    if not paths:
        raise ReductionError("at least one runtime corpus index is required")
    seen_paths: set[Path] = set()
    by_sha: dict[str, dict[str, Any]] = {}
    for path in paths:
        key = path.absolute()
        if key in seen_paths:
            raise ReductionError(f"duplicate runtime corpus index path: {path}")
        seen_paths.add(key)
        index_sha256, rows, by_id, authority = _load_index(
            path,
            canonical_rows,
            canonical_authority,
        )
        binding = {
            "rows": rows,
            "by_id": by_id,
            "authority": authority,
        }
        prior = by_sha.get(index_sha256)
        if prior is not None:
            if prior["authority"] != authority:
                raise ReductionError(
                    "identical runtime index SHA produced inconsistent authority"
                )
            continue
        by_sha[index_sha256] = binding
    materialization_values = {
        binding["authority"]["materialization_manifest_sha256"]
        for binding in by_sha.values()
    }
    if materialization_values != {
        canonical_authority["materialization_manifest_sha256"]
    }:
        raise ReductionError(
            "runtime indexes disagree on canonical materialization authority"
        )
    authority = {
        **canonical_authority,
        "runtime_index_count": len(by_sha),
        "runtime_indexes": sorted(
            (
                {
                    "index_sha256": sha,
                    "entry_paths_sha256": binding["authority"][
                        "entry_paths_sha256"
                    ],
                }
                for sha, binding in by_sha.items()
            ),
            key=lambda row: row["index_sha256"],
        ),
    }
    return by_sha, authority
'''

text = sub_once(
    text,
    r"def _load_index\(\n.*?\n\ndef _expected_rows_for_shard\(",
    authority_block.lstrip("\n") + "\n\ndef _expected_rows_for_shard(",
    "canonical materialization/index block",
)

text = sub_once(
    text,
    r'''def _scan_roots\(\n    label: str,\n    roots: Iterable\[Path\],\n    index_sha256: str,\n    index_rows: list\[dict\[str, Any\]\],\n    index_by_id: dict\[str, dict\[str, Any\]\],\n\) -> tuple\[''',
    '''def _scan_roots(\n    label: str,\n    roots: Iterable[Path],\n    indexes_by_sha: dict[str, dict[str, Any]],\n) -> tuple[''',
    "scan roots signature",
)
text = replace_once(
    text,
    '''        if declared_index != index_sha256:\n            raise ReductionError(\n                f"{label} run index differs from supplied "\n                f"authenticated index: {root}"\n            )\n        engine = _engine_map(run.get("engine"), f"{root}.engine")\n''',
    '''        index_binding = indexes_by_sha.get(declared_index)\n        if index_binding is None:\n            raise ReductionError(\n                f"{label} run references an unsupplied runtime index: {root}"\n            )\n        index_rows = index_binding["rows"]\n        index_by_id = index_binding["by_id"]\n        index_authority = index_binding["authority"]\n        engine = _engine_map(run.get("engine"), f"{root}.engine")\n''',
    "per-run index lookup",
)
text = replace_once(
    text,
    '''            "index_sha256": declared_index,\n            "evaluator_sha256": evaluator_sha256,\n''',
    '''            "index_sha256": declared_index,\n            "index_materialization_sha256": index_authority[\n                "materialization_manifest_sha256"\n            ],\n            "canonical_manifest_sha256": index_authority[\n                "source_manifest_sha256"\n            ],\n            "evaluator_sha256": evaluator_sha256,\n''',
    "run receipt semantic index authority",
)

panel_topology = r'''
def _panel_topology(
    v31_runs: list[dict[str, Any]],
    v4_runs: list[dict[str, Any]],
    index_authority: dict[str, Any],
    expected_cells_override: int | None,
) -> tuple[dict[str, Any], int]:
    def inspect(
        label: str,
        runs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        shard_totals = {row["shards"] for row in runs}
        if len(shard_totals) != 1:
            raise ReductionError(
                f"{label} roots disagree on declared shard count"
            )
        declared = next(iter(shard_totals))
        by_shard: dict[int, dict[str, Any]] = {}
        raw_index_values = {row["index_sha256"] for row in runs}
        materialization_values = {
            row["index_materialization_sha256"] for row in runs
        }
        canonical_manifest_values = {
            row["canonical_manifest_sha256"] for row in runs
        }
        evaluator_values = {
            row["evaluator_sha256"] for row in runs
        }
        loader_values = {row["loader_sha256"] for row in runs}
        engine_values = {_digest(row["engine"]) for row in runs}
        if len(materialization_values) != 1:
            raise ReductionError(
                f"{label} roots disagree on semantic corpus materialization"
            )
        if len(canonical_manifest_values) != 1:
            raise ReductionError(
                f"{label} roots disagree on canonical corpus manifest"
            )
        if len(evaluator_values) != 1:
            raise ReductionError(
                f"{label} roots disagree on evaluator identity"
            )
        if len(loader_values) != 1:
            raise ReductionError(
                f"{label} roots disagree on loader identity"
            )
        if len(engine_values) != 1:
            raise ReductionError(
                f"{label} roots disagree on engine identity"
            )
        for row in runs:
            shard = row["shard"]
            if shard in by_shard:
                raise ReductionError(
                    f"duplicate {label} shard receipt: {shard}"
                )
            by_shard[shard] = row
        expected_shards = set(range(declared))
        observed_shards = set(by_shard)
        return {
            "declared_shards": declared,
            "observed_shards": sorted(observed_shards),
            "complete_shard_set": observed_shards == expected_shards,
            "all_observed_roots_cell_complete": all(
                row["root_cell_set_complete"] for row in runs
            ),
            "selected_fixtures_observed": sum(
                row["selected_fixtures"] for row in runs
            ),
            "index_sha256s": sorted(raw_index_values),
            "index_materialization_sha256": next(
                iter(materialization_values)
            ),
            "canonical_manifest_sha256": next(
                iter(canonical_manifest_values)
            ),
            "evaluator_sha256": next(iter(evaluator_values)),
            "loader_sha256": next(iter(loader_values)),
            "engine_digest": next(iter(engine_values)),
            "by_shard": by_shard,
        }

    left = inspect("v31", v31_runs)
    right = inspect("v4", v4_runs)
    if left["declared_shards"] != right["declared_shards"]:
        raise ReductionError("V3.1/V4 declared shard counts differ")
    if (
        left["index_materialization_sha256"]
        != right["index_materialization_sha256"]
    ):
        raise ReductionError(
            "V3.1/V4 semantic corpus materializations differ"
        )
    if (
        left["index_materialization_sha256"]
        != index_authority["materialization_manifest_sha256"]
    ):
        raise ReductionError(
            "run receipts do not match canonical corpus materialization"
        )
    if (
        left["canonical_manifest_sha256"]
        != right["canonical_manifest_sha256"]
        or left["canonical_manifest_sha256"]
        != index_authority["source_manifest_sha256"]
    ):
        raise ReductionError(
            "run receipts do not share canonical manifest authority"
        )
    if left["evaluator_sha256"] != right["evaluator_sha256"]:
        raise ReductionError("V3.1/V4 evaluator identities differ")
    if left["loader_sha256"] != right["loader_sha256"]:
        raise ReductionError("V3.1/V4 loader identities differ")
    if left["engine_digest"] != right["engine_digest"]:
        raise ReductionError("V3.1/V4 engine identities differ")
    shared_shards = set(left["by_shard"]) & set(right["by_shard"])
    for shard in shared_shards:
        left_run = left["by_shard"][shard]
        right_run = right["by_shard"][shard]
        if left_run["index_sha256"] != right_run["index_sha256"]:
            raise ReductionError(
                "V3.1/V4 shard used different workspace indexes for "
                f"shard {shard}"
            )
        if (
            left_run["selected_fixtures"]
            != right_run["selected_fixtures"]
        ):
            raise ReductionError(
                "V3.1/V4 selected fixture count differs for "
                f"shard {shard}"
            )
        if (
            left_run["expected_fixtures"]
            != right_run["expected_fixtures"]
        ):
            raise ReductionError(
                "V3.1/V4 authenticated fixture count differs for "
                f"shard {shard}"
            )

    expected_cells = index_authority["recorded_fixture_count"] * 2
    if expected_cells_override is not None:
        expected_cells_override = _plain_int(
            expected_cells_override,
            "expected_cells",
            1,
        )
        if expected_cells_override != expected_cells:
            raise ReductionError(
                "expected_cells override disagrees with canonical corpus: "
                f"{expected_cells_override} != {expected_cells}"
            )

    complete_topology = (
        left["complete_shard_set"]
        and right["complete_shard_set"]
        and left["all_observed_roots_cell_complete"]
        and right["all_observed_roots_cell_complete"]
        and left["selected_fixtures_observed"]
        == index_authority["recorded_fixture_count"]
        and right["selected_fixtures_observed"]
        == index_authority["recorded_fixture_count"]
    )
    public_left = {
        key: value for key, value in left.items() if key != "by_shard"
    }
    public_right = {
        key: value for key, value in right.items() if key != "by_shard"
    }
    return {
        "index_authority": index_authority,
        "v31": public_left,
        "v4": public_right,
        "complete_cross_version_shard_topology": complete_topology,
        "authenticated_expected_cells": expected_cells,
        "expected_cells_override": expected_cells_override,
    }, expected_cells
'''
text = sub_once(
    text,
    r"def _panel_topology\(\n.*?\n\ndef _same_authority\(",
    panel_topology.lstrip("\n") + "\n\ndef _same_authority(",
    "multi-index panel topology",
)

reduce_prefix = r'''
def reduce_roots(
    v31_roots: Iterable[Path],
    v4_roots: Iterable[Path],
    *,
    index: Path | Iterable[Path],
    corpus: Path | None = None,
    expected_cells: int | None = None,
) -> dict[str, Any]:
    indexes_by_sha, index_authority = _load_indexes(
        index,
        corpus=corpus,
    )
    v31, v31_runs = _scan_roots(
        "v31",
        v31_roots,
        indexes_by_sha,
    )
    v4, v4_runs = _scan_roots(
        "v4",
        v4_roots,
        indexes_by_sha,
    )
    used_indexes = {
        row["index_sha256"] for row in v31_runs + v4_runs
    }
    supplied_indexes = set(indexes_by_sha)
    if used_indexes != supplied_indexes:
        raise ReductionError(
            "supplied runtime index set must exactly equal run-referenced indexes"
        )
    topology, expected_cells = _panel_topology(
        v31_runs,
        v4_runs,
        index_authority,
        expected_cells,
    )
'''
text = sub_once(
    text,
    r"def reduce_roots\(\n.*?\n    keys = sorted",
    reduce_prefix.lstrip("\n") + "    keys = sorted",
    "reduce roots multi-index prefix",
)

text = sub_once(
    text,
    r'''    parser\.add_argument\(\n        "--index",\n        type=Path,\n        required=True,\n        help=\(\n            "Exact top30-union corpus index used by the gauntlet runners\."\n        \),\n    \)''',
    '''    parser.add_argument(\n        "--index",\n        action="append",\n        type=Path,\n        required=True,\n        help=(\n            "Exact workspace-local recorded-opponents.json used by a consumed "\n            "shard. Repeat once per distinct raw index SHA."\n        ),\n    )\n    parser.add_argument(\n        "--corpus",\n        type=Path,\n        required=True,\n        help=(\n            "Extracted canonical top30-union corpus. The reducer privately "\n            "recaptures all 123 replay bytes and re-materializes action tapes."\n        ),\n    )''',
    "CLI repeated indexes and corpus",
)
text = replace_once(
    text,
    '''            index=args.index,\n            expected_cells=args.expected_cells,\n''',
    '''            index=args.index,\n            corpus=args.corpus,\n            expected_cells=args.expected_cells,\n''',
    "CLI canonical corpus call",
)
REDUCER.write_text(text, encoding="utf-8")

# Keep the broad existing suite while making its synthetic indexes look exactly
# like corpus.py output. The internal canonical materializer is patched only in
# this unit-test class; production has no injectable authority parameter.
test = TEST.read_text(encoding="utf-8")
setup_and_index = r'''    def setUp(self):
        self._canonical_rows = None
        self._canonical_authority = None
        patcher = mock.patch.object(
            rg,
            "_canonical_materialization",
            side_effect=self._fake_canonical_materialization,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _fake_canonical_materialization(self, _corpus):
        if self._canonical_rows is None or self._canonical_authority is None:
            raise rg.ReductionError("synthetic canonical authority was not initialized")
        rows = json.loads(json.dumps(self._canonical_rows))
        return (
            rows,
            {row["id"]: row for row in rows},
            json.loads(json.dumps(self._canonical_authority)),
        )

    def index(self, base, count=2):
        path = Path(base) / "index.json"
        opponents = []
        source_manifest_sha256 = hashlib.sha256(
            f"synthetic-canonical-manifest-{count}".encode()
        ).hexdigest()
        for i in range(count):
            submission_id = i + 1
            episode_id = 100000 + i
            recorded_seat = 1 - (i % 2)
            opponents.append({
                "id": f"opp{i:03d}",
                "kind": "recorded_trace",
                "provenance": rg.CANONICAL_PROVENANCE,
                "executable": False,
                "family": f"recorded-submission:{submission_id}",
                "submission_id": submission_id,
                "team_id": 200000 + i,
                "team_name": f"team-{i}",
                "memberships": [{"group": "current_top30"}],
                "episode_id": episode_id,
                "seed": 1909000000 + i,
                "recorded_opponent_seat": recorded_seat,
                "candidate_seat_for_recorded_orientation": 1 - recorded_seat,
                "entry": str((Path(base) / f"opp{i:03d}" / "main.py").absolute()),
                "entry_sha256": hashlib.sha256(b"canonical-adapter").hexdigest(),
                "actions_sha256": hashlib.sha256(
                    f"actions-{i}".encode()
                ).hexdigest(),
                "replay_sha256": hashlib.sha256(
                    f"replay-{i}".encode()
                ).hexdigest(),
                "decisions": rg.EXPECTED_CALLBACKS,
                "adaptive": False,
                "interpretation": rg.CANONICAL_INTERPRETATION,
            })
        write_json(path, {
            "schema": rg.CANONICAL_INDEX_SCHEMA,
            "source_manifest_sha256": source_manifest_sha256,
            "submission_hold": True,
            "opponents": opponents,
            "targets": count,
        })
        self._canonical_rows = [
            rg._runtime_row_projection(row, i)
            for i, row in enumerate(opponents)
        ]
        materialization_sha256 = rg._digest(self._canonical_rows)
        self._canonical_authority = {
            "source_manifest_sha256": source_manifest_sha256,
            "materializer_git_blob": "f" * 40,
            "unique_submission_targets": count,
            "recorded_fixture_count": count,
            "fixtures_per_submission": 1,
            "materialization_manifest_sha256": materialization_sha256,
            "captured_replay_count": count,
        }
        return path, opponents

    def expected_count'''
test = sub_once(
    test,
    r"    def index\(self, base, count=2\):\n.*?\n    def expected_count",
    setup_and_index,
    "synthetic canonical index helper",
)
# The synthetic helper varies canonical counts by test; let _load_index compare
# against the fake authority rather than production constants.
# Production still has fixed 41/123 constants through _canonical_materialization.
reducer = REDUCER.read_text(encoding="utf-8")
reducer = replace_once(
    reducer,
    '''    if index.get("source_manifest_sha256") != CANONICAL_MANIFEST_SHA256:\n        raise ReductionError(\n            "runtime corpus index does not bind the canonical source manifest"\n        )\n''',
    '''    if (\n        index.get("source_manifest_sha256")\n        != canonical_authority["source_manifest_sha256"]\n    ):\n        raise ReductionError(\n            "runtime corpus index does not bind the canonical source manifest"\n        )\n''',
    "runtime manifest authority comparison",
)
reducer = replace_once(
    reducer,
    '''    if index.get("targets") != CANONICAL_UNIQUE_SUBMISSIONS:\n        raise ReductionError("runtime corpus index target count drifted")\n''',
    '''    if (\n        index.get("targets")\n        != canonical_authority["unique_submission_targets"]\n    ):\n        raise ReductionError("runtime corpus index target count drifted")\n''',
    "runtime target authority comparison",
)
reducer = replace_once(
    reducer,
    '''    if len(opponents) != CANONICAL_FIXTURE_COUNT:\n        raise ReductionError(\n            f"runtime corpus index has {len(opponents)} fixtures; "\n            f"canonical universe requires {CANONICAL_FIXTURE_COUNT}"\n        )\n''',
    '''    if len(opponents) != canonical_authority["recorded_fixture_count"]:\n        raise ReductionError(\n            f"runtime corpus index has {len(opponents)} fixtures; "\n            "canonical universe requires "\n            f"{canonical_authority['recorded_fixture_count']}"\n        )\n''',
    "runtime fixture authority comparison",
)
reducer = replace_once(
    reducer,
    '''        "source_manifest_sha256": CANONICAL_MANIFEST_SHA256,\n        "recorded_fixture_count": len(rows),\n''',
    '''        "source_manifest_sha256": canonical_authority[\n            "source_manifest_sha256"\n        ],\n        "recorded_fixture_count": len(rows),\n''',
    "runtime index receipt manifest identity",
)
REDUCER.write_text(reducer, encoding="utf-8")

# One existing CLI test invokes main() in-process; fake canonical authority ignores
# the corpus path, but the production CLI must still require the argument.
cli_anchor = '''                "--index",\n                str(index),\n'''
cli_count = test.count(cli_anchor)
if cli_count != 1:
    raise SystemExit(f"CLI test index anchor expected once, found {cli_count}")
test = test.replace(
    cli_anchor,
    cli_anchor + '''                "--corpus",\n                str(Path(td) / "synthetic-corpus"),\n''',
    1,
)

new_tests = r'''
    def test_self_consistent_smaller_runtime_index_cannot_redefine_universe(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 2)
            smaller = Path(td) / "smaller-index.json"
            payload = json.loads(Path(index).read_text())
            payload["opponents"] = payload["opponents"][:1]
            payload["targets"] = 1
            write_json(smaller, payload)
            with self.assertRaisesRegex(
                rg.ReductionError,
                "target count|canonical universe",
            ):
                rg.reduce_roots([], [], index=smaller)

    def test_semantic_substitute_index_rejects_even_with_spoofed_manifest_sha(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 2)
            substitute = Path(td) / "substitute-index.json"
            payload = json.loads(Path(index).read_text())
            payload["opponents"][1]["seed"] += 1
            write_json(substitute, payload)
            with self.assertRaisesRegex(
                rg.ReductionError,
                "differs from canonical materialization",
            ):
                rg.reduce_roots([], [], index=substitute)

    def test_equivalent_workspace_indexes_with_distinct_absolute_paths_assemble(self):
        with tempfile.TemporaryDirectory() as td:
            index_a, rows = self.index(td, 2)
            index_b = Path(td) / "index-b.json"
            payload = json.loads(Path(index_a).read_text())
            for row in payload["opponents"]:
                row["entry"] = str(
                    (Path(td) / "other-workspace" / row["id"] / "main.py").absolute()
                )
            write_json(index_b, payload)
            self.assertNotEqual(
                hashlib.sha256(Path(index_a).read_bytes()).hexdigest(),
                hashlib.sha256(index_b.read_bytes()).hexdigest(),
            )
            a0 = self.root(td, "v31", index_a, shard=0, shards=2)
            a1 = self.root(td, "v31", index_b, shard=1, shards=2)
            b0 = self.root(td, "v4", index_a, shard=0, shards=2)
            b1 = self.root(td, "v4", index_b, shard=1, shards=2)
            self.fill_root(a0, "v31", rows, 0, 2, score_bias=10)
            self.fill_root(a1, "v31", rows, 1, 2, score_bias=10)
            self.fill_root(b0, "v4", rows, 0, 2)
            self.fill_root(b1, "v4", rows, 1, 2)
            report = rg.reduce_roots(
                [a0, a1],
                [b0, b1],
                index=[index_a, index_b],
            )
            self.assertTrue(report["panel_complete"])
            authority = report["authority"]["panel_topology"]["index_authority"]
            self.assertEqual(authority["runtime_index_count"], 2)
            self.assertEqual(len(authority["runtime_indexes"]), 2)

    def test_cross_version_shard_must_bind_same_raw_workspace_index(self):
        with tempfile.TemporaryDirectory() as td:
            index_a, rows = self.index(td, 1)
            index_b = Path(td) / "index-b.json"
            payload = json.loads(Path(index_a).read_text())
            payload["opponents"][0]["entry"] = str(
                (Path(td) / "other" / "opp000" / "main.py").absolute()
            )
            write_json(index_b, payload)
            a = self.root(td, "v31", index_a)
            b = self.root(td, "v4", index_b)
            self.fill_root(a, "v31", rows, 0, 1)
            self.fill_root(b, "v4", rows, 0, 1)
            with self.assertRaisesRegex(
                rg.ReductionError,
                "different workspace indexes",
            ):
                rg.reduce_roots([a], [b], index=[index_a, index_b])
'''
test = replace_once(
    test,
    '\n\nif __name__ == "__main__":\n',
    new_tests + '\n\nif __name__ == "__main__":\n',
    "canonical multi-index regression tests",
)
TEST.write_text(test, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
marker = "## Canonical corpus + workspace-index authority (v4)"
if marker in readme:
    raise SystemExit("README already contains v4 canonical authority section")
readme += r'''

## Canonical corpus + workspace-index authority (v4)

The reducer no longer lets a caller-provided runtime index define the universe.
Authorizing reduction requires `--corpus` pointing at the extracted canonical
Top30-union corpus. The reducer single-reads and pins manifest SHA256
`510ca5c5...`, captures all 123 replay files by the manifest SHA256s into a
private temporary corpus, captured-loads the pinned `corpus.py` Git blob, and
re-materializes the 41 x 3 recorded-action fixtures itself. Runtime index rows
must exactly equal that canonical materialization on fixture identity,
provenance, orientation, replay SHA, action-tape SHA, adapter SHA, and decision
count.

`corpus.py` intentionally records an absolute adapter path, so independent
shard workspaces have different raw `recorded-opponents.json` bytes. `--index`
is therefore repeatable. Each run is bound to the exact raw index SHA it used;
V3.1 and V4 for the same shard must share that raw index, while different
shards may use different raw SHA256s only when their canonical materialization
digest is identical. This preserves every already-running shard without
normalizing or rewriting its evidence.
'''
README.write_text(readme, encoding="utf-8")

allowed = {
    ".github/workflows/titan-v5-v31-v4-gauntlet-reducer.yml",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v5/archive-version-bridge/README.md",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v5/archive-version-bridge/reduce_gauntlet.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v5/archive-version-bridge/test_reduce_gauntlet.py",
} | TRANSIENT
changed = {line for line in run("git", "diff", "--name-only", BASE).splitlines() if line}
if changed - allowed:
    raise SystemExit(f"patch escaped #13415 reducer scope: {sorted(changed - allowed)!r}")
print("gauntlet canonical-universe v4 staged", *sorted(changed), sep="\n")
