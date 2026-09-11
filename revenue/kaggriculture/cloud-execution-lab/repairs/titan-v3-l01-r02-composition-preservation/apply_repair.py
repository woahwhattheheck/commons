#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-preimage carrier for the TITAN V3 L01 x R02 composition repair.

This file does not mutate the canonical V3 branch by itself.  It transforms the
candidate generator only when the source is the exact audited preimage and both
anchors occur exactly once.  That lets the S17/T08 integrator compose the fix
without racing the active L01, R02, or generator-hardening owners.
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
INIT_NEW = (
    '"        self._v3_r02_install()\\n"\n'
    '        "        self._v3_l01_install()\\n"'
)

R02_METHOD_OLD = '''    "    def _v3_r02_step(self, obs):\\n"
    "        \\\"\\\"\\\"V3 lane R02: the published plan switches at steps 144 and 648. Identity when off.\\\"\\\"\\\"\\n"
    "        if not self.features.r02_route_bank:\\n"
    "            return\\n"
    "        try:\\n"
    "            from r02_route_bank import step\\n"
    "            state = step(self, obs, True)\\n"
    "            self.diagnostics['v3_r02_step'] = {'plan': state.get('plan'), 'endgame': state.get('endgame'),\\n"
    "                                               'replaced': state.get('replaced')}\\n"
    "        except Exception as error:\\n"
    "            self.diagnostics['v3_r02_step'] = {'error': type(error).__name__}\\n"
    "\\n"
'''

R02_METHOD_NEW = '''    "    def _v3_r02_step(self, obs):\\n"
    "        \\\"\\\"\\\"V3 lane R02: preserve L01 tape edits across route-bank replacements.\\\"\\\"\\\"\\n"
    "        if not self.features.r02_route_bank:\\n"
    "            return\\n"
    "        try:\\n"
    "            from r02_route_bank import step\\n"
    "            before = int((getattr(self, '_v3_r02', None) or {}).get('replaced') or 0)\\n"
    "            state = step(self, obs, True)\\n"
    "            after = int((state or {}).get('replaced') or 0)\\n"
    "            l01_reapplied = False\\n"
    "            if after > before and (self.features.l01_land or self.features.l01_sheep or\\n"
    "                                   self.features.l01_day0buy or self.features.l01_leanplant):\\n"
    "                self._v3_l01_install()\\n"
    "                l01_reapplied = True\\n"
    "            self.diagnostics['v3_r02_step'] = {'plan': state.get('plan'), 'endgame': state.get('endgame'),\\n"
    "                                               'replaced': state.get('replaced'),\\n"
    "                                               'l01_reapplied': l01_reapplied}\\n"
    "        except Exception as error:\\n"
    "            self.diagnostics['v3_r02_step'] = {'error': type(error).__name__}\\n"
    "\\n"
'''


def git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def transform(text: str) -> str:
    """Return the repaired apply_v3.py source, rejecting stale/duplicate anchors."""
    text = _replace_once(text, INIT_OLD, INIT_NEW, "initialize order")
    text = _replace_once(text, R02_METHOD_OLD, R02_METHOD_NEW, "R02 step method")
    if text.count(INIT_NEW) != 1 or text.count(R02_METHOD_NEW) != 1:
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
    original = data.decode("utf-8")
    repaired = transform(original)
    repaired_bytes = repaired.encode("utf-8")
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
    parser.add_argument("--check", action="store_true", help="validate and print postimage without writing")
    args = parser.parse_args()
    path = args.candidate
    if path.is_dir():
        path = path / "apply_v3.py"
    before, after = apply_file(path, check_only=args.check)
    print(f"L01_R02_COMPOSITION_REPAIR before={before} after={after} check={int(args.check)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
