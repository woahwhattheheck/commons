# SPDX-License-Identifier: Apache-2.0
"""Bind the L01 finding to the authenticated one-tree Slack packet."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any

PACKET_SHA256 = "f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728"
ROOT = "revenue/kaggriculture/cloud-execution-lab/candidates/v3"
MEMBERS = {
    "l01_mechanics.py": f"{ROOT}/overlay/l01_mechanics.py",
    "test_v3_l01.py": f"{ROOT}/overlay/checks/test_v3_l01.py",
    "V3-MANIFEST.json": f"{ROOT}/V3-MANIFEST.json",
}
EXPECTED_SHA256 = {
    "l01_mechanics.py": "65fc1841f6d00b6db78e2eb88d98e9e7b05053502e0de527bce1f1a60fbe9691",
    "test_v3_l01.py": "fb3a4ecebbc37021977423dfc23cc0bb3db75eddc41dae6a9db8eb490462a589",
}
EXPECTED_BASKET = (
    ("CARROT", 14),
    ("MELON", 20),
    ("MILK", 40),
    ("STRAWBERRY", 8),
    ("TOMATO", 12),
    ("WHEAT", 2),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_member(archive: tarfile.TarFile, name: str) -> bytes:
    posix = PurePosixPath(name)
    if posix.is_absolute() or ".." in posix.parts or "\\" in name:
        raise ValueError(f"noncanonical member name: {name!r}")
    member = archive.getmember(name)
    if not member.isfile():
        raise ValueError(f"not a regular file: {name}")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"unreadable member: {name}")
    data = stream.read()
    if len(data) != member.size:
        raise ValueError(f"short member: {name}")
    return data


def assigned_literal(source: str, name: str) -> Any:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"assignment not found: {name}")


def run(packet_path: Path) -> dict[str, Any]:
    packet = packet_path.read_bytes()
    actual_packet = sha256(packet)
    if actual_packet != PACKET_SHA256:
        raise ValueError(f"packet hash mismatch: {actual_packet}")
    with tarfile.open(packet_path, "r:gz") as archive:
        payload = {short: read_member(archive, path) for short, path in MEMBERS.items()}

    for short, expected in EXPECTED_SHA256.items():
        actual = sha256(payload[short])
        if actual != expected:
            raise ValueError(f"source preimage mismatch {short}: {actual}")

    source = payload["l01_mechanics.py"].decode("utf-8")
    basket = assigned_literal(source, "DAY0_BASKET")
    if basket != EXPECTED_BASKET:
        raise ValueError(f"DAY0_BASKET mismatch: {basket!r}")
    manifest = json.loads(payload["V3-MANIFEST.json"])
    declared = manifest["overlay"]["l01_mechanics.py"]
    if declared != EXPECTED_SHA256["l01_mechanics.py"]:
        raise ValueError("manifest does not bind the L01 source preimage")

    result = {
        "schema": "titan.l01-day0-source-packet-witness.v1",
        "packet_sha256": actual_packet,
        "packet_bytes": len(packet),
        "member_sha256": {short: sha256(data) for short, data in sorted(payload.items())},
        "manifest_base": manifest["base"],
        "manifest_archive": manifest["archive"],
        "l01_main_tape": assigned_literal(source, "MAIN"),
        "day0_basket": [list(row) for row in basket],
        "generated_orders": [["BUY_PRODUCT", item, quantity] for item, quantity in basket],
    }
    body = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["receipt_sha256"] = sha256(body.encode("utf-8"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.packet)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
