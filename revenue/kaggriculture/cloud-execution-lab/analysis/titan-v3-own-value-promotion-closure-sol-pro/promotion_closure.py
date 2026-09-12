#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Public facade for TITAN own-value promotion-evidence closure."""
from __future__ import annotations

import promotion_core as _core
import promotion_seed as _seed
import promotion_manifest as _manifest
import promotion_trajectory as _trajectory
import promotion_policy as _policy
import promotion_assess as _assess

for _module in (_core, _seed, _manifest, _trajectory, _policy, _assess):
    for _name in dir(_module):
        if not _name.startswith("__"):
            globals()[_name] = getattr(_module, _name)

main = _assess.main

if __name__ == "__main__":
    raise SystemExit(main())
