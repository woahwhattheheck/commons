# SPDX-License-Identifier: Apache-2.0
"""Raw evaluator shard, receipt, and report provenance admission."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from strict_types import (
    EXPECTED_ACTION_COUNT, EXPECTED_AGENT_RNG_SEED, EXPECTED_CELLS_PER_ARM,
    EXPECTED_ENGINE_FILES, EXPECTED_ENGINE_REF, EXPECTED_EVALUATOR_EMBEDDED_OLD,
    EXPECTED_EVALUATOR_RAW_OLD_AFTER, EXPECTED_EVALUATOR_REPAIR_OPERATION,
    EXPECTED_EVALUATOR_SOURCE_BLOB, EXPECTED_LIMITS, EXPECTED_METHOD,
    EXPECTED_OPPONENTS, EXPECTED_SEEDS, HEX32, HEX40, HEX64, OPERATION,
    AdmissionError, _is_int, _is_number, _require_hex, expected_keys,
    git_blob_sha1, load_json, sha256_file,
)
from strict_artifacts import (
    _artifact_paths, _validate_game, _validate_materialization,
)


def _validate_limits(value: Any, arm: str, shard: str) -> None:
    if not isinstance(value, Mapping) or set(value) != set(EXPECTED_LIMITS):
        raise AdmissionError(f"{arm}: limits schema mismatch in {shard}")
    for key, expected in EXPECTED_LIMITS.items():
        actual = value.get(key)
        if not _is_number(actual) or float(actual) != float(expected):
            raise AdmissionError(f"{arm}: limit {key} mismatch in {shard}: {actual!r}")


def _shard_files(directory: Path, arm: str) -> list[Path]:
    directory = Path(directory).resolve(strict=True)
    pattern = re.compile(rf"^{re.escape(arm)}-shard-[0-9]{{2}}\.json$")
    result = sorted(path for path in directory.iterdir() if path.is_file() and pattern.fullmatch(path.name))
    if len(result) != 2:
        raise AdmissionError(f"{arm}: expected exactly two final shard reports, found {len(result)}")
    return result


def _validate_evaluator_receipt(shard_dir: Path, identity: Mapping[str, Any], arm: str) -> dict[str, Any]:
    receipt_path = shard_dir / "EVALUATOR-MATERIALIZATION.json"
    receipt = load_json(receipt_path)
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != 1:
        raise AdmissionError(f"{arm}: candidate-action evaluator receipt missing")
    if receipt.get("operation") != EXPECTED_EVALUATOR_REPAIR_OPERATION:
        raise AdmissionError(f"{arm}: candidate-action evaluator operation mismatch")
    if receipt.get("repair") != "sol-candidate-action-evidence-v1":
        raise AdmissionError(f"{arm}: unrecognized candidate-action evaluator repair")
    source = receipt.get("source") or {}
    patched = receipt.get("patched") or {}
    if source.get("path_name") != "evaluate.py":
        raise AdmissionError(f"{arm}: evaluator source filename mismatch")
    if source.get("git_blob_sha1") != EXPECTED_EVALUATOR_SOURCE_BLOB:
        raise AdmissionError(f"{arm}: evaluator source blob mismatch")
    if source.get("sha256") != identity.get("evaluator_source_sha256"):
        raise AdmissionError(f"{arm}: evaluator source digest mismatch")
    if (patched.get("candidate_action_field") != "candidate_action_sha256"
            or patched.get("candidate_action_count_field") != "candidate_action_count"
            or patched.get("capture_phase") != "after both returned actions, before interpreter"):
        raise AdmissionError(f"{arm}: candidate-action capture contract mismatch")
    patched_name = patched.get("path_name")
    if not isinstance(patched_name, str) or Path(patched_name).name != patched_name:
        raise AdmissionError(f"{arm}: invalid patched evaluator filename")
    evaluator = (shard_dir / patched_name).resolve(strict=True)
    if not _is_int(patched.get("bytes")) or patched.get("bytes") != evaluator.stat().st_size:
        raise AdmissionError(f"{arm}: patched evaluator byte count mismatch")
    if sha256_file(evaluator) != patched.get("sha256") or patched.get("sha256") != identity.get("evaluator_effective_sha256"):
        raise AdmissionError(f"{arm}: patched evaluator digest mismatch")
    if git_blob_sha1(evaluator.read_bytes()) != patched.get("git_blob_sha1"):
        raise AdmissionError(f"{arm}: patched evaluator Git blob mismatch")
    patches = patched.get("patches")
    labels = (
        "candidate digest initialization",
        "pre-interpreter candidate action capture",
        "candidate digest publication",
    )
    if not isinstance(patches, list) or tuple(row.get("label") for row in patches if isinstance(row, Mapping)) != labels:
        raise AdmissionError(f"{arm}: evaluator patch receipt labels mismatch")
    for index, row in enumerate(patches):
        if not isinstance(row, Mapping):
            raise AdmissionError(f"{arm}: evaluator patch cardinality receipt mismatch")
        raw_after = row.get("old_occurrences_after_raw")
        embedded = row.get("old_occurrences_embedded_in_replacement")
        if (row.get("old_occurrences_before") != 1
                or row.get("old_occurrences_after") != 0
                or raw_after != EXPECTED_EVALUATOR_RAW_OLD_AFTER[index]
                or embedded != EXPECTED_EVALUATOR_EMBEDDED_OLD[index]
                or type(raw_after) is not int or type(embedded) is not int
                or raw_after - embedded != row.get("old_occurrences_after")
                or row.get("new_occurrences_after") != 1):
            raise AdmissionError(f"{arm}: evaluator patch cardinality receipt mismatch")
        _require_hex(row.get("old_sha256"), HEX64, f"{arm} evaluator old seam")
        _require_hex(row.get("new_sha256"), HEX64, f"{arm} evaluator new seam")
    return {
        "receipt_sha256": sha256_file(receipt_path),
        "patched_sha256": patched["sha256"],
        "patched_git_blob": patched["git_blob_sha1"],
    }


def _validate_raw_shards(paths: Mapping[str, Path], arm: str, report: Mapping[str, Any]) -> dict[str, Any]:
    identity = report.get("identity") or {}
    shard_dir = paths["shards"].resolve(strict=True)
    evaluator = _validate_evaluator_receipt(shard_dir, identity, arm)
    all_games: dict[tuple[str, int, int], dict[str, Any]] = {}
    invocation_ids: list[str] = []
    shard_seed_sets: list[tuple[int, ...]] = []
    environment_rows: list[dict[str, Any]] = []
    raw_shas: dict[str, str] = {}
    for shard_path in _shard_files(shard_dir, arm):
        raw = load_json(shard_path)
        if not isinstance(raw, Mapping) or raw.get("schema_version") != 1:
            raise AdmissionError(f"{arm}: malformed raw shard {shard_path.name}")
        invocation = _require_hex(raw.get("invocation_id"), HEX32, f"{arm} invocation")
        invocation_ids.append(invocation)
        if raw.get("engine_ref") != EXPECTED_ENGINE_REF or raw.get("engine_ref") != identity.get("engine_ref"):
            raise AdmissionError(f"{arm}: engine ref mismatch in {shard_path.name}")
        engine_sha = raw.get("engine_sha256")
        if not isinstance(engine_sha, Mapping) or tuple(engine_sha.keys()) != EXPECTED_ENGINE_FILES:
            raise AdmissionError(f"{arm}: engine source domain mismatch in {shard_path.name}")
        for name in EXPECTED_ENGINE_FILES:
            _require_hex(engine_sha.get(name), HEX64, f"{arm} engine source {name}")
        if raw.get("loader_sha256") != identity.get("loader_sha256"):
            raise AdmissionError(f"{arm}: loader mismatch in {shard_path.name}")
        if raw.get("evaluator_sha256") != identity.get("evaluator_effective_sha256"):
            raise AdmissionError(f"{arm}: evaluator mismatch in {shard_path.name}")
        candidate = raw.get("candidate") or {}
        if (candidate.get("entry") != "bound_entry.py" or candidate.get("callable") != "agent"
                or candidate.get("sha256") != identity.get("entry_sha256")):
            raise AdmissionError(f"{arm}: candidate entry mismatch in {shard_path.name}")
        opponents = raw.get("opponents")
        if not isinstance(opponents, Mapping) or tuple(opponents.keys()) != EXPECTED_OPPONENTS:
            raise AdmissionError(f"{arm}: opponent order/domain mismatch in {shard_path.name}")
        expected_opp = identity.get("opponent_entry_sha256") or {}
        for name in EXPECTED_OPPONENTS:
            if not isinstance(opponents.get(name), Mapping) or opponents[name].get("sha256") != expected_opp.get(name):
                raise AdmissionError(f"{arm}: opponent digest mismatch for {name}")
        seeds = raw.get("seeds")
        if (not isinstance(seeds, list) or not seeds
                or any(not _is_int(seed) or seed not in EXPECTED_SEEDS for seed in seeds)
                or len(seeds) != len(set(seeds))):
            raise AdmissionError(f"{arm}: invalid shard seed domain in {shard_path.name}")
        shard_seed_sets.append(tuple(seeds))
        if not _is_int(raw.get("agent_rng_seed")) or raw.get("agent_rng_seed") != EXPECTED_AGENT_RNG_SEED:
            raise AdmissionError(f"{arm}: agent RNG seed mismatch in {shard_path.name}")
        if not isinstance(raw.get("python"), str) or not raw["python"].startswith("3.11."):
            raise AdmissionError(f"{arm}: Python identity mismatch in {shard_path.name}")
        if raw.get("platform") != "linux" or raw.get("method") != EXPECTED_METHOD:
            raise AdmissionError(f"{arm}: runtime identity mismatch in {shard_path.name}")
        _validate_limits(raw.get("limits"), arm, shard_path.name)
        progress = raw.get("progress") or {}
        planned = len(seeds) * len(EXPECTED_OPPONENTS) * 2
        if (progress.get("state") != "complete" or progress.get("planned_games") != planned
                or progress.get("recorded_games") != planned or progress.get("active_game") is not None
                or progress.get("recheck_requested") is not False):
            raise AdmissionError(f"{arm}: progress receipt mismatch in {shard_path.name}")
        local_keys = {
            (opponent, seed, seat)
            for opponent in EXPECTED_OPPONENTS for seed in seeds for seat in (0, 1)
        }
        found: set[tuple[str, int, int]] = set()
        games = raw.get("games")
        if not isinstance(games, list):
            raise AdmissionError(f"{arm}: games must be a list in {shard_path.name}")
        for game in games:
            if not isinstance(game, Mapping):
                raise AdmissionError(f"{arm}: non-object game in {shard_path.name}")
            key = _validate_game(game, arm)
            if key in found or key in all_games:
                raise AdmissionError(f"{arm}: duplicate raw game {key}")
            found.add(key)
            all_games[key] = dict(game)
        if found != local_keys:
            raise AdmissionError(f"{arm}: raw shard cell domain mismatch in {shard_path.name}")
        raw_shas[shard_path.name] = sha256_file(shard_path)
        environment_rows.append({
            "engine_sha256": raw.get("engine_sha256"),
            "loader_sha256": raw.get("loader_sha256"),
            "evaluator_sha256": raw.get("evaluator_sha256"),
            "limits": raw.get("limits"),
            "python": raw.get("python"),
            "platform": raw.get("platform"),
            "method": raw.get("method"),
        })
    if set(all_games) != expected_keys():
        raise AdmissionError(f"{arm}: raw shards do not cover the exact 32-cell grid")
    flattened = [seed for group in shard_seed_sets for seed in group]
    if sorted(flattened) != sorted(EXPECTED_SEEDS) or len(flattened) != len(set(flattened)):
        raise AdmissionError(f"{arm}: shard seed partition is not exact")
    report_games = report.get("games")
    if not isinstance(report_games, list):
        raise AdmissionError(f"{arm}: ARM.json games must be a list")
    report_map: dict[tuple[str, int, int], dict[str, Any]] = {}
    for game in report_games:
        if not isinstance(game, Mapping):
            raise AdmissionError(f"{arm}: non-object ARM.json game")
        key = _validate_game(game, arm)
        if key in report_map:
            raise AdmissionError(f"{arm}: duplicate ARM.json game {key}")
        report_map[key] = dict(game)
    if report_map != all_games:
        raise AdmissionError(f"{arm}: ARM.json is not byte-semantically derived from raw shards")
    return {
        "games": all_games,
        "invocation_ids": invocation_ids,
        "environment_rows": environment_rows,
        "raw_report_sha256": raw_shas,
        "evaluator": evaluator,
    }


def validate_arm(path: Path, arm: str, head: str) -> dict[str, Any]:
    report = load_json(path)
    if not isinstance(report, Mapping):
        raise AdmissionError(f"{arm}: report must be an object")
    if (report.get("schema_version") != 1 or report.get("operation") != OPERATION
            or report.get("status") != "complete" or report.get("arm") != arm):
        raise AdmissionError(f"{arm}: report identity/status mismatch")
    if tuple(report.get("seeds") or ()) != EXPECTED_SEEDS:
        raise AdmissionError(f"{arm}: report seed tuple mismatch")
    if tuple(report.get("opponents") or ()) != EXPECTED_OPPONENTS:
        raise AdmissionError(f"{arm}: report opponent tuple mismatch")
    if not _is_int(report.get("expected_cells")) or report.get("expected_cells") != EXPECTED_CELLS_PER_ARM:
        raise AdmissionError(f"{arm}: expected_cells must equal {EXPECTED_CELLS_PER_ARM}")
    gate = report.get("gate") or {}
    if (gate.get("valid") is not True or gate.get("errors") != []
            or not _is_int(gate.get("expected")) or gate.get("expected") != EXPECTED_CELLS_PER_ARM
            or not _is_int(gate.get("accepted")) or gate.get("accepted") != EXPECTED_CELLS_PER_ARM):
        raise AdmissionError(f"{arm}: arm gate is not exact and clean")
    completed = report.get("completed_shards")
    expected_partitions = (
        (0, (EXPECTED_SEEDS[0], EXPECTED_SEEDS[2])),
        (1, (EXPECTED_SEEDS[1], EXPECTED_SEEDS[3])),
    )
    if not isinstance(completed, list) or len(completed) != 2:
        raise AdmissionError(f"{arm}: expected exactly two completed shard receipts")
    normalized = []
    for row in completed:
        if (not isinstance(row, Mapping) or not _is_int(row.get("shard"))
                or not _is_int(row.get("returncode")) or row.get("returncode") != 0
                or not isinstance(row.get("seeds"), list)
                or any(not _is_int(seed) for seed in row["seeds"])):
            raise AdmissionError(f"{arm}: invalid or nonzero shard completion receipt")
        normalized.append((row["shard"], tuple(row["seeds"])))
    if tuple(sorted(normalized)) != expected_partitions:
        raise AdmissionError(f"{arm}: completed shard partition mismatch")
    identity = report.get("identity") or {}
    if identity.get("operation") != OPERATION or identity.get("arm") != arm:
        raise AdmissionError(f"{arm}: report identity object mismatch")
    if identity.get("git_head") != head or HEX40.fullmatch(head) is None:
        raise AdmissionError(f"{arm}: exact head mismatch")
    for field in (
        "entry_sha256", "materialization_receipt_sha256",
        "evaluator_source_sha256", "evaluator_effective_sha256", "loader_sha256",
    ):
        _require_hex(identity.get(field), HEX64, f"{arm} identity {field}")
    if identity.get("engine_ref") != EXPECTED_ENGINE_REF:
        raise AdmissionError(f"{arm}: engine ref mismatch")
    if Path(str(identity.get("entrypoint", ""))).name != "bound_entry.py":
        raise AdmissionError(f"{arm}: candidate entrypoint name mismatch")
    opponent_entries = identity.get("opponent_entry_sha256")
    if not isinstance(opponent_entries, Mapping) or tuple(opponent_entries.keys()) != EXPECTED_OPPONENTS:
        raise AdmissionError(f"{arm}: opponent entry identity domain mismatch")
    for name in EXPECTED_OPPONENTS:
        _require_hex(opponent_entries.get(name), HEX64, f"{arm} opponent entry {name}")
    bundles = identity.get("opponent_bundles")
    if not isinstance(bundles, Mapping) or tuple(bundles.keys()) != EXPECTED_OPPONENTS:
        raise AdmissionError(f"{arm}: opponent bundle identity domain mismatch")
    for name in EXPECTED_OPPONENTS:
        row = bundles.get(name)
        if (not isinstance(row, Mapping) or not isinstance(row.get("root"), str) or not row.get("root")
                or not _is_int(row.get("files")) or row.get("files") <= 0):
            raise AdmissionError(f"{arm}: malformed opponent bundle receipt for {name}")
        _require_hex(row.get("sha256"), HEX64, f"{arm} opponent bundle {name}")
    apex = identity.get("generated_apex_binary")
    if (not isinstance(apex, Mapping) or not _is_int(apex.get("bytes")) or apex.get("bytes") <= 0):
        raise AdmissionError(f"{arm}: compiled Apex receipt missing")
    _require_hex(apex.get("sha256"), HEX64, f"{arm} compiled Apex")
    paths = _artifact_paths(Path(path), arm)
    materialization = _validate_materialization(paths, arm, identity)
    raw = _validate_raw_shards(paths, arm, report)
    return {
        "report": dict(report),
        "identity": dict(identity),
        "paths": paths,
        "materialization": materialization,
        **raw,
    }

