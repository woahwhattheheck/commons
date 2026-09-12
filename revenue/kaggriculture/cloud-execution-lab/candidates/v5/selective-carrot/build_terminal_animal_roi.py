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
HELPER_SHA = "11ab299c83a09b53ad9a2d6c5177daf55fbc3c759eaa2a0791774391271dd2dd"
HORIZONS = (718, 696, 672, 648)
AGENT_ANCHOR = b"\ndef agent("
RETURN_ANCHOR = b"    return returned\n"
INLINE_BEGIN = b"# TITAN_TERMINAL_ANIMAL_ROI_INLINE_BEGIN\n"
INLINE_END = b"# TITAN_TERMINAL_ANIMAL_ROI_INLINE_END\n"


def _horizon(value: int) -> int:
    if type(value) is not int or value not in HORIZONS:
        raise ValueError("min_step must be one of " + ", ".join(map(str, HORIZONS)))
    return value


def inline_source(helper: bytes) -> bytes:
    """Extract the one authenticated runtime region from the repo-only helper."""
    if digest(helper) != HELPER_SHA:
        raise ValueError("terminal-animal helper identity drift")
    if helper.count(INLINE_BEGIN) != 1 or helper.count(INLINE_END) != 1:
        raise ValueError("terminal-animal inline markers drift")
    before, rest = helper.split(INLINE_BEGIN, 1)
    body, after = rest.split(INLINE_END, 1)
    if INLINE_BEGIN in body or INLINE_END in body or not body.strip():
        raise ValueError("invalid terminal-animal inline region")
    return body.rstrip() + b"\n"


def patch_entry(entry: bytes, helper: bytes, min_step: int) -> bytes:
    """Patch exactly one authenticated production-v3 return seam, add no member."""
    min_step = _horizon(min_step)
    if digest(entry) != PRODUCTION_MAIN_SHA:
        raise ValueError("production-v3 main.py identity drift")
    if entry.count(AGENT_ANCHOR) != 1:
        raise ValueError("expected one production-v3 agent seam")
    if entry.count(RETURN_ANCHOR) != 1:
        raise ValueError("expected one production-v3 returned-action seam")
    if b"terminal_animal_roi_filter" in entry:
        raise ValueError("production-v3 main.py already has terminal-animal treatment")

    runtime = inline_source(helper)
    patched = entry.replace(AGENT_ANCHOR, b"\n" + runtime + AGENT_ANCHOR, 1)
    replacement = (
        f"    returned = terminal_animal_roi_filter(observation, returned, min_step={min_step})\n".encode("ascii")
        + RETURN_ANCHOR
    )
    return patched.replace(RETURN_ANCHOR, replacement, 1)


def compose(parent: dict[str, bytes], helper: bytes, min_step: int, *, enabled: bool) -> dict[str, bytes]:
    """Return exact parent when disabled; enabled replaces only existing main.py."""
    min_step = _horizon(min_step)
    if "main.py" not in parent:
        raise ValueError("production-v3 archive lacks main.py")
    if digest(parent["main.py"]) != PRODUCTION_MAIN_SHA:
        raise ValueError("production-v3 main.py identity drift")
    inline_source(helper)
    if not enabled:
        return dict(parent)
    files = dict(parent)
    files["main.py"] = patch_entry(parent["main.py"], helper, min_step)
    if set(files) != set(parent):
        raise ValueError("replacement-only treatment changed archive membership")
    for name in parent:
        if name != "main.py" and files[name] != parent[name]:
            raise ValueError("replacement-only treatment changed unrelated member: " + name)
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
        "schema": "titan-v5-terminal-animal-roi/v2",
        "production_v3_archive_sha256": PRODUCTION_V3_SHA,
        "production_main_sha256": PRODUCTION_MAIN_SHA,
        "helper_source_sha256": HELPER_SHA,
        "enabled": args.enable,
        "min_step": args.min_step,
        "candidate_archive_sha256": digest(packed),
        "changed_members": [] if not args.enable else ["main.py"],
        "archive_member_set_preserved": True,
        "kaggle_submission_hold": True,
        "files": {name: digest(body) for name, body in sorted(files.items())},
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_archive_sha256": digest(packed),
                      "enabled": args.enable, "min_step": args.min_step,
                      "members": len(files), "changed_members": receipt["changed_members"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
