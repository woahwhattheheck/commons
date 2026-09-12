# SPDX-License-Identifier: Apache-2.0
"""Materialize the default-off mirror SELL queue arm from exact production-v3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_delivery import archive_bytes, digest, members

PRODUCTION_V3_SHA = "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239"
FROZEN_SELECTED_SHA256 = "5ca1bc39efed756de71207f46926744ea69f9d2f300dd7b9c1a8cc4dbefeb9ef"
MIRROR_DONOR_GIT_BLOB = "90052d735316461c7b3320a7e968dcddbb2c364e"
MIRROR_DONOR_REL = Path("v4/repairs/gameplay/row-shed-sell-order/mirror_collision_value.py")
FEATURE = "r04_mirror_sell_queue"


def git_blob_sha(body: bytes) -> str:
    header = b"blob " + str(len(body)).encode("ascii") + b"\0"
    return hashlib.sha1(header + body).hexdigest()


def patch_frozen_selected(body: bytes) -> bytes:
    newline = b"\r\n" if b"\r\n" in body else b"\n"
    anchor = newline.join((
        b"        self.previous=seller_public_observation(obs)",
        b"        return out",
    ))
    if body.count(anchor) != 1:
        raise ValueError("expected one FrozenSelected final-return seam")
    replacement = newline.join((
        b"        self.previous=seller_public_observation(obs)",
        b"        if config.get('r04_mirror_sell_queue') is True:",
        b"            from mirror_sell_queue import MirrorSellQueue",
        b"            out=MirrorSellQueue().transform(",
        b"                obs,config,out,post_unit_shed=shed,fallback_action=out)",
        b"        return out",
    ))
    return body.replace(anchor, replacement, 1)


def compose(production: dict[str, bytes], transformer: bytes, donor: bytes) -> dict[str, bytes]:
    files = dict(production)
    frozen = files.get("frozen_selected.py")
    if frozen is None or digest(frozen) != FROZEN_SELECTED_SHA256:
        raise ValueError("production-v3 FrozenSelected authority drift")
    if git_blob_sha(donor) != MIRROR_DONOR_GIT_BLOB:
        raise ValueError("mirror assignment donor Git blob drift")
    for name in ("mirror_sell_queue.py", "mirror_collision_value.py"):
        if name in files:
            raise ValueError("production-v3 already contains mirror SELL experiment member")
    files["mirror_sell_queue.py"] = transformer
    files["mirror_collision_value.py"] = donor
    files["frozen_selected.py"] = patch_frozen_selected(frozen)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-v3", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tar", type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.out.parent / (args.out.name + "-manifest.json")
    if any(path.exists() for path in (args.out, args.tar, receipt_path)):
        parser.error("use new output directory, archive and manifest paths")

    production = members(args.production_v3, PRODUCTION_V3_SHA)
    here = Path(__file__).resolve().parent
    transformer = (here / "mirror_sell_queue.py").read_bytes()
    donor_path = here.parents[1] / MIRROR_DONOR_REL
    donor = donor_path.read_bytes()
    files = compose(production, transformer, donor)
    packed = archive_bytes(files)

    args.out.mkdir(parents=True)
    for name, body in files.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    args.tar.parent.mkdir(parents=True, exist_ok=True)
    with args.tar.open("xb") as stream:
        stream.write(packed)

    receipt = {
        "schema": "titan-v5-mirror-sell-queue-build/v1",
        "parent_archive_sha256": PRODUCTION_V3_SHA,
        "candidate_archive_sha256": digest(packed),
        "feature": FEATURE,
        "feature_default": False,
        "source_authority": {
            "frozen_selected_sha256": FROZEN_SELECTED_SHA256,
            "mirror_assignment_git_blob": MIRROR_DONOR_GIT_BLOB,
        },
        "files": {name: digest(body) for name, body in sorted(files.items())},
        "kaggle_submission_hold": True,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "out": str(args.out),
        "members": len(files),
        "candidate_archive_sha256": digest(packed),
        "feature_default": False,
    }))


if __name__ == "__main__":
    main()
