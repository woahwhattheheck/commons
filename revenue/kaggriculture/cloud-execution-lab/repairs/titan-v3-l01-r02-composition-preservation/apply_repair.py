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
import json
from pathlib import Path

EXPECTED_APPLY_V3_GIT_BLOB = "a7f716d742bd9ea45f2e370b2f151f5ee15ba042"


def _string_block(source: str) -> str:
    """Encode generated runtime source as adjacent string literals in apply_v3.py."""
    return "".join("    " + json.dumps(line) + "\n" for line in source.splitlines(keepends=True))


INIT_OLD = (
    '"        self._v3_l01_install()\\n"\n'
    '        "        self._v3_r02_install()\\n"'
)
INIT_NEW = '"        self._v3_r02_l01_install()\\n"'

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

R02_RUNTIME_NEW = '    def _v3_l01_r02_snapshot(self):\n        """Snapshot the mutable route/state seam before an R02 replacement."""\n        import copy\n        controller = self.controller\n        routes_ref = controller.R\n        route_refs = dict(routes_ref)\n        state_present = hasattr(self, \'_v3_r02\')\n        state_ref = getattr(self, \'_v3_r02\', None)\n        fs_present = hasattr(controller, \'_fs_for\')\n        fs_value = getattr(controller, \'_fs_for\', None)\n        routes_before, state_before = copy.deepcopy((routes_ref, state_ref))\n        return (controller, routes_ref, route_refs, state_present, state_ref, fs_present,\n                routes_before, state_before, fs_value)\n\n    def _v3_l01_r02_restore(self, snapshot):\n        """Restore the route-list identities plus R02/cache state from a seam snapshot."""\n        (controller, routes_ref, route_refs, state_present, state_ref, fs_present,\n         routes_before, state_before, fs_before) = snapshot\n        controller.R = routes_ref\n        routes_ref.clear()\n        routes_ref.update(route_refs)\n        restored = set()\n        for key, route in route_refs.items():\n            marker = id(route)\n            if marker in restored:\n                continue\n            route[:] = routes_before[key]\n            restored.add(marker)\n        if state_present:\n            if state_ref is None:\n                self._v3_r02 = None\n            else:\n                state_ref.clear()\n                state_ref.update(state_before)\n                self._v3_r02 = state_ref\n        elif hasattr(self, \'_v3_r02\'):\n            delattr(self, \'_v3_r02\')\n        if fs_present:\n            controller._fs_for = fs_before\n        elif hasattr(controller, \'_fs_for\'):\n            delattr(controller, \'_fs_for\')\n\n    def _v3_r02_l01_install(self):\n        """Seat R02 then L01 atomically whenever both tape lanes are active."""\n        tape_l01 = bool(self.features.l01_land or self.features.l01_sheep or\n                        self.features.l01_day0buy or self.features.l01_leanplant)\n        if not self.features.r02_route_bank or not tape_l01:\n            self._v3_r02_install()\n            self._v3_l01_install()\n            return\n        snapshot = None\n        try:\n            snapshot = self._v3_l01_r02_snapshot()\n            self._v3_r02_install()\n            self._v3_l01_install()\n            r02_reasons = list((self.diagnostics.get(\'v3_r02\') or {}).get(\'reasons\') or [])\n            l01_reasons = list((self.diagnostics.get(\'v3_l01\') or {}).get(\'reasons\') or [])\n            error = next((reason for reason in r02_reasons\n                          if isinstance(reason, str) and reason.startswith(\'V3_R02_ERROR_\')), None)\n            if error is None:\n                error = next((reason for reason in l01_reasons\n                              if isinstance(reason, str) and reason.startswith(\'V3_L01_ERROR_\')), None)\n            if error is not None:\n                self._v3_l01_r02_restore(snapshot)\n                if isinstance(self.diagnostics.get(\'v3_r02\'), dict):\n                    self.diagnostics[\'v3_r02\'][\'rolled_back\'] = True\n                self.diagnostics[\'v3_l01_r02_init\'] = {\'rolled_back\': True, \'error\': error}\n                return\n            self.diagnostics[\'v3_l01_r02_init\'] = {\'rolled_back\': False, \'l01_applied\': True}\n        except Exception as error:\n            if snapshot is not None:\n                self._v3_l01_r02_restore(snapshot)\n                if isinstance(self.diagnostics.get(\'v3_r02\'), dict):\n                    self.diagnostics[\'v3_r02\'][\'rolled_back\'] = True\n            self.diagnostics[\'v3_l01_r02_init\'] = {\'rolled_back\': True,\n                                                   \'error\': type(error).__name__}\n\n    def _v3_r02_step(self, obs):\n        """V3 lane R02: atomically preserve L01 tape edits across route-bank replacements."""\n        if not self.features.r02_route_bank:\n            return\n        try:\n            from r02_route_bank import FINAL_PLAN_STEP, ROUTE_STEP, plan_for, step\n            current = getattr(self, \'_v3_r02\', None)\n            obs_step = obs.get(\'step\')\n            if obs_step is None:\n                obs_step = int(obs.get(\'day\', 0)) * 24 + int(obs.get(\'hour\', 0))\n            obs_step = int(obs_step)\n            will_replace = False\n            if current is not None and current.get(\'tapes\') is not None:\n                if obs_step >= ROUTE_STEP and current.get(\'plan\') in (None, 0):\n                    will_replace = bool(plan_for(obs))\n                if obs_step >= FINAL_PLAN_STEP and not current.get(\'endgame\'):\n                    will_replace = True\n            if not will_replace:\n                state = step(self, obs, True)\n                self.diagnostics[\'v3_r02_step\'] = {\'plan\': state.get(\'plan\'),\n                                                   \'endgame\': state.get(\'endgame\'),\n                                                   \'replaced\': state.get(\'replaced\'),\n                                                   \'l01_reapplied\': False,\n                                                   \'rolled_back\': False}\n                return\n\n            snapshot = self._v3_l01_r02_snapshot()\n            before = int((current or {}).get(\'replaced\') or 0)\n            try:\n                state = step(self, obs, True)\n                after = int((state or {}).get(\'replaced\') or 0)\n                l01_reapplied = False\n                if after > before and (self.features.l01_land or self.features.l01_sheep or\n                                       self.features.l01_day0buy or self.features.l01_leanplant):\n                    self._v3_l01_install()\n                    l01_reasons = list((self.diagnostics.get(\'v3_l01\') or {}).get(\'reasons\') or [])\n                    l01_error = next((reason for reason in l01_reasons\n                                      if isinstance(reason, str) and reason.startswith(\'V3_L01_ERROR_\')), None)\n                    if l01_error is not None:\n                        self._v3_l01_r02_restore(snapshot)\n                        self.diagnostics[\'v3_r02_step\'] = {\'plan\': (current or {}).get(\'plan\'),\n                                                           \'endgame\': (current or {}).get(\'endgame\'),\n                                                           \'replaced\': before,\n                                                           \'l01_reapplied\': False,\n                                                           \'rolled_back\': True,\n                                                           \'error\': l01_error}\n                        return\n                    l01_reapplied = True\n                self.diagnostics[\'v3_r02_step\'] = {\'plan\': state.get(\'plan\'),\n                                                   \'endgame\': state.get(\'endgame\'),\n                                                   \'replaced\': state.get(\'replaced\'),\n                                                   \'l01_reapplied\': l01_reapplied,\n                                                   \'rolled_back\': False}\n            except Exception as error:\n                self._v3_l01_r02_restore(snapshot)\n                self.diagnostics[\'v3_r02_step\'] = {\'plan\': (current or {}).get(\'plan\'),\n                                                   \'endgame\': (current or {}).get(\'endgame\'),\n                                                   \'replaced\': before,\n                                                   \'l01_reapplied\': False,\n                                                   \'rolled_back\': True,\n                                                   \'error\': type(error).__name__}\n        except Exception as error:\n            self.diagnostics[\'v3_r02_step\'] = {\'error\': type(error).__name__,\n                                               \'l01_reapplied\': False,\n                                               \'rolled_back\': False}\n\n'
R02_METHOD_NEW = _string_block(R02_RUNTIME_NEW)


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
