#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed source and semantic receipt for the inherited SELL priority patch."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
OPERATION = 'titan-v3-inherited-sell-priority-20260910-sol-priority-01'
FILES = {
    'scheduler.py': LAB / 'scheduler.py',
    'frozen_selected.py': LAB / 'frozen_selected.py',
    'build_integrated.py': LAB / 'build_integrated.py',
}
EXPECTED_BEFORE_BLOBS = {
    'scheduler.py': 'a483b24dd72b580d7d8811636b54d2d44f391575',
    'frozen_selected.py': 'fc7baf5c179818a55037f6a61d92984d81d1a21c',
    'build_integrated.py': '05994d946885ff0fe2a2ce77439fd335174900aa',
}
EXPECTED_CARRIER_BLOBS = {
    'change.patch': 'c5c604c758e90dd614c54a8370230df7f244dce1',
    'test_scheduler_priority.py': 'b651e0e35f0736b059206d2f214f4bbe8a686d4f',
}
OLD_TARGET = (
    "targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    "if shed.get(p,0)>0}"
)
NEW_TARGET = 'targets=ordered_targets(shed,self.pending,baseline_q)'
BUILD_ENTRY = (
    "mapping['checks/test_scheduler_priority.py']='test_scheduler_priority.py'"
)


class VerificationError(ValueError):
    """The exact patch boundary or semantic contract is not satisfied."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b'blob ' + str(len(data)).encode('ascii') + b'\0' + data
    ).hexdigest()


def read_regular(path: Path) -> bytes:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise VerificationError(f'missing required file: {path}') from exc
    if not stat.S_ISREG(info.st_mode):
        raise VerificationError(f'required file is not regular: {path}')
    data = path.read_bytes()
    if not data:
        raise VerificationError(f'required file is empty: {path}')
    return data


def decode(path: Path, data: bytes) -> str:
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise VerificationError(f'file is not UTF-8: {path}') from exc


def require_count(text: str, needle: str, expected: int, label: str) -> None:
    actual = text.count(needle)
    if actual != expected:
        raise VerificationError(
            f'{label}: expected {expected} occurrence(s), found {actual}'
        )


def parse_module(name: str, text: str) -> ast.Module:
    try:
        return ast.parse(text, filename=name)
    except SyntaxError as exc:
        raise VerificationError(f'{name} does not parse: {exc}') from exc


def ordered_target_calls(tree: ast.AST) -> int:
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'ordered_targets'
    )


def helper_definitions(tree: ast.AST) -> int:
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == 'ordered_targets'
    )


def inventory() -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    raw = {name: read_regular(path) for name, path in FILES.items()}
    records = {
        name: {
            'bytes': len(data),
            'sha256': sha256(data),
            'git_blob_sha1': git_blob_sha1(data),
        }
        for name, data in raw.items()
    }
    return raw, records


def validate_carrier() -> dict[str, dict[str, Any]]:
    paths = {
        'change.patch': HERE / 'change.patch',
        'test_scheduler_priority.py': LAB / 'test_scheduler_priority.py',
    }
    records = {}
    for name, path in paths.items():
        data = read_regular(path)
        actual_blob = git_blob_sha1(data)
        expected_blob = EXPECTED_CARRIER_BLOBS[name]
        if actual_blob != expected_blob:
            raise VerificationError(
                f'{name}: carrier blob mismatch: expected {expected_blob}, '
                f'got {actual_blob}'
            )
        records[name] = {
            'bytes': len(data),
            'git_blob_sha1': actual_blob,
            'sha256': sha256(data),
        }
    return records


def validate_before(texts: dict[str, str], records: dict[str, dict[str, Any]]) -> None:
    for name, expected in EXPECTED_BEFORE_BLOBS.items():
        actual = records[name]['git_blob_sha1']
        if actual != expected:
            raise VerificationError(
                f'{name}: predecessor blob drift: expected {expected}, got {actual}'
            )
    require_count(texts['scheduler.py'], OLD_TARGET, 1, 'scheduler predecessor')
    require_count(texts['frozen_selected.py'], OLD_TARGET, 1, 'selected predecessor')
    require_count(texts['scheduler.py'], NEW_TARGET, 0, 'scheduler successor')
    require_count(texts['frozen_selected.py'], NEW_TARGET, 0, 'selected successor')
    require_count(texts['build_integrated.py'], BUILD_ENTRY, 0, 'release test entry')
    scheduler_tree = parse_module('scheduler.py', texts['scheduler.py'])
    frozen_tree = parse_module('frozen_selected.py', texts['frozen_selected.py'])
    if helper_definitions(scheduler_tree) or ordered_target_calls(scheduler_tree):
        raise VerificationError('scheduler predecessor already contains priority helper')
    if ordered_target_calls(frozen_tree):
        raise VerificationError('selected predecessor already contains priority helper call')


def validate_after(texts: dict[str, str]) -> None:
    require_count(texts['scheduler.py'], OLD_TARGET, 0, 'scheduler predecessor')
    require_count(texts['frozen_selected.py'], OLD_TARGET, 0, 'selected predecessor')
    require_count(texts['scheduler.py'], NEW_TARGET, 1, 'scheduler successor')
    require_count(texts['frozen_selected.py'], NEW_TARGET, 1, 'selected successor')
    require_count(texts['build_integrated.py'], BUILD_ENTRY, 1, 'release test entry')
    scheduler_tree = parse_module('scheduler.py', texts['scheduler.py'])
    frozen_tree = parse_module('frozen_selected.py', texts['frozen_selected.py'])
    parse_module('build_integrated.py', texts['build_integrated.py'])
    if helper_definitions(scheduler_tree) != 1:
        raise VerificationError('scheduler must define exactly one ordered_targets helper')
    if ordered_target_calls(scheduler_tree) != 1:
        raise VerificationError('direct scheduler must call ordered_targets exactly once')
    if ordered_target_calls(frozen_tree) != 1:
        raise VerificationError('selected scheduler must call ordered_targets exactly once')


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('before', 'after'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    carrier = validate_carrier()
    raw, records = inventory()
    texts = {name: decode(FILES[name], data) for name, data in raw.items()}
    if args.phase == 'before':
        validate_before(texts, records)
    else:
        validate_after(texts)
    receipt = {
        'schema_version': 1,
        'operation': OPERATION,
        'phase': args.phase,
        'carrier': carrier,
        'files': records,
        'semantics': {
            'target_membership': 'all positive non-operating shed products',
            'priority': ['pending insertion order', 'baseline SELL insertion order',
                         'remaining stable PRODUCTS order'],
            'direct_scheduler_calls': ordered_target_calls(
                parse_module('scheduler.py', texts['scheduler.py'])
            ),
            'selected_scheduler_calls': ordered_target_calls(
                parse_module('frozen_selected.py', texts['frozen_selected.py'])
            ),
        },
    }
    atomic_json(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
