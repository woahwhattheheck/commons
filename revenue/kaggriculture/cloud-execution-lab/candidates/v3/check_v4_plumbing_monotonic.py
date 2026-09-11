#!/usr/bin/env python3
"""Promotion-aware CI entry point for the V4 plumbing guard.

``check_v4_plumbing`` owns the structural/reachability proof. This wrapper adds
state monotonicity across the exact PR base without weakening those checks:

* genuinely new keys must source-land OFF;
* an existing OFF key may remain OFF or be intentionally promoted ON;
* an existing ON key may never silently regress OFF during recomposition;
* Features and router source defaults remain OFF for every key.

Promotion therefore lives only in materialized ``TITAN-CONFIG.json``, as required
by docs/V4.md, while the runtime plumbing remains neutral and reusable.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import check_v4_plumbing as core


def _load_apply(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("_v4_target_apply", path)
    core._require(spec is not None and spec.loader is not None, f"cannot load target apply layer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package_with_apply(module: ModuleType) -> dict[str, bytes]:
    original = core.build_v3.apply_v4
    try:
        core.build_v3.apply_v4 = module
        return core.build_v3.package_files()
    finally:
        core.build_v3.apply_v4 = original


def _config_transition_ok(*, is_new: bool, base_value: object, head_value: object) -> bool:
    if type(head_value) is not bool:
        return False
    if is_new:
        return head_value is False
    if type(base_value) is not bool:
        return False
    return not (base_value is True and head_value is False)


def _self_test_config_transitions() -> None:
    cases = (
        (True, None, False, True, "new OFF"),
        (True, None, True, False, "new ON poison"),
        (False, False, False, True, "existing OFF stays OFF"),
        (False, False, True, True, "promotion OFF to ON"),
        (False, True, True, True, "promoted ON stays ON"),
        (False, True, False, False, "promoted ON regression"),
        (False, None, False, False, "missing base state"),
    )
    for is_new, base_value, head_value, expected, label in cases:
        actual = _config_transition_ok(
            is_new=is_new,
            base_value=base_value,
            head_value=head_value,
        )
        core._require(actual is expected, f"internal config-transition regression: {label}")


def check(base_apply_v4: Path) -> None:
    core._self_test_agent_reachability()
    core._self_test_router_reachability()
    _self_test_config_transitions()

    base_keys = core._literal_keys(base_apply_v4)
    head_keys = core._literal_keys(core.APPLY_V4)
    base_key_set = set(base_keys)
    head_key_set = set(head_keys)
    removed = sorted(base_key_set - head_key_set)
    core._require(
        not removed,
        "V4 recomposition removed already-landed key(s): " + ", ".join(removed),
    )
    new_keys = head_key_set - base_key_set

    base_apply = _load_apply(base_apply_v4)
    base_files = _package_with_apply(base_apply)
    files = core.build_v3.package_files()

    for label, package in (("base", base_files), ("head", files)):
        for required in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
            core._require(required in package, f"materialized {label} package missing {required}")

    base_config = json.loads(base_files["TITAN-CONFIG.json"].decode("utf-8"))
    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    runtime_tree = core.ast.parse(
        files["titan_runtime.py"].decode("utf-8"), filename="titan_runtime.py"
    )
    router_tree = core.ast.parse(
        files["r04_full_router.py"].decode("utf-8"), filename="r04_full_router.py"
    )
    feature_defaults = core._feature_defaults(runtime_tree)
    agent = core._titan_agent_class(runtime_tree)
    reachable_agent = core._reachable_agent_methods(agent)

    for key in head_keys:
        core._require(key in config, f"{key}: missing from materialized TITAN-CONFIG.json")
        core._require(type(config[key]) is bool, f"{key}: materialized config value must be boolean")

        if key in new_keys:
            core._require(config[key] is False, f"{key}: new V4 key must source-land OFF")
        else:
            core._require(key in base_config, f"{key}: missing from materialized base TITAN-CONFIG.json")
            core._require(type(base_config[key]) is bool, f"{key}: base config value must be boolean")
            core._require(
                _config_transition_ok(
                    is_new=False,
                    base_value=base_config[key],
                    head_value=config[key],
                ),
                f"{key}: already-promoted base config True may not regress to False",
            )

        core._require(key in feature_defaults, f"{key}: missing from materialized Features")
        core._require(type(feature_defaults[key]) is bool, f"{key}: Features default must be boolean")
        core._require(feature_defaults[key] is False, f"{key}: Features source default must remain False")
        core._require(
            core._reachable_agent_feature_ref(reachable_agent, key),
            f"{key}: TitanAgent.act chain never references self.features.{key}",
        )
        if key.startswith("r04_"):
            core._assert_r04_router_contract(
                router_tree,
                reachable_agent,
                key,
                require_default_off=True,
            )

    promoted = [key for key in head_keys if config.get(key) is True]
    print(
        "V4 PLUMBING OK",
        "base", list(base_keys),
        "head", list(head_keys),
        "new", sorted(new_keys),
        "promoted", promoted,
        "reachable_agent_methods",
        sorted(getattr(node, "name", "<anonymous>") for node in reachable_agent),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-apply-v4", type=Path, required=True)
    args = parser.parse_args()
    check(args.base_apply_v4)


if __name__ == "__main__":
    main()
