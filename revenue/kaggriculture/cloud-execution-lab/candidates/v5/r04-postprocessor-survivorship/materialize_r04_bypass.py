#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize an R04 semantic-bypass survivorship arm from exact V5 production recovery."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile

BASELINE_ARCHIVE_SHA256 = "0aded66a2c393cc60f4f45d10f11c384a7e788182bf5430863829a02b66daf02"
BASELINE_CONFIG_SHA256 = "ba18563683125fd89d5473ddb8a5c3e9431db1787a3046f618a9e03af2cb44af"
TREATMENT_CONFIG_SHA256 = "f32890231e5ea0b082ffdb6e2e9dbf65450172488e023f51314fc1aff059ff2f"
CONFIG_PATH = "TITAN-CONFIG.json"
SCHEMA = "titan-v5-production-recovery-r04-bypass-survivorship/v2"

# Bind the semantic interpretation to the exact executable members of 0aded.
# The whole-archive SHA already authenticates these bytes; this explicit map
# makes the topology theorem reviewable and fail-closed if a later baseline is
# substituted without re-proving the call graph.
SEMANTIC_MEMBER_SHA256 = {
    "main.py": "85c13e55696a702ab1e292386dc16af118ae4f916000f935c9bc46a18aea34fa",
    "titan_runtime.py": "7fefc550cf2b1ee73995616321bf4824755f075125221a03bdc5d83db1ee22ab",
    "frozen_selected.py": "5ca1bc39efed756de71207f46926744ea69f9d2f300dd7b9c1a8cc4dbefeb9ef",
    "scheduler.py": "00d72a5c6b511e73ed1923ea402c4a36e0f9490f3b4c177490ddc72440f4a64a",
    "r04_full_router.py": "41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a",
}
SEMANTIC_ANCHORS = {
    "titan_runtime.py": (
        b"self.consumer = FrozenSelected()",
        b"self.controller = self.consumer.controller",
        b"self.production = self.controller",
        b"if self.features.consumer == 'frozen' else deepcopy(selected)",
    ),
    "frozen_selected.py": (
        b"class FrozenSelected(SellScheduler):",
    ),
    "scheduler.py": (
        b"self.controller=parent.Agent()",
    ),
}

# Submitted V3.1 carried these values, but its active R04 fast-return bypassed
# the canonical consumer/postprocessor path. Production recovery restores R04
# inside the V4 runtime, so these shared values become executable around R04.
# This one aggregate arm asks whether those retained postprocessors survive
# composition at all before any single-feature localization is justified.
CHANGES = {
    "consumer": ("frozen", "parent"),
    "seed": (True, False),
    "funding": (True, False),
    "redundant_hire": (True, False),
    "market_pressure": (True, False),
    "operating_stock": (True, False),
    "idle_fertilizer": (True, False),
    "crop_release": (True, False),
    "early_capital": (True, False),
    "town_procurement": (True, False),
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_archive_bytes(raw: bytes, expected_sha256: str) -> dict[str, bytes]:
    if type(raw) is not bytes:
        raise TypeError("archive snapshot must be bytes")
    actual = digest(raw)
    if actual != expected_sha256:
        raise ValueError(f"Archive identity mismatch: expected {expected_sha256}, got {actual}")
    result: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for member in archive.getmembers():
            name = member.name
            rel = PurePosixPath(name)
            if (
                not member.isfile()
                or not name
                or name in result
                or rel.is_absolute()
                or ".." in rel.parts
                or "\\" in name
                or str(rel) != name
            ):
                raise ValueError("Noncanonical archive member: " + name)
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("Missing archive member bytes: " + name)
            result[name] = stream.read()
    if not result:
        raise ValueError("Archive is empty")
    return result


def archive_members(path: Path) -> dict[str, bytes]:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Baseline must be an ordinary file: {path}")
    return parse_archive_bytes(path.read_bytes(), BASELINE_ARCHIVE_SHA256)


def archive_bytes(files: dict[str, bytes]) -> bytes:
    if not files:
        raise ValueError("Cannot create an empty archive")
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        for name, body in sorted(files.items()):
            rel = PurePosixPath(name)
            if (
                type(body) is not bytes
                or not name
                or rel.is_absolute()
                or ".." in rel.parts
                or "\\" in name
                or str(rel) != name
            ):
                raise ValueError("Noncanonical output member: " + str(name))
            info = tarfile.TarInfo(name)
            info.size = len(body)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(body))
    packed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=packed, mtime=0) as zipped:
        zipped.write(raw.getvalue())
    return packed.getvalue()


def verify_semantic_topology(
    baseline: dict[str, bytes],
    expected_hashes: dict[str, str] | None = None,
    anchors: dict[str, tuple[bytes, ...]] | None = None,
) -> None:
    expected_hashes = SEMANTIC_MEMBER_SHA256 if expected_hashes is None else expected_hashes
    anchors = SEMANTIC_ANCHORS if anchors is None else anchors
    for name, expected in expected_hashes.items():
        body = baseline.get(name)
        if body is None:
            raise ValueError(f"Baseline is missing semantic member {name}")
        if digest(body) != expected:
            raise ValueError(f"Semantic member identity mismatch: {name}")
    for name, required in anchors.items():
        body = baseline.get(name)
        if body is None:
            raise ValueError(f"Baseline is missing semantic member {name}")
        for anchor in required:
            if body.count(anchor) != 1:
                raise ValueError(f"Semantic topology anchor mismatch: {name}: {anchor!r}")


def treatment_members(baseline: dict[str, bytes]) -> dict[str, bytes]:
    if CONFIG_PATH not in baseline:
        raise ValueError("Baseline archive is missing TITAN-CONFIG.json")
    original = baseline[CONFIG_PATH]
    if digest(original) != BASELINE_CONFIG_SHA256:
        raise ValueError("Baseline config is not the exact production-recovery config")
    config = json.loads(original)
    if not isinstance(config, dict):
        raise ValueError("TITAN-CONFIG.json must contain a JSON object")
    for key, (before, _after) in CHANGES.items():
        value = config.get(key)
        if type(value) is not type(before) or value != before:
            raise ValueError(f"Baseline {key} does not match authenticated preimage")

    for key, (_before, after) in CHANGES.items():
        config[key] = after
    changed = json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    if digest(changed) != TREATMENT_CONFIG_SHA256:
        raise AssertionError("R04-bypass config bytes drifted from authenticated treatment")

    treatment = dict(baseline)
    treatment[CONFIG_PATH] = changed
    if set(treatment) != set(baseline):
        raise AssertionError("Treatment changed archive membership")
    diffs = sorted(name for name in baseline if baseline[name] != treatment[name])
    if diffs != [CONFIG_PATH]:
        raise AssertionError(f"Treatment changed unexpected members: {diffs}")
    for name in baseline:
        if name != CONFIG_PATH and baseline[name] != treatment[name]:
            raise AssertionError(f"Treatment changed retained member: {name}")
    return treatment


def receipt_for(baseline: dict[str, bytes], treatment: dict[str, bytes], packed: bytes) -> dict:
    if set(baseline) != set(treatment):
        raise ValueError("Receipt inputs have different member sets")
    changed = sorted(name for name in baseline if baseline[name] != treatment[name])
    if changed != [CONFIG_PATH]:
        raise ValueError(f"Unexpected treatment member delta: {changed}")
    return {
        "schema": SCHEMA,
        "baseline_archive_sha256": BASELINE_ARCHIVE_SHA256,
        "baseline_config_sha256": BASELINE_CONFIG_SHA256,
        "semantic_topology": {
            "status": "AUTHENTICATED",
            "members": dict(sorted(SEMANTIC_MEMBER_SHA256.items())),
        },
        "treatment": {
            "name": "r04_semantic_bypass",
            "config_changes": {
                key: {"before": before, "after": after}
                for key, (before, after) in CHANGES.items()
            },
            "config_sha256": TREATMENT_CONFIG_SHA256,
            "archive_sha256": digest(packed),
        },
        "member_count": len(treatment),
        "changed_members": changed,
        "baseline_members": {name: digest(body) for name, body in sorted(baseline.items())},
        "treatment_members": {name: digest(body) for name, body in sorted(treatment.items())},
        "native_economics_status": "PENDING_BASE_PRODUCTION_PANEL",
        "interpretation": (
            "Aggregate survivorship only: suppress canonical V4 consumer/postprocessors "
            "that submitted V3.1 R04 bypassed; preserve exact R04 + carrot/delivery package bytes."
        ),
        "kaggle_submission_hold": True,
    }


def _receipt_bytes(receipt: dict) -> bytes:
    return (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")


def publish_pair(out: Path, receipt_path: Path, packed: bytes, receipt: dict) -> None:
    """Publish receipt first, then atomically link a fully-written archive.

    A path race can therefore leave at worst a receipt without an archive, never
    a runnable treatment archive without its complete receipt. The archive is
    staged on the destination filesystem and linked create-only.
    """
    out = Path(out)
    receipt_path = Path(receipt_path)
    if out == receipt_path:
        raise ValueError("archive and receipt paths must differ")
    if out.exists() or out.is_symlink() or receipt_path.exists() or receipt_path.is_symlink():
        raise FileExistsError("Use fresh archive and receipt paths")
    out.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_raw = _receipt_bytes(receipt)

    fd, temp_name = tempfile.mkstemp(prefix=out.name + ".stage.", dir=out.parent)
    temp_path = Path(temp_name)
    receipt_published = False
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(packed)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, 0o644)

        with receipt_path.open("xb") as stream:
            stream.write(receipt_raw)
            stream.flush()
            os.fsync(stream.fileno())
        receipt_published = True

        try:
            os.link(temp_path, out)
        except BaseException:
            # Remove only the exact receipt bytes this invocation published.
            try:
                if receipt_path.read_bytes() == receipt_raw:
                    receipt_path.unlink()
                    receipt_published = False
            except OSError:
                pass
            raise
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

    if not receipt_published or not out.is_file() or out.is_symlink():
        raise RuntimeError("Treatment pair publication did not complete")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    if args.out == args.receipt:
        parser.error("--out and --receipt must be different paths")
    if args.out.exists() or args.out.is_symlink() or args.receipt.exists() or args.receipt.is_symlink():
        parser.error("Use fresh --out and --receipt paths")

    baseline = archive_members(args.baseline)
    verify_semantic_topology(baseline)
    treatment = treatment_members(baseline)
    packed = archive_bytes(treatment)
    receipt = receipt_for(baseline, treatment, packed)

    publish_pair(args.out, args.receipt, packed, receipt)

    print(json.dumps({
        "baseline_archive_sha256": BASELINE_ARCHIVE_SHA256,
        "treatment_archive_sha256": receipt["treatment"]["archive_sha256"],
        "treatment_config_sha256": TREATMENT_CONFIG_SHA256,
        "members": len(treatment),
        "changed_members": [CONFIG_PATH],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
