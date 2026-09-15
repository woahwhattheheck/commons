"""Submission packaging with a strict real-fold gate and explicit fixture path."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence
import zipfile

import numpy as np

try:
    from .contract import (
        BundleReceipt,
        ContractError,
        D3D_PUBLIC_TEST_SHOTS,
        HF_DATASET,
        MAST_PUBLIC_TEST_SHOTS,
        OFFICIAL_STARTER_SHA,
        Prediction,
        contract_snapshot,
    )
    from .npz_packaging import compile_submission_npz, read_npz_strict, validate_prediction_arrays
except ImportError:
    from contract import (
        BundleReceipt,
        ContractError,
        D3D_PUBLIC_TEST_SHOTS,
        HF_DATASET,
        MAST_PUBLIC_TEST_SHOTS,
        OFFICIAL_STARTER_SHA,
        Prediction,
        contract_snapshot,
    )
    from npz_packaging import compile_submission_npz, read_npz_strict, validate_prediction_arrays


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PublicFoldManifest:
    machine: str
    config: str
    lengths: tuple[int, ...]
    source_receipt_sha256: str
    sha256: str


def _canonical_json_bytes(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _load_json_strict(path: Path) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ContractError(f"duplicate manifest key {key!r}")
            out[key] = value
        return out
    try:
        value = json.loads(path.read_text("utf-8"), object_pairs_hook=pairs)
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError(f"invalid manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("manifest must be an object")
    return value


def _fold_contract(machine: str) -> tuple[str, int]:
    if machine == "DIII-D":
        return "diii_d_public_test", D3D_PUBLIC_TEST_SHOTS
    if machine == "MAST":
        return "mast_public_test", MAST_PUBLIC_TEST_SHOTS
    raise ContractError(f"unknown machine {machine}")


def _fold_payload(machine: str, config: str, lengths: Sequence[int], source_receipt_sha256: str) -> dict:
    return {
        "schema": "sophelio-fusion-equilibrium/public-fold-lengths-v1",
        "machine": machine,
        "config": config,
        "dataset": HF_DATASET,
        "starter_sha": OFFICIAL_STARTER_SHA,
        "shots": len(lengths),
        "lengths": [int(v) for v in lengths],
        "source_receipt_sha256": source_receipt_sha256,
    }


def _manifest_from_lengths(
    machine: str,
    lengths: Sequence[int],
    source_receipt_sha256: str,
) -> PublicFoldManifest:
    config, expected = _fold_contract(machine)
    if not _SHA256_RE.fullmatch(str(source_receipt_sha256)):
        raise ContractError("source receipt must be lowercase SHA-256")
    normalized = tuple(int(v) for v in lengths)
    if len(normalized) != expected:
        raise ContractError(f"{machine} fold has {len(normalized)} shots, expected {expected}")
    if any(v <= 0 for v in normalized):
        raise ContractError("public-test shot lengths must be positive")
    payload = _fold_payload(machine, config, normalized, source_receipt_sha256)
    digest = sha256(_canonical_json_bytes(payload)).hexdigest()
    return PublicFoldManifest(machine, config, normalized, source_receipt_sha256, digest)


def capture_public_test_lengths(
    rows: Iterable[Mapping[str, object]],
    machine: str,
    *,
    source_receipt_sha256: str,
) -> PublicFoldManifest:
    """Capture T from streamed public-test rows; raw caller length lists are not accepted."""
    _, expected = _fold_contract(machine)
    lengths: list[int] = []
    for row in rows:
        if not isinstance(row, Mapping) or "efit_times" not in row:
            raise ContractError("public-test row missing efit_times")
        times = np.asarray(row["efit_times"], dtype=np.float64)
        if times.ndim != 1 or times.size < 1 or not np.isfinite(times).all():
            raise ContractError("invalid public-test efit_times")
        lengths.append(int(times.size))
        if len(lengths) > expected:
            raise ContractError(f"{machine} public-test stream has extra shots")
    return _manifest_from_lengths(machine, lengths, source_receipt_sha256)


def _validate_fold_manifest(
    fold: PublicFoldManifest,
    machine: str,
    expected_sha256: str,
) -> None:
    if not isinstance(fold, PublicFoldManifest):
        raise ContractError("real bundle requires a retained PublicFoldManifest")
    rebuilt = _manifest_from_lengths(fold.machine, fold.lengths, fold.source_receipt_sha256)
    expected_config, expected_count = _fold_contract(machine)
    if fold.machine != machine or fold.config != expected_config:
        raise ContractError("public-fold machine/config drift")
    if len(fold.lengths) != expected_count:
        raise ContractError("public-fold shot-count drift")
    if fold.sha256 != rebuilt.sha256:
        raise ContractError("public-fold manifest digest drift")
    if not _SHA256_RE.fullmatch(str(expected_sha256)) or fold.sha256 != expected_sha256:
        raise ContractError("public-fold retained root mismatch")


def _write_direct_zip(out: Path, d3d: Path, mast: Path) -> str:
    submission = out / "submission.zip"
    with zipfile.ZipFile(submission, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in (d3d.name, mast.name):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, (out / name).read_bytes())
    return sha256(submission.read_bytes()).hexdigest()


def _verify_direct_zip(out: Path, direct: object) -> None:
    submission = out / "submission.zip"
    if not isinstance(direct, dict) or direct.get("name") != submission.name:
        raise ContractError("direct submission receipt drift")
    if not submission.is_file() or sha256(submission.read_bytes()).hexdigest() != direct.get("sha256"):
        raise ContractError("direct submission zip digest mismatch")
    try:
        with zipfile.ZipFile(submission, "r") as zf:
            names = zf.namelist()
            if names != ["diii_d_public_test.npz", "mast_public_test.npz"]:
                raise ContractError(f"direct submission member drift: {names}")
            for name in names:
                if zf.read(name) != (out / name).read_bytes():
                    raise ContractError(f"direct submission member bytes drift: {name}")
    except zipfile.BadZipFile as exc:
        raise ContractError("invalid direct submission zip") from exc


def compile_real_bundle(
    out_dir: Path | str,
    d3d_predictions: Sequence[Prediction],
    d3d_fold: PublicFoldManifest,
    mast_predictions: Sequence[Prediction],
    mast_fold: PublicFoldManifest,
    *,
    expected_d3d_fold_sha256: str,
    expected_mast_fold_sha256: str,
) -> BundleReceipt:
    """Build the terminal two-NPZ artifact only from retained full-fold manifests."""
    _validate_fold_manifest(d3d_fold, "DIII-D", expected_d3d_fold_sha256)
    _validate_fold_manifest(mast_fold, "MAST", expected_mast_fold_sha256)
    if len(d3d_predictions) != D3D_PUBLIC_TEST_SHOTS:
        raise ContractError("DIII-D predictions do not cover the complete public test fold")
    if len(mast_predictions) != MAST_PUBLIC_TEST_SHOTS:
        raise ContractError("MAST predictions do not cover the complete public test fold")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    d3d = out / "diii_d_public_test.npz"
    mast = out / "mast_public_test.npz"
    d3d_sha = compile_submission_npz(d3d, d3d_predictions, d3d_fold.lengths, "DIII-D")
    mast_sha = compile_submission_npz(mast, mast_predictions, mast_fold.lengths, "MAST")
    submission_sha = _write_direct_zip(out, d3d, mast)

    manifest = {
        "schema": "sophelio-fusion-equilibrium/tjlabs-real-bundle-v2",
        "contract": contract_snapshot(),
        "folds": {
            d3d_fold.config: {**_fold_payload(d3d_fold.machine, d3d_fold.config, d3d_fold.lengths, d3d_fold.source_receipt_sha256), "sha256": d3d_fold.sha256},
            mast_fold.config: {**_fold_payload(mast_fold.machine, mast_fold.config, mast_fold.lengths, mast_fold.source_receipt_sha256), "sha256": mast_fold.sha256},
        },
        "files": {
            d3d.name: {"sha256": d3d_sha, "shots": D3D_PUBLIC_TEST_SHOTS, "fold_sha256": d3d_fold.sha256},
            mast.name: {"sha256": mast_sha, "shots": MAST_PUBLIC_TEST_SHOTS, "fold_sha256": mast_fold.sha256},
        },
        "direct_submission_zip": {"name": "submission.zip", "sha256": submission_sha},
        "truth": {
            "fixture_only": False,
            "codabench_submission_performed": False,
            "leaderboard_score_known": False,
            "award_or_payment_received": False,
        },
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    (out / "manifest.json").write_bytes(manifest_bytes)
    manifest_sha = sha256(manifest_bytes).hexdigest()
    return BundleReceipt(d3d_sha, mast_sha, manifest_sha, submission_sha)


def _fold_from_json(value: object) -> PublicFoldManifest:
    if not isinstance(value, dict):
        raise ContractError("fold manifest must be an object")
    required = {
        "schema", "machine", "config", "dataset", "starter_sha",
        "shots", "lengths", "source_receipt_sha256", "sha256",
    }
    if set(value) != required:
        raise ContractError("fold manifest shape drift")
    lengths = value.get("lengths")
    if not isinstance(lengths, list) or any(isinstance(v, bool) or not isinstance(v, int) for v in lengths):
        raise ContractError("fold lengths malformed")
    fold = _manifest_from_lengths(str(value["machine"]), lengths, str(value["source_receipt_sha256"]))
    if value["schema"] != "sophelio-fusion-equilibrium/public-fold-lengths-v1":
        raise ContractError("fold schema drift")
    if value["config"] != fold.config or value["dataset"] != HF_DATASET or value["starter_sha"] != OFFICIAL_STARTER_SHA:
        raise ContractError("fold source identity drift")
    if value["shots"] != len(fold.lengths) or value["sha256"] != fold.sha256:
        raise ContractError("fold receipt drift")
    return fold


def verify_real_bundle(
    out_dir: Path | str,
    *,
    expected_d3d_fold_sha256: str,
    expected_mast_fold_sha256: str,
) -> dict:
    out = Path(out_dir)
    manifest = _load_json_strict(out / "manifest.json")
    if manifest.get("schema") != "sophelio-fusion-equilibrium/tjlabs-real-bundle-v2":
        raise ContractError("wrong real manifest schema")
    if manifest.get("contract") != contract_snapshot():
        raise ContractError("contract snapshot drift")
    folds = manifest.get("folds")
    if not isinstance(folds, dict) or set(folds) != {"diii_d_public_test", "mast_public_test"}:
        raise ContractError("fold set drift")
    d3d_fold = _fold_from_json(folds["diii_d_public_test"])
    mast_fold = _fold_from_json(folds["mast_public_test"])
    _validate_fold_manifest(d3d_fold, "DIII-D", expected_d3d_fold_sha256)
    _validate_fold_manifest(mast_fold, "MAST", expected_mast_fold_sha256)

    expected_files = {
        "diii_d_public_test.npz": ("DIII-D", d3d_fold, D3D_PUBLIC_TEST_SHOTS),
        "mast_public_test.npz": ("MAST", mast_fold, MAST_PUBLIC_TEST_SHOTS),
    }
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(expected_files):
        raise ContractError("manifest file set drift")
    for name, (machine, fold, shots) in expected_files.items():
        meta = files[name]
        if not isinstance(meta, dict) or set(meta) != {"sha256", "shots", "fold_sha256"}:
            raise ContractError(f"file receipt shape drift for {name}")
        path = out / name
        if meta["shots"] != shots or meta["fold_sha256"] != fold.sha256:
            raise ContractError(f"file completeness receipt drift for {name}")
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
            raise ContractError(f"digest mismatch for {name}")
        arrays = read_npz_strict(path)
        validate_prediction_arrays(arrays, fold.lengths, machine)

    _verify_direct_zip(out, manifest.get("direct_submission_zip"))
    if manifest.get("truth") != {
        "fixture_only": False,
        "codabench_submission_performed": False,
        "leaderboard_score_known": False,
        "award_or_payment_received": False,
    }:
        raise ContractError("truth boundary drift")
    return manifest


def compile_bundle(
    out_dir: Path | str,
    d3d_predictions: Sequence[Prediction],
    d3d_lengths: Sequence[int],
    mast_predictions: Sequence[Prediction],
    mast_lengths: Sequence[int],
) -> BundleReceipt:
    """Synthetic/partial fixture helper. Its output is never terminal submission evidence."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    d3d = out / "diii_d_public_test.npz"
    mast = out / "mast_public_test.npz"
    d3d_sha = compile_submission_npz(d3d, d3d_predictions, d3d_lengths, "DIII-D")
    mast_sha = compile_submission_npz(mast, mast_predictions, mast_lengths, "MAST")
    submission_sha = _write_direct_zip(out, d3d, mast)
    manifest = {
        "schema": "sophelio-fusion-equilibrium/tjlabs-fixture-bundle-v2",
        "contract": contract_snapshot(),
        "files": {
            d3d.name: {"sha256": d3d_sha, "shots": len(d3d_lengths)},
            mast.name: {"sha256": mast_sha, "shots": len(mast_lengths)},
        },
        "direct_submission_zip": {"name": "submission.zip", "sha256": submission_sha},
        "truth": {
            "fixture_only": True,
            "codabench_submission_performed": False,
            "leaderboard_score_known": False,
            "award_or_payment_received": False,
        },
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    (out / "manifest.json").write_bytes(manifest_bytes)
    manifest_sha = sha256(manifest_bytes).hexdigest()
    return BundleReceipt(d3d_sha, mast_sha, manifest_sha, submission_sha)


def verify_bundle(out_dir: Path | str) -> dict:
    """Verify only a fixture bundle; use ``verify_real_bundle`` for terminal artifacts."""
    out = Path(out_dir)
    manifest = _load_json_strict(out / "manifest.json")
    if manifest.get("schema") != "sophelio-fusion-equilibrium/tjlabs-fixture-bundle-v2":
        raise ContractError("wrong fixture manifest schema")
    if manifest.get("contract") != contract_snapshot():
        raise ContractError("contract snapshot drift")
    expected = {"diii_d_public_test.npz", "mast_public_test.npz"}
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != expected:
        raise ContractError("manifest file set drift")
    for name in sorted(expected):
        path = out / name
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != files[name].get("sha256"):
            raise ContractError(f"digest mismatch for {name}")
    _verify_direct_zip(out, manifest.get("direct_submission_zip"))
    if manifest.get("truth") != {
        "fixture_only": True,
        "codabench_submission_performed": False,
        "leaderboard_score_known": False,
        "award_or_payment_received": False,
    }:
        raise ContractError("fixture truth boundary drift")
    return manifest
