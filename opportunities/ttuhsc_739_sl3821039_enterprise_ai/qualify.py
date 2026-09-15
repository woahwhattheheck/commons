"""Current TTUHSC pursuit gate backed by repo-pinned evidence, never caller time."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from revenue.pursuit_evidence_bridge.bridge import BridgeError, compile_bridge, load_json

BINDING_ID = "ttuhsc-739-sl3821039-main-v1"
HERE = Path(__file__).resolve().parent


def _load_local(name: str) -> dict[str, Any]:
    return load_json((HERE / name).read_bytes(), name)


def evaluate_current(vault: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate only the checked-in TTUHSC source generation at process-owned UTC."""
    return compile_bridge(
        BINDING_ID,
        _load_local("source_ledger.json"),
        _load_local("submission_manifest.json"),
        vault,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Current TTUHSC 739-SL3821039 pursuit gate")
    parser.add_argument(
        "--vault",
        type=Path,
        help="Optional bidder-vault envelope; rejected unless exact roots are already pinned in the repo binding",
    )
    args = parser.parse_args(argv)
    try:
        vault = None if args.vault is None else load_json(args.vault.read_bytes(), "vault")
        result = evaluate_current(vault)
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        return 0 if result["status"] == "OPPORTUNITY_EVIDENCE_READY" else 2
    except (BridgeError, OSError) as exc:
        sys.stderr.write(f"HOLD: {exc}\n")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
