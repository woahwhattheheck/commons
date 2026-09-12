#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the production-v3 action witness from witness-owned immutable snapshots.

This shell leaves the existing recorder semantics untouched. It snapshots every
executable input before the first game, makes evaluator subprocesses consume
only those snapshots, and binds the captured runtime closure into the report.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import tempfile
from typing import Any

import action_divergence_witness as base

SNAPSHOT_SCHEMA = "titan-v5-production-action-divergence-exec-snapshot/v1"


class SnapshotError(base.WitnessError):
    pass


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_digest(manifest: dict[str, str]) -> str:
    return base._digest(manifest)


def _canonical_member(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        raise SnapshotError(f"noncanonical archive member: {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SnapshotError(f"noncanonical archive member: {name!r}")
    return str(PurePosixPath(name))


def _archive_snapshot(
    source: Path,
    expected_sha256: str,
    destination: Path,
) -> tuple[Path, dict[str, str]]:
    raw = base._read_regular(source)
    expected = base._expected_sha(expected_sha256, "archive_sha256")
    actual = _sha_bytes(raw)
    if actual != expected:
        raise SnapshotError(f"archive SHA256 mismatch: {actual} != {expected}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())

    members: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tar:
            for item in tar.getmembers():
                name = _canonical_member(item.name)
                if name in members:
                    raise SnapshotError(f"duplicate archive member: {name}")
                if not item.isfile():
                    raise SnapshotError(f"archive member is not a regular file: {name}")
                stream = tar.extractfile(item)
                if stream is None:
                    raise SnapshotError(f"cannot read archive member: {name}")
                members[name] = _sha_bytes(stream.read())
    except (tarfile.TarError, OSError) as exc:
        raise SnapshotError(f"cannot inspect candidate archive: {exc}") from exc
    if "main.py" not in members:
        raise SnapshotError("candidate archive lacks main.py")
    return destination, members


def _copy_tree(source: Path, destination: Path) -> dict[str, str]:
    source = Path(source)
    if source.is_symlink():
        raise SnapshotError(f"snapshot root is a symlink: {source}")
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise SnapshotError(f"snapshot root is not an ordinary directory: {source}")
    destination.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, str] = {}

    def visit(src: Path, dst: Path, prefix: PurePosixPath) -> None:
        try:
            entries = sorted(os.scandir(src), key=lambda entry: entry.name)
        except OSError as exc:
            raise SnapshotError(f"cannot scan runtime tree {src}: {exc}") from exc
        for entry in entries:
            src_path = Path(entry.path)
            rel = prefix / entry.name
            if entry.is_symlink():
                raise SnapshotError(f"runtime tree contains symlink: {src_path}")
            if entry.is_dir(follow_symlinks=False):
                dst_path = dst / entry.name
                dst_path.mkdir()
                visit(src_path, dst_path, rel)
                continue
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise SnapshotError(f"cannot stat runtime file {src_path}: {exc}") from exc
            if not stat.S_ISREG(info.st_mode):
                raise SnapshotError(f"runtime tree contains non-regular file: {src_path}")
            data = base._read_regular(src_path)
            dst_path = dst / entry.name
            with dst_path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            manifest[rel.as_posix()] = _sha_bytes(data)

    visit(source, destination, PurePosixPath())
    return manifest


def _capture_control_file(
    source: Path,
    expected_sha256: str,
    destination_root: Path,
) -> tuple[Path, dict[str, str]]:
    source = source.resolve(strict=True)
    manifest = _copy_tree(source.parent, destination_root)
    captured = destination_root / source.name
    expected = base._expected_sha(expected_sha256, source.name)
    actual = manifest.get(source.name)
    if actual != expected:
        raise SnapshotError(
            f"captured {source.name} SHA256 mismatch: {actual} != {expected}"
        )
    return captured, manifest


def _pack_adapter_targets(source: bytes, path: Path) -> tuple[Path, Path]:
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SnapshotError(f"cannot parse agent adapter {path}: {exc}") from exc

    contract_paths: list[str] = []
    main_paths: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            node.func.attr == "spec_from_file_location"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "kag_pack_contract"
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            contract_paths.append(node.args[1].value)
        if (
            node.func.attr == "make_agent"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            main_paths.append(node.args[0].value)

    if len(set(contract_paths)) != 1 or len(set(main_paths)) != 1:
        raise SnapshotError(
            "agent adapter must expose exactly one pinned kag_pack_contract and main path"
        )
    contract = Path(contract_paths[0])
    main = Path(main_paths[0])
    if not contract.is_absolute() or not main.is_absolute():
        raise SnapshotError("agent adapter runtime paths must be absolute")
    contract = contract.resolve(strict=True)
    main = main.resolve(strict=True)
    base._read_regular(contract)
    base._read_regular(main)
    if main.name != "main.py":
        raise SnapshotError("agent adapter must target archive-root main.py")
    return contract, main


def _deterministic_adapter(contract_name: str, main_name: str) -> bytes:
    if "/" in contract_name or "/" in main_name:
        raise SnapshotError("snapshot entry filenames must be single path components")
    return (
        "import importlib.util as _util\n"
        "from pathlib import Path as _Path\n"
        "_runner = None\n"
        "def agent(observation, configuration=None):\n"
        "    global _runner\n"
        "    if _runner is None:\n"
        "        _root = _Path(__file__).resolve().parent\n"
        f"        spec = _util.spec_from_file_location('kag_pack_contract', _root / 'contract' / {contract_name!r})\n"
        "        module = _util.module_from_spec(spec)\n"
        "        spec.loader.exec_module(module)\n"
        f"        _runner = module.make_agent(_root / 'candidate' / {main_name!r})\n"
        "    return _runner(observation, configuration or {})\n"
    ).encode("utf-8")


def _capture_agent(
    spec_text: str,
    destination: Path,
    *,
    archive_members: dict[str, str] | None,
) -> tuple[str, dict[str, Any]]:
    path_text, sep, callable_name = spec_text.partition("::")
    if not path_text or (sep and not callable_name):
        raise SnapshotError(f"invalid agent spec: {spec_text!r}")
    callable_name = callable_name if sep else "agent"
    if callable_name != "agent":
        raise SnapshotError("immutable witness currently requires the canonical agent callable")

    source_path = Path(path_text).resolve(strict=True)
    source = base._read_regular(source_path)
    source_sha256 = _sha_bytes(source)
    contract, main = _pack_adapter_targets(source, source_path)

    destination.mkdir(parents=True, exist_ok=False)
    candidate_manifest = _copy_tree(main.parent, destination / "candidate")
    contract_manifest = _copy_tree(contract.parent, destination / "contract")

    if archive_members is not None and candidate_manifest != archive_members:
        missing = sorted(set(archive_members) - set(candidate_manifest))[:5]
        extra = sorted(set(candidate_manifest) - set(archive_members))[:5]
        drift = sorted(
            name
            for name in set(candidate_manifest) & set(archive_members)
            if candidate_manifest[name] != archive_members[name]
        )[:5]
        raise SnapshotError(
            "captured candidate runtime differs from authenticated archive "
            f"(missing={missing}, extra={extra}, drift={drift})"
        )

    entry = destination / "entry.py"
    entry_bytes = _deterministic_adapter(contract.name, main.name)
    with entry.open("xb") as handle:
        handle.write(entry_bytes)
        handle.flush()
        os.fsync(handle.fileno())

    candidate_manifest_sha = _manifest_digest(candidate_manifest)
    archive_manifest_sha = (
        _manifest_digest(archive_members) if archive_members is not None else None
    )
    meta = {
        "source_entry_sha256": source_sha256,
        "snapshot_entry_sha256": _sha_bytes(entry_bytes),
        "candidate_files": candidate_manifest,
        "candidate_manifest_sha256": candidate_manifest_sha,
        "contract_files": contract_manifest,
        "contract_manifest_sha256": _manifest_digest(contract_manifest),
        "archive_member_manifest_sha256": archive_manifest_sha,
        "archive_members_verified": (
            archive_members is not None and candidate_manifest_sha == archive_manifest_sha
        ),
    }
    return f"{entry}::agent", meta


def _capture_execution(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=False)

    evaluator_path, evaluator_files = _capture_control_file(
        Path(args.evaluator),
        args.expected_evaluator_sha256,
        root / "control" / "evaluator",
    )
    loader_path, loader_files = _capture_control_file(
        Path(args.loader),
        args.expected_loader_sha256,
        root / "control" / "loader",
    )
    engine_files = _copy_tree(
        Path(args.engine_dir),
        root / "control" / "engine",
    )

    left_archive, left_members = _archive_snapshot(
        Path(args.left_archive),
        args.left_archive_sha256,
        root / "archives" / "left.tar.gz",
    )
    right_archive, right_members = _archive_snapshot(
        Path(args.right_archive),
        args.right_archive_sha256,
        root / "archives" / "right.tar.gz",
    )

    left_spec, left_meta = _capture_agent(
        args.left_candidate,
        root / "agents" / "left",
        archive_members=left_members,
    )
    right_spec, right_meta = _capture_agent(
        args.right_candidate,
        root / "agents" / "right",
        archive_members=right_members,
    )
    opponent_spec, opponent_meta = _capture_agent(
        args.opponent,
        root / "agents" / "opponent",
        archive_members=None,
    )

    return {
        "evaluator": evaluator_path,
        "loader": loader_path,
        "engine_dir": root / "control" / "engine",
        "left_archive": left_archive,
        "right_archive": right_archive,
        "left_candidate": left_spec,
        "right_candidate": right_spec,
        "opponent": opponent_spec,
        "authority": {
            "schema": SNAPSHOT_SCHEMA,
            "control": {
                "evaluator_files": evaluator_files,
                "evaluator_manifest_sha256": _manifest_digest(evaluator_files),
                "loader_files": loader_files,
                "loader_manifest_sha256": _manifest_digest(loader_files),
                "engine_files": engine_files,
                "engine_manifest_sha256": _manifest_digest(engine_files),
            },
            "left": left_meta,
            "right": right_meta,
            "opponent": opponent_meta,
        },
    }


def run_witness(args: argparse.Namespace) -> dict[str, Any]:
    # Capture source-entry identities before any game and never re-read originals
    # after the snapshot is made.
    original_entries = {
        "left": _sha_bytes(base._read_regular(base._spec_path(args.left_candidate))),
        "right": _sha_bytes(base._read_regular(base._spec_path(args.right_candidate))),
        "opponent": _sha_bytes(base._read_regular(base._spec_path(args.opponent))),
    }

    with tempfile.TemporaryDirectory(prefix="titan-action-witness-snapshot-") as tmp:
        snapshot = _capture_execution(args, Path(tmp) / "runtime")
        frozen = argparse.Namespace(**vars(args))
        frozen.evaluator = snapshot["evaluator"]
        frozen.loader = snapshot["loader"]
        frozen.engine_dir = snapshot["engine_dir"]
        frozen.left_archive = snapshot["left_archive"]
        frozen.right_archive = snapshot["right_archive"]
        frozen.left_candidate = snapshot["left_candidate"]
        frozen.right_candidate = snapshot["right_candidate"]
        frozen.opponent = snapshot["opponent"]

        report = base.run_witness(frozen)

        exec_authority = snapshot["authority"]
        exec_authority["control"]["engine_sha256"] = report["authority"]["engine_sha256"]
        for side, field in (
            ("left", "left_entry_sha256"),
            ("right", "right_entry_sha256"),
            ("opponent", "opponent_entry_sha256"),
        ):
            observed_snapshot_sha = report["authority"][field]
            expected_snapshot_sha = exec_authority[side]["snapshot_entry_sha256"]
            if observed_snapshot_sha != expected_snapshot_sha:
                raise SnapshotError(
                    f"{side} executed snapshot entry drift: "
                    f"{observed_snapshot_sha} != {expected_snapshot_sha}"
                )
            source_sha = exec_authority[side]["source_entry_sha256"]
            if source_sha != original_entries[side]:
                raise SnapshotError(f"{side} source adapter moved during capture")
            report["authority"][field] = source_sha

        report["authority"]["execution_snapshot"] = exec_authority
        report["authority_sha256"] = base._digest(report["authority"])
        report.pop("report_sha256", None)
        report["report_sha256"] = base._digest(report)
        return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--expected-evaluator-sha256", required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--expected-loader-sha256", required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--left-candidate", required=True)
    parser.add_argument("--right-candidate", required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--left-label", required=True)
    parser.add_argument("--right-label", required=True)
    parser.add_argument("--opponent-label", required=True)
    parser.add_argument("--left-archive", type=Path, required=True)
    parser.add_argument("--left-archive-sha256", required=True)
    parser.add_argument("--right-archive", type=Path, required=True)
    parser.add_argument("--right-archive-sha256", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--rng-seed", type=int, default=20260912)
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--action-timeout", type=float, default=1.25)
    parser.add_argument("--startup-timeout", type=float, default=10.0)
    parser.add_argument("--game-timeout", type=float, default=900.0)
    parser.add_argument("--window-radius", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = run_witness(args)
        base._atomic_write(args.output, report)
    except (base.WitnessError, SnapshotError, OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"immutable_action_divergence_witness: {exc}", file=os.sys.stderr)
        return 2
    print(json.dumps({
        "report_sha256": report["report_sha256"],
        "authority_sha256": report["authority_sha256"],
        "snapshot_schema": report["authority"]["execution_snapshot"]["schema"],
        "rows": [
            {
                "candidate_seat": row["candidate_seat"],
                "left_scores": row["left_result"].get("scores"),
                "right_scores": row["right_result"].get("scores"),
                "first_candidate_action_divergence_step":
                    row["comparison"]["first_candidate_action_divergence_step"],
                "candidate_action_is_first_observed_divergence":
                    row["comparison"]["candidate_action_is_first_observed_divergence"],
            }
            for row in report["rows"]
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
