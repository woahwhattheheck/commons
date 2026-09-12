#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-pinned current-FrozenSelected H3/S420 candidate composer.

H3 maps the historical sale-window horizon 8 -> 3 onto the current scheduler's
baseline horizon. S420 maps the historical "stop new late reservation" rule onto
current FrozenSelected by suppressing only *new plan selection* at/after step 420.
Inherited/base SELL rows and quantities from already-planned due commitments are
still materialized by the untouched tail of FrozenSelected.transform().

Candidate/research composer only. It never edits production files in place.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

FROZEN_SELECTED_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
BASELINE_HORIZON = 3
SUPPRESS_NEW_PLANS_AFTER = 420

_IMPORT_MARKER = (
    "from selected_sell_core import optimize_lot, joint_plan_metrics, shared_slot_ledger\n"
)
_BLOCK_START = "        budget=self.cash_reserve(obs,config,base,end)\n"
_BLOCK_END = "        out=copy.deepcopy(base)\n"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _rewrite_source(source: str) -> str:
    if source.count(_IMPORT_MARKER) != 1:
        raise ValueError("selected-sell import marker drift")
    if source.count(_BLOCK_START) != 1 or source.count(_BLOCK_END) != 1:
        raise ValueError("FrozenSelected transform marker drift")

    constants = (
        _IMPORT_MARKER
        + "\n"
        + "# H3/S420 current-ABI experiment: source-pinned and default-off at composition.\n"
        + f"H3S420_BASELINE_HORIZON = {BASELINE_HORIZON}\n"
        + f"H3S420_SUPPRESS_NEW_PLANS_AFTER = {SUPPRESS_NEW_PLANS_AFTER}\n"
        + "# scheduler.HORIZON was imported above via `from scheduler import *`; shadow it\n"
        + "# only in this generated FrozenSelected module.\n"
        + "HORIZON = H3S420_BASELINE_HORIZON\n"
    )
    out = source.replace(_IMPORT_MARKER, constants, 1)

    start = out.index(_BLOCK_START)
    end = out.index(_BLOCK_END, start)
    block = out[start:end]
    indented = "".join(("    " + line) if line.strip() else line for line in block.splitlines(True))
    guard = (
        "        self.diagnostics['h3s420']={\n"
        "            'baseline_horizon':H3S420_BASELINE_HORIZON,\n"
        "            'suppress_new_plans_after':H3S420_SUPPRESS_NEW_PLANS_AFTER,\n"
        "            'new_plan_suppressed':now>=H3S420_SUPPRESS_NEW_PLANS_AFTER}\n"
        "        if now < H3S420_SUPPRESS_NEW_PLANS_AFTER:\n"
        + indented
    )
    out = out[:start] + guard + out[end:]
    compile(out, "<h3s420-frozen-selected>", "exec")
    return out


def compose(source: bytes, *, enabled: bool) -> bytes:
    if not enabled:
        return source
    if git_blob(source) != FROZEN_SELECTED_GIT_BLOB:
        raise ValueError("frozen_selected.py source drift")
    return _rewrite_source(source.decode("utf-8")).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scheduler", type=Path, required=True,
                        help="current scheduler.py; authenticated but not modified")
    parser.add_argument("--enable-current-h3s420", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    source = args.source.read_bytes()
    scheduler = args.scheduler.read_bytes()
    if git_blob(source) != FROZEN_SELECTED_GIT_BLOB:
        raise ValueError("frozen_selected.py source drift")
    if git_blob(scheduler) != SCHEDULER_GIT_BLOB:
        raise ValueError("scheduler.py source drift")
    result = compose(source, enabled=args.enable_current_h3s420)
    args.output.write_bytes(result)

    if args.receipt is not None:
        import json
        payload = {
            "schema": "titan.v4.h3s420-current-source/v1",
            "enabled": bool(args.enable_current_h3s420),
            "source_git_blob": git_blob(source),
            "scheduler_git_blob": git_blob(scheduler),
            "output_git_blob": git_blob(result),
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "output_sha256": hashlib.sha256(result).hexdigest(),
            "baseline_horizon": BASELINE_HORIZON if args.enable_current_h3s420 else 8,
            "suppress_new_plans_after": SUPPRESS_NEW_PLANS_AFTER if args.enable_current_h3s420 else None,
            "production_activation": False,
            "semantics": (
                "new plan selection suppressed at/after threshold; inherited/base SELLs and "
                "already-planned due quantities remain materialized"
            ),
        }
        args.receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
