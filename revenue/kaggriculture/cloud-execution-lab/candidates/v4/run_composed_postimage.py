#!/usr/bin/env python3
"""Authenticated front-end for the sole TITAN V4 graph postimage runner.

This is not a second assembler.  It verifies the exact canonical manifest,
checker, existing runner generation, and every runner adapter/support source
before importing and invoking ``build_composed_postimage.py``.  There is no
alternate-manifest option.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import postimage_trust as trust


def _load_runner(path: Path):
    spec = importlib.util.spec_from_file_location("_titan_v4_pinned_postimage_runner", path)
    if spec is None or spec.loader is None:
        raise trust.TrustError("cannot load authenticated graph postimage runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).parent)
    parser.add_argument("--check", action="store_true", help="validate canonical graph + pinned adapters only")
    parser.add_argument("--package", type=Path, help="authenticated extracted native package")
    parser.add_argument("--output", type=Path, help="new disposable composed output directory")
    args = parser.parse_args()

    try:
        workspace = args.workspace.resolve(strict=True)
        manifest, _manifest_bytes, paths = trust.verify_control_sources(workspace)
        runner = _load_runner(paths[trust.RUNNER_NAME])
        adapters = getattr(runner, "ADAPTERS", None)
        if not isinstance(adapters, dict):
            raise trust.TrustError("authenticated runner exposes malformed ADAPTERS")
        trust.verify_adapter_paths(workspace, manifest, adapters)
        canonical_manifest = paths[trust.MANIFEST_NAME]

        if args.check:
            if args.package is not None or args.output is not None:
                raise trust.TrustError("--check cannot be combined with --package/--output")
            result = runner.check_only(
                workspace,
                manifest_path=canonical_manifest,
                adapters=adapters,
            )
        else:
            if args.package is None or args.output is None:
                raise trust.TrustError("--package and --output are required unless --check is used")
            result = runner.materialize(
                workspace,
                args.package,
                args.output,
                manifest_path=canonical_manifest,
                adapters=adapters,
            )
    except (trust.TrustError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
