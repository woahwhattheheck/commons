#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the default-OFF overflow-safe DROP theorem into current TITAN V5.

This is an integration composer, not a second gameplay implementation.  It
requires the root helper to remain byte-identical to the landed #13357 research
source and edits only the four current-lineage integration surfaces.  Every
textual edit is anchored exactly once and is emitted into a scratch postimage
tree for review before any carrier-source copyback.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGETS = ('main.py', 'titan_runtime.py', 'TITAN-CONFIG.json', 'build_integrated.py')
CANONICAL = Path('candidates/v5/research/overflow-safe-drop/overflow_safe_drop.py')
ROOT_HELPER = Path('overflow_safe_drop.py')


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


def compose_runtime(text: str) -> str:
    if 'overflow_safe_drop' in text:
        raise ValueError('titan_runtime.py already mentions overflow_safe_drop')
    text = _replace_once(
        text,
        "    exec_pace: bool = False\n",
        "    exec_pace: bool = False\n    overflow_safe_drop: bool = False\n",
        'runtime feature field',
    )
    text = _replace_once(
        text,
        "        bool_fields = (*bool_fields, 'exec_pace')\n",
        "        bool_fields = (*bool_fields, 'exec_pace', 'overflow_safe_drop')\n",
        'runtime exact-bool tuple',
    )
    anchor = (
        "        if self.exec_pace and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('exec_pace is the tested nonterminal frozen SELL composition')\n"
    )
    replacement = anchor + (
        "        if self.overflow_safe_drop and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('overflow_safe_drop is the tested nonterminal frozen composition')\n"
    )
    return _replace_once(text, anchor, replacement, 'runtime topology guard')


def compose_main(text: str) -> str:
    if "self.diagnostics['overflow_safe_drop']" in text:
        raise ValueError('main.py already wires overflow_safe_drop')
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
        "            if features.overflow_safe_drop and completed:\n"
        "                episode_steps = cfg.get('episodeSteps', 720)\n"
        "                terminal = (type(episode_steps) is not int or episode_steps < 2\n"
        "                            or obs['step'] == episode_steps - 2)\n"
        "                if terminal:\n"
        "                    self.diagnostics['overflow_safe_drop'] = {\n"
        "                        'changed': False, 'reason': 'terminal_or_invalid_episode_suppressed'}\n"
        "                else:\n"
        "                    from overflow_safe_drop import transform\n"
        "                    returned, report = transform(returned, obs, cfg)\n"
        "                    self.diagnostics['overflow_safe_drop'] = report\n"
        "                    self._checkpoint_finalizer(obs, returned, 'overflow_safe_drop')\n"
        "            return returned\n"
    )
    return _replace_once(text, anchor, replacement, 'final returned-action seam')


def compose_config(text: str) -> str:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError('TITAN-CONFIG.json must be an object')
    if 'overflow_safe_drop' in payload:
        raise ValueError('TITAN-CONFIG.json already has overflow_safe_drop')
    if payload.get('exec_pace') is not False:
        raise ValueError('expected current exec_pace default false anchor')
    payload['overflow_safe_drop'] = False
    return json.dumps(payload, indent=2) + '\n'


def compose_build(text: str) -> str:
    if "'overflow_safe_drop.py'" in text or 'test_overflow_safe_drop.py' in text:
        raise ValueError('build_integrated.py already maps overflow-safe DROP')
    text = _replace_once(
        text,
        "              'exec_pace_runtime.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:\n",
        "              'exec_pace_runtime.py','overflow_safe_drop.py','town_procurement.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:\n",
        'build runtime source map',
    )
    text = _replace_once(
        text,
        "    mapping['checks/test_early_capital.py']='test_early_capital.py'\n",
        "    mapping['checks/test_early_capital.py']='test_early_capital.py'\n"
        "    mapping['checks/test_overflow_safe_drop.py']='candidates/v5/research/overflow-safe-drop/test_overflow_safe_drop.py'\n",
        'build helper-check map',
    )
    return text


def _authenticate_helper(root: Path) -> None:
    canonical = root / CANONICAL
    helper = root / ROOT_HELPER
    if not canonical.is_file() or not helper.is_file():
        raise FileNotFoundError('canonical and root overflow helpers are required')
    if canonical.read_bytes() != helper.read_bytes():
        raise ValueError('root overflow helper differs from canonical #13357 bytes')


def materialize(root: Path, output: Path) -> dict[str, Path]:
    root = root.resolve(strict=True)
    _authenticate_helper(root)
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
