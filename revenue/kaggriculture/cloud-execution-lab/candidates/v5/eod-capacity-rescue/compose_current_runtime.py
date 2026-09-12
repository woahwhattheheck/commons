#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the default-OFF EOD-capacity rescue into current TITAN V5.

The composer deliberately edits only four current-lineage integration surfaces
and fails closed unless each expected anchor occurs exactly once.  It writes a
scratch postimage tree; callers review/test the postimages before copying them
back to the owned carrier branch.
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
        "    exec_pace: bool = False\n",
        "    exec_pace: bool = False\n    eod_capacity_rescue: bool = False\n",
        'runtime feature field',
    )
    text = _replace_once(
        text,
        "        bool_fields = (*bool_fields, 'exec_pace')\n",
        "        bool_fields = (*bool_fields, 'exec_pace', 'eod_capacity_rescue')\n",
        'runtime exact-bool tuple',
    )
    anchor = (
        "        if self.exec_pace and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('exec_pace is the tested nonterminal frozen SELL composition')\n"
    )
    replacement = anchor + (
        "        if self.eod_capacity_rescue and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('eod_capacity_rescue is the tested nonterminal frozen SELL composition')\n"
    )
    return _replace_once(text, anchor, replacement, 'runtime topology guard')


def compose_main(text: str) -> str:
    if "self.diagnostics['eod_capacity_rescue']" in text:
        raise ValueError('main.py already wires eod_capacity_rescue')
    anchor = (
        "            if self.town_procurement_enabled:\n"
        "                from town_procurement import apply\n"
        "                returned, report = apply(obs, returned, cfg, completed=completed)\n"
        "                self.diagnostics['town_procurement'] = report\n"
        "                self._checkpoint_finalizer(obs, returned, 'town_procurement')\n"
        "            return returned\n"
    )
    replacement = (
        "            if self.town_procurement_enabled:\n"
        "                from town_procurement import apply\n"
        "                returned, report = apply(obs, returned, cfg, completed=completed)\n"
        "                self.diagnostics['town_procurement'] = report\n"
        "                self._checkpoint_finalizer(obs, returned, 'town_procurement')\n"
        "            if features.eod_capacity_rescue:\n"
        "                from eod_capacity_rescue import apply_native_eod_capacity_rescue\n"
        "                returned, report = apply_native_eod_capacity_rescue(\n"
        "                    returned, obs, cfg, enabled=True)\n"
        "                self.diagnostics['eod_capacity_rescue'] = report\n"
        "                self._checkpoint_finalizer(obs, returned, 'eod_capacity_rescue')\n"
        "            return returned\n"
    )
    return _replace_once(text, anchor, replacement, 'final returned-action seam')


def compose_config(text: str) -> str:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError('TITAN-CONFIG.json must be an object')
    if 'eod_capacity_rescue' in payload:
        raise ValueError('TITAN-CONFIG.json already has eod_capacity_rescue')
    if payload.get('exec_pace') is not False:
        raise ValueError('expected current exec_pace default false anchor')
    # Keep insertion beside the newest production feature while preserving the
    # canonical pretty-printed JSON shape used by this repository.
    payload['eod_capacity_rescue'] = False
    return json.dumps(payload, indent=2) + '\n'


def compose_build(text: str) -> str:
    if "mapping['eod_capacity_rescue.py']" in text or "checks/test_eod_capacity_rescue.py" in text:
        raise ValueError('build_integrated.py already maps EOD rescue')
    text = _replace_once(
        text,
        "              'exec_pace_runtime.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:\n",
        "              'exec_pace_runtime.py','eod_capacity_rescue.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:\n",
        'build runtime source map',
    )
    text = _replace_once(
        text,
        "    mapping['checks/test_early_capital.py']='test_early_capital.py'\n",
        "    mapping['checks/test_early_capital.py']='test_early_capital.py'\n"
        "    mapping['checks/test_eod_capacity_rescue.py']='test_eod_capacity_rescue.py'\n",
        'build focused check map',
    )
    return text


def materialize(root: Path, output: Path) -> dict[str, Path]:
    root = root.resolve(strict=True)
    helper = root / 'eod_capacity_rescue.py'
    test = root / 'test_eod_capacity_rescue.py'
    if not helper.is_file() or not test.is_file():
        raise FileNotFoundError('carrier helper and focused test must already exist at root')
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
