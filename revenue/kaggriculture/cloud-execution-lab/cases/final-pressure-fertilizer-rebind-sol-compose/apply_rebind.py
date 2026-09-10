# SPDX-License-Identifier: Apache-2.0
"""Exact-source carrier for the final-pressure idle-FERT ledger rebind."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Final

TARGET: Final = Path("revenue/kaggriculture/cloud-execution-lab/main.py")
EXPECTED_MAIN_GIT_BLOB_SHA1: Final = "4a8cf7bcda1f0fea231a144692cb84a779a9e73e"
EXPECTED_PRESSURE_GIT_BLOB_SHA1: Final = "7261674962d10fc8bc6af5ff73ff9212c40f61ad"
OPERATION: Final = "TITAN-V3-FINAL-PRESSURE-FERTILIZER-LEDGER-REBIND-20260910-01"

OLD = '        def _early_capital_selected(self, obs, cfg, selected):\n            # TitanAgent._finish_production calls this after every stock/crop\n            # guard and before every receipt/history commit. Reuse that stable\n            # boundary instead of copying the finalizer or mutating afterward.\n            returned = super()._early_capital_selected(obs, cfg, selected)\n            if self.diagnostics.get(\'status\') != \'completed\':\n                return returned\n            self._final_pressure_boundary = True\n            try:\n                return super()._market_pressure_selected(obs, cfg, returned)\n            finally:\n                self._final_pressure_boundary = False\n'

NEW = '        def _rebind_idle_fertilizer_sale(self, obs, selected):\n            """Bind the existing idle-FERT proposal to the final market bytes.\n\n            SpatialTempo validates the DROP+SELL pair before late capital and\n            pressure transforms. Pressure preserves lots but may move the unique\n            FERTILIZER sale, so update only its custody slot after that reorder.\n            An impossible missing/duplicate lot cancels the paired DROP instead\n            of returning an untracked delivery.\n            """\n            spatial = getattr(self, \'spatial\', None)\n            proposal = (None if spatial is None\n                        else getattr(spatial, \'_sale_proposal\', None))\n            if proposal is None or proposal.get(\'step\') != int(obs[\'step\']):\n                return selected\n            market = selected.get(\'market\', [])\n            slots = [i for i, order in enumerate(market[:10])\n                     if order and len(order) > 2\n                     and order[:2] == [\'SELL\', \'FERTILIZER\']]\n            if (len(slots) == 1\n                    and market[slots[0]] == [\'SELL\', \'FERTILIZER\', 1]):\n                proposal[\'slot\'] = slots[0]\n                return selected\n\n            from copy import deepcopy\n            result = deepcopy(selected)\n            worker = proposal.get(\'worker\')\n            if worker is not None:\n                if worker == 0:\n                    result[\'farmer\'] = [\'PASS\']\n                elif worker > 0:\n                    hands = result.setdefault(\'hands\', [])\n                    while len(hands) < worker:\n                        hands.append([\'PASS\'])\n                    hands[worker - 1] = [\'PASS\']\n            for slot in slots:\n                result[\'market\'][slot] = []\n            return result\n\n        def _early_capital_selected(self, obs, cfg, selected):\n            # TitanAgent._finish_production calls this after every stock/crop\n            # guard and before every receipt/history commit. Reuse that stable\n            # boundary instead of copying the finalizer or mutating afterward.\n            returned = super()._early_capital_selected(obs, cfg, selected)\n            if self.diagnostics.get(\'status\') != \'completed\':\n                return returned\n            self._final_pressure_boundary = True\n            try:\n                returned = super()._market_pressure_selected(obs, cfg, returned)\n            finally:\n                self._final_pressure_boundary = False\n            return self._rebind_idle_fertilizer_sale(obs, returned)\n'

def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def patch_bytes(source: bytes) -> bytes:
    if git_blob_sha1(source) != EXPECTED_MAIN_GIT_BLOB_SHA1:
        raise ValueError("main.py preimage Git blob mismatch")
    text = source.decode("utf-8")
    count = text.count(OLD)
    if count != 1:
        raise ValueError(f"main.py anchor expected once, found {count}")
    candidate = text.replace(OLD, NEW, 1)
    if candidate.count(NEW) != 1 or OLD in candidate:
        raise ValueError("replacement closure failed")
    compile(candidate, str(TARGET), "exec")
    return candidate.encode("utf-8")


def materialize(tree: Path, output: Path) -> dict:
    tree = tree.resolve()
    source_path = tree / TARGET
    source = source_path.read_bytes()
    candidate = patch_bytes(source)
    target = output.resolve()
    if target == source_path:
        raise ValueError("in-place canonical mutation is not supported by this carrier")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(candidate)
    if target.read_bytes() != candidate:
        raise OSError("candidate readback mismatch")
    return {
        "operation": OPERATION,
        "target": TARGET.as_posix(),
        "source_git_blob_sha1": git_blob_sha1(source),
        "candidate_git_blob_sha1": git_blob_sha1(candidate),
        "source_bytes": len(source),
        "candidate_bytes": len(candidate),
        "changed": source != candidate,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = materialize(args.tree, args.output)
    payload = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if args.receipt:
        args.receipt.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
