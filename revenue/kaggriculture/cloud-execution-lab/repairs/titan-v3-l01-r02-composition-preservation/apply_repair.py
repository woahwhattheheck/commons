#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-preimage carrier for the TITAN V3 L01 x R02 composition repair.

This file does not mutate the canonical V3 branch by itself. It transforms the
candidate generator only when the source is the exact audited preimage and both
anchors occur exactly once. The composed runtime patches copies of every R02
tape with L01 *before* any R02 route replacement, so later R02 tail switches
cannot erase L01 semantics and an L01 composition failure cannot leave a raw
R02 tail committed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_APPLY_V3_GIT_BLOB = "a7f716d742bd9ea45f2e370b2f151f5ee15ba042"

INIT_OLD = (
    '"        self._v3_l01_install()\\n"\n'
    '        "        self._v3_r02_install()\\n"'
)
INIT_NEW = '"        self._v3_route_install()\\n"'

R02_INSTALL_END = '''    "        except Exception as error:\\n"
    "            self.diagnostics['v3_r02'] = {'plan': None, 'reasons': ['V3_R02_ERROR_' + type(error).__name__]}\\n"
    "\\n"
'''
R02_STEP_START = '''    "    def _v3_r02_step(self, obs):\\n"
'''

ROUTE_INSTALL_METHOD = '''    "    def _v3_route_install(self):\\n"
    "        \\\"\\\"\\\"Compose L01 tape edits into R02 copies before any live R02 replacement.\\\"\\\"\\\"\\n"
    "        tape_l01 = bool(self.features.l01_land or self.features.l01_sheep or\\n"
    "                        self.features.l01_day0buy or self.features.l01_leanplant)\\n"
    "        if not (self.features.r02_route_bank and tape_l01):\\n"
    "            self._v3_l01_install()\\n"
    "            self._v3_r02_install()\\n"
    "            return\\n"
    "        from copy import deepcopy\\n"
    "        controller = self.controller\\n"
    "        routes_before = deepcopy(controller.R)\\n"
    "        fs_before = getattr(controller, '_fs_for', None)\\n"
    "        r02_before = deepcopy(getattr(self, '_v3_r02', None))\\n"
    "        try:\\n"
    "            from collections import Counter\\n"
    "            from l01_mechanics import flags_from_features, install as install_l01, patch_routes\\n"
    "            from r01_tapes import load_tapes\\n"
    "            from r02_route_bank import install as install_r02\\n"
    "            flags = flags_from_features(self.features)\\n"
    "            tapes = deepcopy(load_tapes())\\n"
    "            tape_state = {'activations': Counter(), 'reasons': []}\\n"
    "            patch_routes({str(i): tape for i, tape in enumerate(tapes)}, flags,\\n"
    "                         tape_state['activations'], tape_state['reasons'])\\n"
    "            l01 = install_l01(self, flags)\\n"
    "            r02 = install_r02(self, True, tapes=tapes)\\n"
    "            self.diagnostics['v3_l01'] = {'activations': dict(l01['activations']),\\n"
    "                                          'reasons': list(l01['reasons'])}\\n"
    "            self.diagnostics['v3_r02'] = {'plan': r02.get('plan'), 'replaced': r02.get('replaced'),\\n"
    "                                          'reasons': list(r02.get('reasons') or [])}\\n"
    "            self.diagnostics['v3_l01_r02'] = {'composed': True, 'rolled_back': False,\\n"
    "                                              'tape_activations': dict(tape_state['activations']),\\n"
    "                                              'reasons': list(tape_state['reasons'])}\\n"
    "        except Exception as error:\\n"
    "            for key in list(controller.R):\\n"
    "                if key not in routes_before:\\n"
    "                    del controller.R[key]\\n"
    "            for key, saved in routes_before.items():\\n"
    "                route = controller.R.get(key)\\n"
    "                if isinstance(route, list) and isinstance(saved, list):\\n"
    "                    route[:] = deepcopy(saved)\\n"
    "                else:\\n"
    "                    controller.R[key] = deepcopy(saved)\\n"
    "            controller._fs_for = fs_before\\n"
    "            self._v3_r02 = r02_before\\n"
    "            self.diagnostics['v3_l01_r02'] = {'composed': False, 'rolled_back': True,\\n"
    "                                              'error': type(error).__name__, 'r02_installed': False}\\n"
    "            self._v3_l01_install()\\n"
    "\\n"
'''

R02_BOUNDARY_OLD = R02_INSTALL_END + R02_STEP_START
R02_BOUNDARY_NEW = R02_INSTALL_END + ROUTE_INSTALL_METHOD + R02_STEP_START


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def transform(text: str) -> str:
    """Return repaired apply_v3.py source, rejecting stale/duplicate anchors."""
    text = _replace_once(text, INIT_OLD, INIT_NEW, "initialize composition seam")
    text = _replace_once(
        text,
        R02_BOUNDARY_OLD,
        R02_BOUNDARY_NEW,
        "R02 install/step boundary",
    )
    if text.count(INIT_NEW) != 1 or text.count(ROUTE_INSTALL_METHOD) != 1:
        raise ValueError("postimage validation failed")
    return text


def apply_file(path: Path, *, check_only: bool = False) -> tuple[str, str]:
    data = path.read_bytes()
    before = git_blob_sha(data)
    if before != EXPECTED_APPLY_V3_GIT_BLOB:
        raise ValueError(
            "apply_v3.py preimage drift: expected Git blob "
            f"{EXPECTED_APPLY_V3_GIT_BLOB}, got {before}"
        )
    repaired_bytes = transform(data.decode("utf-8")).encode("utf-8")
    after = git_blob_sha(repaired_bytes)
    if not check_only:
        path.write_bytes(repaired_bytes)
    return before, after


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "candidate",
        type=Path,
        help="path to candidates/v3 directory or its apply_v3.py",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and print postimage without writing",
    )
    args = parser.parse_args()
    path = args.candidate
    if path.is_dir():
        path = path / "apply_v3.py"
    before, after = apply_file(path, check_only=args.check)
    print(
        f"L01_R02_COMPOSITION_REPAIR before={before} after={after} "
        f"check={int(args.check)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
