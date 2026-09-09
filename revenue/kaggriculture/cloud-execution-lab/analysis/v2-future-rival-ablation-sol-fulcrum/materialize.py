# SPDX-License-Identifier: Apache-2.0
"""Materialize a closure-bound frozen-V2 future-rival ablation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from materialize_custody import (
    ABLATION_SCENARIOS,
    ENTRYPOINT_SHA256,
    FREEZE_GIT_BLOB,
    FUTURE_SCENARIO_BLOCK,
    HEX40,
    MaterializeError,
    OPERATION,
    SCHEDULER_GIT_BLOB,
    SCHEDULER_SHA256,
    V2_SCENARIOS,
    closure_digest,
    git_blob_bytes,
    inventory,
    sha256_bytes,
    strict_json,
    verify_frozen_source,
)
from materialize_scenario import patch_scheduler, scenario_names
from materialize_build import materialize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", choices=("control", "ablation"), required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--checkout-head", required=True)
    args = parser.parse_args(argv)
    receipt = materialize(
        args.source, args.output, args.arm, args.receipt, args.checkout_head
    )
    print(
        json.dumps(
            {
                "operation": receipt["operation"],
                "arm": receipt["arm"],
                "source_closure": receipt["source"]["runtime_closure_sha256"],
                "runtime_closure": receipt["materialized"]["runtime_closure_sha256"],
                "entry_sha256": receipt["entry"]["sha256"],
                "changed_paths": receipt["materialized"]["changed_paths"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
