#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a three-arm postprocessor knockout screen from exact production-v3."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SUPPORT_PATH = HERE.parent / "r04-postprocessor-survivorship" / "materialize_r04_bypass.py"
_spec = importlib.util.spec_from_file_location("_r04_survivorship_support", SUPPORT_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load materializer support: {SUPPORT_PATH}")
support = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = support
_spec.loader.exec_module(support)

BASELINE_ARCHIVE_SHA256 = "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239"
BASELINE_CONFIG_SHA256 = "ba18563683125fd89d5473ddb8a5c3e9431db1787a3046f618a9e03af2cb44af"
CONFIG_PATH = "TITAN-CONFIG.json"
SCHEMA = "titan-v5-production-v3-postprocessor-attribution/v1"

# Production-v3 changes only main.py versus historical production-v2. Keep the
# already-reviewed runtime/controller/R04 topology pins and rotate main.py to
# the import-safe v3 member authenticated by PRODUCTION-V3-PACKAGE-MANIFEST.
SEMANTIC_MEMBER_SHA256 = dict(support.SEMANTIC_MEMBER_SHA256)
SEMANTIC_MEMBER_SHA256["main.py"] = "b98aec64f83ea9a216def7ab1fef320a6498ae37816f506af1f891c934027035"
SEMANTIC_ANCHORS = support.SEMANTIC_ANCHORS

# Exact production-v3 preimage for every screened flag. The whole config SHA
# binds all other fields; these explicit values prevent a silently redefined
# stage from inheriting a changed baseline.
SCREEN_PREIMAGE = {
    "consumer": "frozen",
    "seed": True,
    "funding": True,
    "redundant_hire": True,
    "market_pressure": True,
    "operating_stock": True,
    "idle_fertilizer": True,
    "crop_release": True,
    "early_capital": True,
    "town_procurement": True,
}

# Valid knockouts from the FULL composition. Keeping consumer=frozen is
# deliberate: Features rejects redundant_hire/idle_fertilizer/crop_release on
# parent consumers. Town is not duplicated here because native-9901 already
# measured the full-context town-off singleton.
ARMS = {
    "seed_hire_off": {
        "seed": False,
        "funding": False,
        "redundant_hire": False,
    },
    "inventory_spatial_off": {
        "operating_stock": False,
        "idle_fertilizer": False,
        "crop_release": False,
    },
    "late_market_off": {
        "market_pressure": False,
        "early_capital": False,
    },
}


def digest(raw: bytes) -> str:
    return support.digest(raw)


def _baseline_config(baseline: dict[str, bytes]) -> dict:
    raw = baseline.get(CONFIG_PATH)
    if raw is None:
        raise ValueError("baseline archive is missing TITAN-CONFIG.json")
    if digest(raw) != BASELINE_CONFIG_SHA256:
        raise ValueError("baseline config is not exact production-v3")
    config = json.loads(raw)
    if not isinstance(config, dict):
        raise ValueError("TITAN-CONFIG.json must contain a JSON object")
    for key, expected in SCREEN_PREIMAGE.items():
        value = config.get(key)
        if type(value) is not type(expected) or value != expected:
            raise ValueError(f"baseline {key} does not match authenticated preimage")
    return config


def arm_members(baseline: dict[str, bytes], arm: str) -> dict[str, bytes]:
    if arm not in ARMS:
        raise ValueError(f"unknown attribution arm: {arm}")
    config = _baseline_config(baseline)
    for key, value in ARMS[arm].items():
        config[key] = value

    # Dependency fence copied from live Features semantics. The screen never
    # emits a parent+spatial/redundant arm just to make a factorial square.
    if config["consumer"] != "frozen" and (
        config["redundant_hire"] or config["idle_fertilizer"] or config["crop_release"]
    ):
        raise AssertionError("invalid non-frozen spatial/redundant treatment")
    if config["town_procurement"] is not True:
        raise AssertionError("town singleton must remain full-context and reuse-only")

    changed_config = json.dumps(config, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    treatment = dict(baseline)
    treatment[CONFIG_PATH] = changed_config
    if set(treatment) != set(baseline):
        raise AssertionError("treatment changed archive membership")
    changed_members = sorted(name for name in baseline if baseline[name] != treatment[name])
    if changed_members != [CONFIG_PATH]:
        raise AssertionError(f"treatment changed unexpected members: {changed_members}")
    return treatment


def build_screen(baseline: dict[str, bytes]) -> tuple[bytes, dict]:
    _baseline_config(baseline)
    baseline_members = {name: digest(body) for name, body in sorted(baseline.items())}
    arm_records = {}
    bundle_members: dict[str, bytes] = {}
    for arm in sorted(ARMS):
        treatment = arm_members(baseline, arm)
        packed = support.archive_bytes(treatment)
        cfg_raw = treatment[CONFIG_PATH]
        treatment_members = {name: digest(body) for name, body in sorted(treatment.items())}
        record = {
            "archive_sha256": digest(packed),
            "config_sha256": digest(cfg_raw),
            "config_changes": {
                key: {"before": SCREEN_PREIMAGE[key], "after": after}
                for key, after in sorted(ARMS[arm].items())
            },
            "member_count": len(treatment),
            "changed_members": [CONFIG_PATH],
            "members": treatment_members,
        }
        for name, member_sha in baseline_members.items():
            if name != CONFIG_PATH and treatment_members[name] != member_sha:
                raise AssertionError(f"treatment changed retained member identity: {arm}: {name}")
        arm_records[arm] = record
        bundle_members[f"arms/{arm}.tar.gz"] = packed

    screen = {
        "schema": SCHEMA,
        "baseline_archive_sha256": BASELINE_ARCHIVE_SHA256,
        "baseline_config_sha256": BASELINE_CONFIG_SHA256,
        "baseline_members": baseline_members,
        "semantic_topology": {
            "status": "AUTHENTICATED",
            "members": dict(sorted(SEMANTIC_MEMBER_SHA256.items())),
        },
        "arms": arm_records,
        "reused_native_9901": {
            "full_production_v3": "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239",
            "aggregate_post_bypass": "EXACT_V31_TERMINAL_SCORES_ON_SEED_1209129901",
            "town_off": "FULL_MINUS_TOWN_LOSES_2_APEX_1_ARLENE_OWN_AND_MARGIN",
            "champion_blocker": "APEX_OWN_MINUS_V31=-237",
        },
        "native_economics_status": "PENDING_MATCHED_NATIVE_9901",
        "decision_rule": (
            "Run only these three knockouts against reused seed1209129901 controls. "
            "Prefer a knockout that restores Apex own score without erasing the V3.1 margin gain; "
            "if none does, stop and attribute the residual to FrozenSelected/cross-group interaction."
        ),
        "kaggle_submission_hold": True,
    }
    screen_raw = (json.dumps(screen, indent=2, sort_keys=True) + "\n").encode("utf-8")
    bundle_members["SCREEN.json"] = screen_raw
    bundle = support.archive_bytes(bundle_members)
    receipt = {
        **screen,
        "bundle_sha256": digest(bundle),
        "bundle_members": {name: digest(body) for name, body in sorted(bundle_members.items())},
    }
    return bundle, receipt


def materialize(baseline_path: Path) -> tuple[bytes, dict]:
    baseline_path = Path(baseline_path)
    if not baseline_path.is_file() or baseline_path.is_symlink():
        raise ValueError(f"baseline must be an ordinary file: {baseline_path}")
    raw = baseline_path.read_bytes()
    baseline = support.parse_archive_bytes(raw, BASELINE_ARCHIVE_SHA256)
    support.verify_semantic_topology(baseline, SEMANTIC_MEMBER_SHA256, SEMANTIC_ANCHORS)
    return build_screen(baseline)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.bundle == args.receipt:
        parser.error("--bundle and --receipt must differ")
    if args.bundle.exists() or args.bundle.is_symlink() or args.receipt.exists() or args.receipt.is_symlink():
        parser.error("use fresh --bundle and --receipt paths")

    bundle, receipt = materialize(args.baseline)
    support.publish_pair(args.bundle, args.receipt, bundle, receipt)
    print(json.dumps({
        "baseline_archive_sha256": BASELINE_ARCHIVE_SHA256,
        "bundle_sha256": receipt["bundle_sha256"],
        "arms": {name: receipt["arms"][name]["archive_sha256"] for name in sorted(ARMS)},
    }, sort_keys=True))


if __name__ == "__main__":
    main()
