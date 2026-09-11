# SPDX-License-Identifier: Apache-2.0
"""Direct evaluator entrypoint for the default-off E5 floor-liquidation experiment."""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
for path in (HERE, V3_ROOT / "overlay"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_e5_floor_liquidation as e5  # noqa: E402

agent = e5.install(enabled=True)
