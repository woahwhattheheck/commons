"""Contract-exact two-NPZ direct-upload ZIP plus external provenance receipt."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from typing import Sequence
import zipfile
try:
    from .contract import BundleReceipt, ContractError, Prediction, contract_snapshot
    from .npz_packaging import compile_submission_npz
except ImportError:
    from contract import BundleReceipt, ContractError, Prediction, contract_snapshot
    from npz_packaging import compile_submission_npz


def _canonical_json_bytes(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def compile_bundle(
    out_dir: Path | str,
    d3d_predictions: Sequence[Prediction],
    d3d_lengths: Sequence[int],
    mast_predictions: Sequence[Prediction],
    mast_lengths: Sequence[int],
) -> BundleReceipt:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    d3d = out / "diii_d_public_test.npz"
    mast = out / "mast_public_test.npz"
    d3d_sha = compile_submission_npz(d3d, d3d_predictions, d3d_lengths, "DIII-D")
    mast_sha = compile_submission_npz(mast, mast_predictions, mast_lengths, "MAST")

    # Organizer direct-upload contract: ZIP root contains exactly these two NPZs.
    submission = out / "submission.zip"
    with zipfile.ZipFile(submission, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in (d3d.name, mast.name):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, (out / name).read_bytes())
    submission_sha = sha256(submission.read_bytes()).hexdigest()

    # Provenance metadata is deliberately external to the upload ZIP.
    manifest = {
        "schema": "sophelio-fusion-equilibrium/tjlabs-bundle-v1",
        "contract": contract_snapshot(),
        "files": {
            d3d.name: {"sha256": d3d_sha, "shots": len(d3d_lengths)},
            mast.name: {"sha256": mast_sha, "shots": len(mast_lengths)},
        },
        "direct_submission_zip": {"name": submission.name, "sha256": submission_sha},
        "truth": {
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
    out = Path(out_dir)
    try:
        manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    except Exception as exc:
        raise ContractError(f"invalid manifest: {exc}") from exc
    if manifest.get("schema") != "sophelio-fusion-equilibrium/tjlabs-bundle-v1":
        raise ContractError("wrong manifest schema")
    if manifest.get("contract") != contract_snapshot():
        raise ContractError("contract snapshot drift")
    expected = {"diii_d_public_test.npz", "mast_public_test.npz"}
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != expected:
        raise ContractError("manifest file set drift")
    for name in sorted(expected):
        p = out / name
        if not p.is_file() or sha256(p.read_bytes()).hexdigest() != files[name].get("sha256"):
            raise ContractError(f"digest mismatch for {name}")

    submission = out / "submission.zip"
    direct = manifest.get("direct_submission_zip")
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

    if manifest.get("truth") != {
        "codabench_submission_performed": False,
        "leaderboard_score_known": False,
        "award_or_payment_received": False,
    }:
        raise ContractError("truth boundary drift")
    return manifest
