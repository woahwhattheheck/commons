# SPDX-License-Identifier: Apache-2.0
"""Materialize the retry-safe R04 successor from exact production-v3.

This evidence carrier does not alter the authenticated V3.1 donor members.  It
changes only the already-injected production adapter in Arlene's vendored file:
identical same-step callbacks replay the adapter's prior R04 result without
re-entering any of R04's nested state machines.  Changed same-step evidence is
rejected before donor state can be mutated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE_SHA = "20f201161b14af7755146b08207593f9fa5df641d2f31e680792ea62c0e24239"
VENDOR = "reference/next-panel/vendor/arlene.py"
SCHEMA = "titan-v5-r04-samestep-state-custody/v1"

_INIT_ANCHOR = b"""        self._policy = r04.install(horizon=8, opening=0, row_order=True,
            evening_flush=True, sale_fertilizer=True, cattle_early=False,
            kill_late_water=False, strawberry_endgame=False,
            no_late_sale_advance=True, no_late_sale_advance_step=648,
            strawberry_topup=True, b5_carrot_fertilizer=True,
            b5_jit_fertilize=True, row_shed=True, fert_hand=True,
            terminal_fertilizer=True, goose_rescue=True)
"""
_INIT_REPLACEMENT = _INIT_ANCHOR + b"        self._r04_retry = {}\n"

_ACT_ANCHOR = b"""    def act(self, obs):
        import full_production_context
        out = self._policy(obs, full_production_context.configuration)
        state = self._r04._POLICY.players[int(obs['player'])]
        self.cur = 'R04-' + str(state.plan)
        return out
"""
_ACT_REPLACEMENT = b"""    def act(self, obs):
        import full_production_context
        from copy import deepcopy

        player = int(obs['player'])
        step = int(obs['step'])
        configuration = full_production_context.configuration
        prior = self._r04_retry.get(player)
        if prior is not None and step == prior['step']:
            if obs != prior['observation'] or configuration != prior['configuration']:
                raise RuntimeError('changed same-step R04 retry evidence')
            policy = self._r04._POLICY
            state = policy.players.get(player) if policy is not None else None
            if state is None or int(getattr(state, 'last_step', -1)) != step:
                raise RuntimeError('R04 retry state drift')
            self.cur = 'R04-' + str(state.plan)
            return deepcopy(prior['action'])
        if prior is not None and step < prior['step']:
            self._r04_retry.pop(player, None)

        out = self._policy(obs, configuration)
        state = self._r04._POLICY.players[player]
        self.cur = 'R04-' + str(state.plan)
        self._r04_retry[player] = {
            'step': step,
            'observation': deepcopy(obs),
            'configuration': deepcopy(configuration),
            'action': deepcopy(out),
        }
        return out
"""


def patch_vendor(raw: bytes) -> bytes:
    """Apply the retry wrapper at exact production-v3 adapter seams."""
    if raw.count(_INIT_ANCHOR) != 1:
        raise ValueError("expected one production R04 install seam")
    if raw.count(_ACT_ANCHOR) != 1:
        raise ValueError("expected one production R04 act seam")
    out = raw.replace(_INIT_ANCHOR, _INIT_REPLACEMENT, 1)
    out = out.replace(_ACT_ANCHOR, _ACT_REPLACEMENT, 1)
    if out == raw:
        raise AssertionError("retry-safe transform made no change")
    return out


def transform(files: dict[str, bytes]) -> dict[str, bytes]:
    if VENDOR not in files:
        raise ValueError("production archive missing vendored Arlene member")
    out = dict(files)
    out[VENDOR] = patch_vendor(files[VENDOR].replace(b"\r\n", b"\n"))
    if set(out) != set(files):
        raise AssertionError("archive membership changed")
    changed = [name for name in files if files[name] != out[name]]
    if changed != [VENDOR]:
        raise AssertionError("expected only vendored Arlene to change")
    return out


def materialize(base: Path, out_path: Path, receipt_path: Path) -> dict:
    from build_delivery import archive_bytes, digest, members
    if out_path.exists() or receipt_path.exists():
        raise FileExistsError("output and receipt paths must be new")
    source = members(base, BASE_SHA)
    changed = transform(source)
    payload = archive_bytes(changed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("xb") as stream:
        stream.write(payload)
    receipt = {
        "schema": SCHEMA,
        "base_archive_sha256": BASE_SHA,
        "candidate_archive_sha256": digest(payload),
        "member_count": len(changed),
        "changed_members": [VENDOR],
        "base_vendor_sha256": digest(source[VENDOR]),
        "candidate_vendor_sha256": digest(changed[VENDOR]),
        "same_step_contract": "identical-replay-changed-evidence-reject",
        "kaggle_submission_hold": True,
    }
    try:
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except Exception:
        out_path.unlink(missing_ok=True)
        raise
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True,
                        help="exact production-v3 archive (20f20116...)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.base, args.out, args.receipt), sort_keys=True))


if __name__ == "__main__":
    main()
