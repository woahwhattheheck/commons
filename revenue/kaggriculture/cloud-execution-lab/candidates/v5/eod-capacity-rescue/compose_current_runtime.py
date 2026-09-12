#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the default-OFF EOD-capacity rescue into current TITAN V5.

The composer is source-custody evidence for the serial late-finalizer chain.
It edits only the four current-lineage integration surfaces and fails closed
unless the exact post-overflow anchors occur once.  The intended returned-action
order is pressure -> town procurement -> overflow-safe-drop -> EOD rescue ->
return.  Combined row-order/shed is downstream and deliberately absent here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGETS = ('main.py', 'titan_runtime.py', 'TITAN-CONFIG.json', 'build_integrated.py')


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


def compose_runtime(text: str) -> str:
    if 'eod_capacity_rescue' in text:
        raise ValueError('titan_runtime.py already mentions eod_capacity_rescue')
    text = _replace_once(
        text,
        "    overflow_safe_drop: bool = False\n",
        "    overflow_safe_drop: bool = False\n    eod_capacity_rescue: bool = False\n",
        'runtime post-overflow feature field',
    )
    text = _replace_once(
        text,
        "        bool_fields = (*bool_fields, 'exec_pace', 'overflow_safe_drop')\n",
        "        bool_fields = (*bool_fields, 'exec_pace', 'overflow_safe_drop', 'eod_capacity_rescue')\n",
        'runtime exact-bool tuple',
    )
    anchor = (
        "        if self.overflow_safe_drop and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('overflow_safe_drop is the tested nonterminal frozen composition')\n"
    )
    replacement = anchor + (
        "        if self.eod_capacity_rescue and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('eod_capacity_rescue is the tested post-overflow frozen composition')\n"
    )
    return _replace_once(text, anchor, replacement, 'runtime post-overflow topology guard')


def compose_main(text: str) -> str:
    if "self.diagnostics['eod_capacity_rescue']" in text:
        raise ValueError('main.py already wires eod_capacity_rescue')
    anchor = (
        "            # Overflow preservation is an optional final-return transform only.\n"
        "            # Do not run it on an incomplete producer result or on the terminal\n"
        "            # settlement step, where liquidation semantics own the returned bytes.\n"
        "            if self.overflow_safe_drop is not None and completed:\n"
        "                episode_steps = cfg.get('episodeSteps', 720)\n"
        "                nonterminal = (type(episode_steps) is int and episode_steps >= 2\n"
        "                               and obs.get('step') != episode_steps - 2)\n"
        "                if nonterminal:\n"
        "                    returned, report = self.overflow_safe_drop.transform(returned, obs, cfg)\n"
        "                    self.diagnostics['overflow_safe_drop'] = report\n"
        "                    self._checkpoint_finalizer(obs, returned, 'overflow_safe_drop')\n"
        "            return returned\n"
    )
    replacement = anchor[:-len("            return returned\n")] + (
        "            # EOD capacity rescue is serially downstream of overflow.  It\n"
        "            # consumes exactly those returned bytes once and never starts\n"
        "            # after an incomplete producer result.\n"
        "            if features.eod_capacity_rescue and completed:\n"
        "                from eod_capacity_rescue import apply_native_eod_capacity_rescue\n"
        "                returned, report = apply_native_eod_capacity_rescue(\n"
        "                    returned, obs, cfg, enabled=True)\n"
        "                self.diagnostics['eod_capacity_rescue'] = report\n"
        "                self._checkpoint_finalizer(obs, returned, 'eod_capacity_rescue')\n"
        "            return returned\n"
    )
    return _replace_once(text, anchor, replacement, 'post-overflow final returned-action seam')


def compose_config(text: str) -> str:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError('TITAN-CONFIG.json must be an object')
    if 'eod_capacity_rescue' in payload:
        raise ValueError('TITAN-CONFIG.json already has eod_capacity_rescue')
    if payload.get('overflow_safe_drop') is not False:
        raise ValueError('expected canonical overflow_safe_drop default false anchor')
    payload['eod_capacity_rescue'] = False
    return json.dumps(payload, indent=2) + '\n'


def compose_build(text: str) -> str:
    if ("'eod_capacity_rescue.py'" in text
            or "checks/test_eod_capacity_rescue.py" in text
            or "checks/test_eod_capacity_rescue_runtime.py" in text):
        raise ValueError('build_integrated.py already maps EOD rescue')
    text = _replace_once(
        text,
        "              'exec_pace_runtime.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:\n",
        "              'exec_pace_runtime.py','eod_capacity_rescue.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:\n",
        'build runtime source map',
    )
    text = _replace_once(
        text,
        "    mapping['checks/test_overflow_safe_drop.py']='candidates/v5/research/overflow-safe-drop/test_overflow_safe_drop.py'\n",
        "    mapping['checks/test_overflow_safe_drop.py']='candidates/v5/research/overflow-safe-drop/test_overflow_safe_drop.py'\n"
        "    mapping['checks/test_eod_capacity_rescue.py']='test_eod_capacity_rescue.py'\n"
        "    mapping['checks/test_eod_capacity_rescue_runtime.py']='test_eod_capacity_rescue_runtime.py'\n",
        'build post-overflow focused/runtime check map',
    )
    return text


def materialize(root: Path, output: Path) -> dict[str, Path]:
    root = root.resolve(strict=True)
    helper = root / 'eod_capacity_rescue.py'
    focused_test = root / 'test_eod_capacity_rescue.py'
    runtime_test = root / 'test_eod_capacity_rescue_runtime.py'
    if not helper.is_file() or not focused_test.is_file() or not runtime_test.is_file():
        raise FileNotFoundError('carrier helper plus focused/runtime tests must already exist at root')
    if output.exists():
        raise FileExistsError(f'output already exists: {output}')
    output.mkdir(parents=True)
    transforms = {
        'main.py': compose_main,
        'titan_runtime.py': compose_runtime,
        'TITAN-CONFIG.json': compose_config,
        'build_integrated.py': compose_build,
    }
    result = {}
    for name in TARGETS:
        source = root / name
        if not source.is_file():
            raise FileNotFoundError(source)
        rendered = transforms[name](source.read_text(encoding='utf-8'))
        target = output / name
        target.write_text(rendered, encoding='utf-8')
        result[name] = target
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    outputs = materialize(args.root, args.out)
    print(json.dumps({'outputs': {name: str(path) for name, path in outputs.items()}}, sort_keys=True))


if __name__ == '__main__':
    main()
