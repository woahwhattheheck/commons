#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose FASTING after the canonical W2 native selected-action hook.

This is a second-stage materializer inside the existing dead-feed-care family,
not a second FEED policy/controller. It consumes an already-W2-composed scratch
package, authenticates that W2 postimage plus both helper identities, inserts a
default-OFF FASTING hook after W2 and before selected-action snapshot consumers,
and writes only a new scratch package.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

FEATURE_BEFORE = "    r04_dead_feed_care: bool = False\n"
FEATURE_AFTER = FEATURE_BEFORE + "    r04_uncared_eod_feed_skip: bool = False\n"
HOOK_BEFORE = """                    selected = care.apply_dead_feed_care(
                        selected, obs, cfg, enabled=True)
                # W2-END: existing detached selected checkpoint and consumers.
"""
HOOK_AFTER = """                    selected = care.apply_dead_feed_care(
                        selected, obs, cfg, enabled=True)
                # FASTING-BEGIN: W2 retains precedence; FASTING sees W2's final action.
                if self.features.r04_uncared_eod_feed_skip:
                    # Cancellation/failure falls back to the completed W2 output.
                    fasting_parent = (deepcopy(selected), self.controller.cur)
                    fallback = fasting_parent[0]
                    selected_checkpoint = fasting_parent
                    self.selected = fasting_parent[0]
                    stage = 'uncared_eod_feed_skip'
                    fasting = load('_titan_uncared_eod_feed_skip',
                                   HERE/'r04_uncared_eod_feed_skip.py', cache=True)
                    selected = fasting.apply_uncared_eod_feed_skip(
                        selected, obs, cfg, enabled=True)
                # FASTING-END: existing selected checkpoint consumers remain authoritative.
                # W2-END: existing detached selected checkpoint and consumers.
"""
FASTING_MARKER = "# FASTING-BEGIN: W2 retains precedence; FASTING sees W2's final action."
W2_MARKER = "# W2-BEGIN: optional CARE completes before unit-snapshot capture."
FASTING_RUNTIME_HELPER = "r04_uncared_eod_feed_skip.py"
W2_RUNTIME_HELPER = "r04_dead_feed_care.py"
FASTING_FEATURE = "r04_uncared_eod_feed_skip"


class CompositionError(ValueError):
    pass


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    found = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name]
    if len(found) != 1:
        raise CompositionError(f"expected exactly one {name} class")
    return found[0]


def _segment(text: str, node: ast.AST) -> str:
    return "".join(text.splitlines(keepends=True)[node.lineno - 1 : node.end_lineno])


def _functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compose_runtime(text: str) -> str:
    """Insert FASTING only into the exact canonical W2 postimage seam."""
    tree = ast.parse(text)
    features = _class(tree, "Features")
    agent = _class(tree, "TitanAgent")
    acts = [node for node in agent.body if isinstance(node, ast.FunctionDef) and node.name == "act"]
    if len(acts) != 1:
        raise CompositionError("expected exactly one TitanAgent.act")
    ftext = _segment(text, features)
    atext = _segment(text, acts[0])

    # This materializer is deliberately downstream of W2. Never synthesize or
    # repair W2 here; the existing compose_native.py remains its authority.
    if W2_MARKER not in atext or FEATURE_BEFORE not in ftext:
        raise CompositionError("canonical W2 integration is required before FASTING")

    already = FASTING_MARKER in text or f"{FASTING_FEATURE}: bool" in text
    if already:
        if (
            text.count(FASTING_MARKER) != 1
            or text.count(FEATURE_AFTER) != 1
            or text.count(HOOK_AFTER) != 1
            or HOOK_AFTER not in atext
            or FEATURE_AFTER not in ftext
        ):
            raise CompositionError("partial or drifted FASTING integration")
        restored = text.replace(HOOK_AFTER, HOOK_BEFORE, 1).replace(FEATURE_AFTER, FEATURE_BEFORE, 1)
        if compose_runtime(restored) != text:
            raise CompositionError("noncanonical FASTING integration")
        return text

    if (
        text.count(HOOK_BEFORE) != 1
        or HOOK_BEFORE not in atext
        or text.count(FEATURE_BEFORE) != 1
        or FEATURE_BEFORE not in ftext
    ):
        raise CompositionError("W2/selected checkpoint seam drifted")

    result = text.replace(HOOK_BEFORE, HOOK_AFTER, 1).replace(FEATURE_BEFORE, FEATURE_AFTER, 1)
    ast.parse(result)
    return result


def _new_output_path(output: Path, package: Path) -> Path:
    output_abs = output.absolute()
    package_real = package.resolve()
    if output_abs.exists():
        raise CompositionError("output must not already exist")
    # Resolve the nearest existing ancestor, then append the unresolved suffix.
    # This catches aliases such as /tmp/link-to-package/new/nested-output before
    # copytree creates any directory through that symlink.
    parent = output_abs.parent
    suffix = [output_abs.name]
    while not parent.exists():
        suffix.append(parent.name)
        parent = parent.parent
    candidate = parent.resolve()
    for part in reversed(suffix):
        candidate = candidate / part
    try:
        candidate.relative_to(package_real)
    except ValueError:
        pass
    else:
        raise CompositionError("output must be outside input package")
    if candidate == package_real:
        raise CompositionError("output aliases input package")
    return output_abs


def materialize(
    package: Path,
    fasting_helper: Path,
    output: Path,
    runtime_sha256: str,
    w2_helper_sha256: str,
    fasting_helper_sha256: str,
    *,
    enable: bool = False,
) -> dict[str, Any]:
    """Create a new FASTING-composed scratch package; never mutate the input."""
    package = package.resolve()
    fasting_helper = fasting_helper.resolve()
    if not package.is_dir() or not fasting_helper.is_file():
        raise CompositionError("package/helper input missing")
    output = _new_output_path(output, package)

    runtime = package / "titan_runtime.py"
    w2_helper = package / W2_RUNTIME_HELPER
    config_path = package / "TITAN-CONFIG.json"
    if not runtime.is_file() or not w2_helper.is_file() or not config_path.is_file():
        raise CompositionError("W2 package is incomplete")
    if digest(runtime) != runtime_sha256:
        raise CompositionError("runtime source authentication failed")
    if digest(w2_helper) != w2_helper_sha256:
        raise CompositionError("W2 helper authentication failed")
    if digest(fasting_helper) != fasting_helper_sha256:
        raise CompositionError("FASTING helper authentication failed")
    if "apply_dead_feed_care" not in _functions(w2_helper):
        raise CompositionError("W2 runtime helper API missing")
    if "apply_uncared_eod_feed_skip" not in _functions(fasting_helper):
        raise CompositionError("FASTING public API missing")
    if (package / FASTING_RUNTIME_HELPER).exists():
        raise CompositionError("input already contains FASTING helper; explicit reconciliation required")

    before = runtime.read_text(encoding="utf-8")
    after = compose_runtime(before)
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    if not isinstance(config, dict):
        raise CompositionError("TITAN-CONFIG root must be an object")
    if FASTING_FEATURE in config:
        raise CompositionError("input has existing FASTING config; explicit reconciliation required")

    # Every parse/hash/API/config/output check above completes before first write.
    shutil.copytree(package, output, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (output / "titan_runtime.py").write_text(after, encoding="utf-8")
    shutil.copyfile(fasting_helper, output / FASTING_RUNTIME_HELPER)
    if enable:
        config[FASTING_FEATURE] = True
        (output / "TITAN-CONFIG.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    result = {
        "schema": "titan-v4-starve-native-composition/v1",
        "runtime_input_sha256": runtime_sha256,
        "runtime_output_sha256": digest(output / "titan_runtime.py"),
        "w2_helper_sha256": w2_helper_sha256,
        "fasting_helper_sha256": fasting_helper_sha256,
        "enabled_in_scratch_only": enable,
        "input_config_unchanged_when_disabled": (output / "TITAN-CONFIG.json").read_bytes() == config_bytes if not enable else None,
        "composition_order": ["production", "W2", "FASTING", "selected_checkpoint_consumers"],
        "policy_authority": "none_consume_existing_w2_and_fasting_only",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--fasting-helper", type=Path, required=True)
    parser.add_argument("--runtime-sha256", required=True)
    parser.add_argument("--w2-helper-sha256", required=True)
    parser.add_argument("--fasting-helper-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enable", action="store_true", help="enable FASTING only in the new scratch copy")
    args = parser.parse_args()
    result = materialize(
        args.package,
        args.fasting_helper,
        args.output,
        args.runtime_sha256,
        args.w2_helper_sha256,
        args.fasting_helper_sha256,
        enable=args.enable,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
