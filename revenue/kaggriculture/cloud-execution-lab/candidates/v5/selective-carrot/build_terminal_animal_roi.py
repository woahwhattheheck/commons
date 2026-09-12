# SPDX-License-Identifier: Apache-2.0
"""Materialize one bounded terminal-animal arm over exact V5 production-v3."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


PRODUCTION_V3_SHA = "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239"
PRODUCTION_MAIN_SHA = "381b50f858212727a9d95d11ae8ff5ba4ab830b35e1d5cd6d1e6a1d375d2e83"
HELPER_SHA = "88ecc56d438998e20abfac15b2833dbdfc58e0a350b8231ff7adeac736ce4b00"
HORIZONS = (718, 696, 672, 648)
RETURN_ANCHOR = b"    return returned\n"


def _horizon(value: int) -> int:
    if type(value) is not int or value not in HORIZONS:
        raise ValueError("min_step must be one of " + ", ".join(map(str, HORIZONS)))
    return value


def patch_entry(entry: bytes, helper: bytes, min_step: int) -> bytes:
    """Patch exactly one authenticated production-v3 return seam."""
    min_step = _horizon(min_step)
    if digest(entry) != PRODUCTION_MAIN_SHA:
        raise ValueError("production-v3 main.py identity drift")
    if digest(helper) != HELPER_SHA:
        raise ValueError("terminal-animal helper identity drift")
    if entry.count(RETURN_ANCHOR) != 1:
        raise ValueError("expected one production-v3 returned-action seam")
    replacement = (
        b"    from terminal_animal_roi import filter_action\n"
        + f"    returned = filter_action(observation, returned, min_step={min_step})\n".encode("ascii")
        + RETURN_ANCHOR
    )
    return entry.replace(RETURN_ANCHOR, replacement, 1)


def compose(parent: dict[str, bytes], helper: bytes, min_step: int, *, enabled: bool) -> dict[str, bytes]:
    """Return exact parent when disabled, else one helper + one entry edit."""
    min_step = _horizon(min_step)
    if "main.py" not in parent:
        raise ValueError("production-v3 archive lacks main.py")
    if "terminal_animal_roi.py" in parent:
        raise ValueError("production-v3 archive already contains terminal_animal_roi.py")
    if digest(parent["main.py"]) != PRODUCTION_MAIN_SHA:
        raise ValueError("production-v3 main.py identity drift")
    if not enabled:
        return dict(parent)
    files = dict(parent)
    files["main.py"] = patch_entry(parent["main.py"], helper, min_step)
    files["terminal_animal_roi.py"] = helper
    return files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-v3", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tar", type=Path, required=True)
    parser.add_argument("--min-step", type=int, choices=HORIZONS, default=718)
    parser.add_argument("--enable", action="store_true",
                        help="materialize treatment; omitted means byte-identical control")
    args = parser.parse_args(argv)

    receipt_path = args.out.parent / (args.out.name + "-manifest.json")
    if any(path.exists() for path in (args.out, args.tar, receipt_path)):
        parser.error("Use new output directory, archive and manifest paths")

    from build_delivery import archive_bytes, members

    parent = members(args.production_v3, PRODUCTION_V3_SHA)
    helper = Path(__file__).with_name("terminal_animal_roi.py").read_bytes().replace(b"\r\n", b"\n")
    if digest(helper) != HELPER_SHA:
        raise ValueError("terminal-animal helper identity drift")
    files = compose(parent, helper, args.min_step, enabled=args.enable)
    packed = archive_bytes(files)
    if not args.enable and digest(packed) != PRODUCTION_V3_SHA:
        raise ValueError("guard-off materialization is not byte-identical production-v3")

    args.out.mkdir(parents=True)
    for name, body in files.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    args.tar.parent.mkdir(parents=True, exist_ok=True)
    with args.tar.open("xb") as stream:
        stream.write(packed)

    receipt = {
        "schema": "titan-v5-terminal-animal-roi/v1",
        "production_v3_archive_sha256": PRODUCTION_V3_SHA,
        "production_main_sha256": PRODUCTION_MAIN_SHA,
        "helper_sha256": HELPER_SHA,
        "enabled": args.enable,
        "min_step": args.min_step,
        "candidate_archive_sha256": digest(packed),
        "changed_members": [] if not args.enable else ["main.py", "terminal_animal_roi.py"],
        "kaggle_submission_hold": True,
        "files": {name: digest(body) for name, body in sorted(files.items())},
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_archive_sha256": digest(packed),
                      "enabled": args.enable, "min_step": args.min_step,
                      "members": len(files)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
