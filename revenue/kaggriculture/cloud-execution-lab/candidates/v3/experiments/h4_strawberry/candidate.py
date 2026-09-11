# SPDX-License-Identifier: Apache-2.0
"""Direct evaluator entrypoint for the default-off H4 experiment.

This file is intentionally outside ``overlay/**`` and is not a V3 package input.  It
exists so paired evidence can execute the exact reviewed H4 bytes without an ad-hoc
external wrapper.  Importing this module arms only the H4 strawberry top-up on top of
the branch's existing R04 defaults and exposes the standard module-level ``agent``.
"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
for path in (HERE, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_h4_strawberry as h4  # noqa: E402

agent = h4.install(strawberry_topup=True)
