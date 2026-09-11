# SPDX-License-Identifier: Apache-2.0
"""Fail-closed composer for consuming the S33 row-shed donor on a current V3.1 root.

This file is analysis/tooling only.  It does not mutate the package unless ``--write``
is explicitly supplied.  The transform uses exact single-occurrence anchors and appends
the new install parameter after every shipped B5/JIT positional argument, so applying
row-shed cannot silently shift the existing R04 install ABI.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

R04_REL = Path("overlay/r04_full_router.py")
APPLY_REL = Path("apply_v3.py")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_r04(text: str) -> str:
    # Preservation witnesses from the shipped 8e3 root / #12535 parent.  L3 may
    # harden independently, but row-shed must never consume a root that lost B5/JIT.
    for marker in (
        "B5_CARROT_FERTILIZER = False",
        "B5_JIT_FERTILIZE = False",
        "def _b5_fertilize(observation, action):",
        "NO_LATE_SALE_ADVANCE_STEP = 648",
        "SALE_EXCLUDED = ('WHEAT', 'FERTILIZER')",
    ):
        if marker not in text:
            raise RuntimeError(f"r04 preservation marker missing: {marker}")

    text = _replace_once(
        text,
        "ROW_ORDER = False\n",
        "ROW_ORDER = False\n# S33: rank leading SELL rows by currently executable shed stock, default OFF.\nROW_SHED = False\n",
        "r04 ROW_SHED declaration",
    )
    text = _replace_once(
        text,
        "def order_sells(market, inventory):\n    \"\"\"Leading SELL rows sorted by the price drop each causes, steepest first.\"\"\"",
        "def order_sells(market, inventory, projected_stock=None):\n    \"\"\"Leading SELL rows sorted by executable price-drop value, steepest first.\"\"\"",
        "r04 order_sells signature",
    )
    text = _replace_once(
        text,
        "        level = int(inventory.get(item, _RO_I0))\n        quantity = max(0, int(order[2]))\n        return (_ro_price(item, level) - _ro_price(item, level + quantity)) * quantity\n",
        "        level = int(inventory.get(item, _RO_I0))\n        quantity = max(0, int(order[2]))\n        if projected_stock is not None:\n            try:\n                if item in projected_stock:\n                    available = projected_stock.get(item)\n                    if type(available) is int and available >= 0:\n                        quantity = min(quantity, available)\n            except Exception:\n                pass  # Fail closed to the incumbent requested-quantity score.\n        return (_ro_price(item, level) - _ro_price(item, level + quantity)) * quantity\n",
        "r04 executable quantity",
    )
    text = _replace_once(
        text,
        "        ordered = order_sells(market, inventory)\n        if ordered != market:\n",
        "        projected = None\n        if ROW_SHED:\n            try:\n                projected = projected_shed(action, FarmView(observation))\n            except Exception:\n                projected = None\n        ordered = order_sells(market, inventory, projected)\n        if ordered != market:\n",
        "r04 v3_agent row-shed projection",
    )
    text = _replace_once(
        text,
        "            b5_carrot_fertilizer=None, b5_jit_fertilize=None):\n",
        "            b5_carrot_fertilizer=None, b5_jit_fertilize=None, row_shed=None):\n",
        "r04 install signature",
    )
    text = _replace_once(
        text,
        "    global B5_CARROT_FERTILIZER, B5_JIT_FERTILIZE\n",
        "    global B5_CARROT_FERTILIZER, B5_JIT_FERTILIZE, ROW_SHED\n",
        "r04 install globals",
    )
    text = _replace_once(
        text,
        "    if b5_jit_fertilize is not None:\n        B5_JIT_FERTILIZE = bool(b5_jit_fertilize)\n    return v3_agent\n",
        "    if b5_jit_fertilize is not None:\n        B5_JIT_FERTILIZE = bool(b5_jit_fertilize)\n    if row_shed is not None:\n        ROW_SHED = bool(row_shed)\n    return v3_agent\n",
        "r04 install assignment",
    )
    compile(text, str(R04_REL), "exec")
    return text


def patch_apply(text: str) -> str:
    text = _replace_once(
        text,
        '    "r04_row_order": True,\n',
        '    "r04_row_order": True,\n    "r04_row_shed": False,\n',
        "apply PARAMS row-shed",
    )
    text = _replace_once(
        text,
        '    "    r04_row_order: bool = True\\n"\n',
        '    "    r04_row_order: bool = True\\n"\n    "    r04_row_shed: bool = False\\n"\n',
        "apply Features row-shed",
    )
    # Append the new argument after B5/JIT to preserve every existing positional slot.
    text = _replace_once(
        text,
        '    "                                 bool(self.features.r04_b5_jit_fertilize))(observation, configuration)\\n"\n',
        '    "                                 bool(self.features.r04_b5_jit_fertilize),\\n"\n'
        '    "                                 bool(self.features.r04_row_shed))(observation, configuration)\\n"\n',
        "apply R04 install call",
    )
    text = _replace_once(
        text,
        '    "                self.diagnostics[\'row_order\'] = bool(self.features.r04_row_order)\\n"\n',
        '    "                self.diagnostics[\'row_order\'] = bool(self.features.r04_row_order)\\n"\n'
        '    "                self.diagnostics[\'row_shed\'] = bool(self.features.r04_row_shed)\\n"\n',
        "apply diagnostics row-shed",
    )
    compile(text, str(APPLY_REL), "exec")
    return text


def compose(v3_dir: Path, write: bool = False):
    v3_dir = Path(v3_dir)
    r04_path = v3_dir / R04_REL
    apply_path = v3_dir / APPLY_REL
    r04_before = r04_path.read_text(encoding="utf-8")
    apply_before = apply_path.read_text(encoding="utf-8")
    r04_after = patch_r04(r04_before)
    apply_after = patch_apply(apply_before)

    result = {
        "r04_before_sha256": hashlib.sha256(r04_before.encode()).hexdigest(),
        "r04_after_sha256": hashlib.sha256(r04_after.encode()).hexdigest(),
        "apply_before_sha256": hashlib.sha256(apply_before.encode()).hexdigest(),
        "apply_after_sha256": hashlib.sha256(apply_after.encode()).hexdigest(),
    }
    if write:
        r04_path.write_text(r04_after, encoding="utf-8")
        apply_path.write_text(apply_after, encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("v3_dir", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    receipt = compose(args.v3_dir, args.write)
    for key in sorted(receipt):
        print(key, receipt[key])


if __name__ == "__main__":
    main()
