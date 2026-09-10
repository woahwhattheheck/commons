# SPDX-License-Identifier: Apache-2.0
"""Bind Capillary panel opponents to exact executable transitive closures.

The parent panel fingerprints only entry files. Frozen V1's 66-byte entrypoint
imports ``scheduler`` from its ambient import path, so the same reported entry
hash can execute different policy bytes. This carrier copies the complete
published V1 freeze into private regular-file payloads, generates wrappers that
verify those payloads before import, attests module origins after import, and
revalidates everything after the game panels finish.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence
HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
V1_ROOT = LAB / 'runtime' / 'variants' / 'v1'
FREEZE = V1_ROOT / 'FREEZE.json'
OPERATION = 'titan-v3-capillary-opponent-transitive-closure-20260910-sol-pro-01'
VERIFY_OPERATION = OPERATION + '-post-panel-verify'
PARENT_HEAD = 'ce740f7d767136185c1bfee46e4a798c17b12303'
EXPECTED_FREEZE_SHA256 = 'b31860daad9da6b46509f79f820139080743f07d43f61aad14ce1dd272d71d41'
EXPECTED_FREEZE_BYTES = 1945
EXPECTED_FREEZE_VARIANT = 'v1'
EXPECTED_FREEZE_PHASE = 'development'
EXPECTED_FREEZE_TIME = '2026-09-07T18:18:31.433794+00:00'
EXPECTED_FILES: dict[str, dict[str, Any]] = {'candidate.py': {'sha256': '2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2', 'bytes': 66}, 'scheduler.py': {'sha256': 'a4eef6065f79cf73a977b7c9f7913cc054f203c27660c4d780f780735ffcfd2f', 'bytes': 17663}, 'naive.py': {'sha256': '56de2de846e4443be84482d7e137381aba577a10c5aa5742c3126c2fa2e2401c', 'bytes': 81}, 'mechanics.py': {'sha256': '579965e589237d1e5bbcc8b8448188f91b173d4480430d34b3a7f0e07e0c48d3', 'bytes': 22526}, 'reference/decision/decision.py': {'sha256': '9d78406668c927785b29f5bf2b5a67f0263bfcd63f626c881a60bad5f8293c52', 'bytes': 7759}, 'reference/decision/README.md': {'sha256': '98c3c233192c83042c80c275cabe2d0ae382baab01ed04e69266ed90042c5bb2', 'bytes': 9410}, 'reference/engine/LICENSE': {'sha256': 'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4', 'bytes': 11357}, 'reference/next-panel/UPSTREAM.json': {'sha256': '617e055107bf0fed5ae4ba55e9468398debdc09aa7c304a3e18cadbc283f251b', 'bytes': 3131}, 'reference/next-panel/NEXT-DISTRIBUTION-NOTICE.txt': {'sha256': '2c32238779169ecf5e673b58d50c94573e3128dda27d2ba5496459477132b02e', 'bytes': 836}, 'reference/next-panel/LICENSE': {'sha256': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30', 'bytes': 11358}, 'reference/next-panel/vendor/arlene.py': {'sha256': '1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4', 'bytes': 46342}}
OPPONENT_SPECS: dict[str, dict[str, Any]] = {'arlene': {'entry_name': 'arlene.py', 'source_files': ('reference/next-panel/vendor/arlene.py',), 'entry_source': 'reference/next-panel/vendor/arlene.py', 'module_origins': {}, 'attribute_origins': {}}, 'v1': {'entry_name': 'candidate.py', 'source_files': tuple(EXPECTED_FILES), 'entry_source': 'candidate.py', 'module_origins': {'scheduler': 'scheduler.py', 'mechanics': 'mechanics.py'}, 'attribute_origins': {'scheduler.parent': 'reference/next-panel/vendor/arlene.py', 'scheduler.receipt_math': 'reference/decision/decision.py'}}}

class BindingError(ValueError):
    """The frozen source, private payload, wrapper, or receipt is unbound."""

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\x00' + data).hexdigest()

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def object_sha256(value: Any) -> str:
    return sha256(canonical_bytes(value))

def lower_hex(value: Any, length: int, label: str) -> str:
    if not isinstance(value, str) or len(value) != length or any((char not in '0123456789abcdef' for char in value)):
        raise BindingError(f'{label} is not lowercase {length}-hex')
    return value

def strict_object_bytes(raw: bytes, label: str) -> dict[str, Any]:

    def pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in rows:
            if key in result:
                raise BindingError(f'duplicate JSON key {key!r} in {label}')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=lambda token: (_ for _ in ()).throw(BindingError(f'non-finite JSON token {token!r} in {label}')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError(f'cannot parse {label}: {type(exc).__name__}: {exc}') from exc
    if not isinstance(value, dict):
        raise BindingError(f'{label} must contain one JSON object')
    return value

def strict_object(path: Path, label: str | None=None) -> dict[str, Any]:
    return strict_object_bytes(regular_bytes(path, label or str(path)), label or str(path))

def safe_relative(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or '\\' in value or ('\x00' in value):
        raise BindingError(f'{label} is not a safe relative path')
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts or any((part in ('', '.', '..') for part in pure.parts)) or (PurePosixPath(*pure.parts).as_posix() != value):
        raise BindingError(f'{label} is not a canonical relative path: {value!r}')
    return value

def regular_bytes(path: Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise BindingError(f'cannot stat {label} {path}: {exc}') from exc
    if not stat.S_ISREG(info.st_mode):
        raise BindingError(f'{label} is not one regular file: {path}')
    try:
        return path.read_bytes()
    except OSError as exc:
        raise BindingError(f'cannot read {label} {path}: {exc}') from exc

def identity(path: Path, label: str) -> dict[str, Any]:
    data = regular_bytes(path, label)
    return {'bytes': len(data), 'sha256': sha256(data), 'git_blob_sha1': git_blob(data)}

def _inventory(root: Path, label: str) -> list[dict[str, Any]]:
    try:
        root_info = root.lstat()
    except OSError as exc:
        raise BindingError(f'cannot stat {label} root {root}: {exc}') from exc
    if not stat.S_ISDIR(root_info.st_mode):
        raise BindingError(f'{label} root is not one directory: {root}')
    rows: list[dict[str, Any]] = []
    try:
        paths = sorted(root.rglob('*'), key=lambda item: item.relative_to(root).as_posix())
    except OSError as exc:
        raise BindingError(f'cannot inventory {label} root: {exc}') from exc
    for path in paths:
        relative = safe_relative(path.relative_to(root).as_posix(), f'{label} member')
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise BindingError(f'{label} contains non-regular member {relative!r}')
        data = path.read_bytes()
        rows.append({'path': relative, 'bytes': len(data), 'sha256': sha256(data), 'git_blob_sha1': git_blob(data)})
    if not rows:
        raise BindingError(f'{label} inventory is empty')
    return rows

def closure_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    seen: set[str] = set()
    for row in sorted(rows, key=lambda value: str(value.get('path'))):
        if not isinstance(row, Mapping):
            raise BindingError('closure row is not an object')
        path = safe_relative(row.get('path'), 'closure path')
        if path in seen:
            raise BindingError(f'duplicate closure path {path!r}')
        seen.add(path)
        count = row.get('bytes')
        value = lower_hex(row.get('sha256'), 64, f'closure sha256 for {path}')
        if type(count) is not int or count < 0:
            raise BindingError(f'invalid closure byte count for {path}')
        digest.update(path.encode('utf-8'))
        digest.update(b'\x00')
        digest.update(str(count).encode('ascii'))
        digest.update(b'\x00')
        digest.update(value.encode('ascii'))
        digest.update(b'\x00')
    if not seen:
        raise BindingError('cannot hash an empty closure')
    return digest.hexdigest()

def _expected_freeze_files() -> dict[str, dict[str, Any]]:
    prefix = 'runtime/variants/v1/'
    return {prefix + relative: {'sha256': metadata['sha256'], 'bytes': metadata['bytes']} for relative, metadata in EXPECTED_FILES.items()}

def source_inventory(root: Path=V1_ROOT) -> list[dict[str, Any]]:
    """Validate the immutable V1 freeze and return its executable file inventory."""
    root = root.resolve()
    raw = regular_bytes(root / 'FREEZE.json', 'frozen V1 manifest')
    if len(raw) != EXPECTED_FREEZE_BYTES or sha256(raw) != EXPECTED_FREEZE_SHA256:
        raise BindingError('frozen V1 FREEZE.json identity drift')
    freeze = strict_object_bytes(raw, 'frozen V1 FREEZE.json')
    expected_freeze = {'variant': EXPECTED_FREEZE_VARIANT, 'frozen_at_utc': EXPECTED_FREEZE_TIME, 'phase': EXPECTED_FREEZE_PHASE, 'files': _expected_freeze_files()}
    if freeze != expected_freeze:
        raise BindingError('frozen V1 manifest semantics drift')
    inventory = _inventory(root, 'frozen V1 source')
    indexed = {row['path']: row for row in inventory}
    expected_paths = set(EXPECTED_FILES) | {'FREEZE.json'}
    if set(indexed) != expected_paths:
        raise BindingError(f'frozen V1 source inventory drift; missing={sorted(expected_paths - set(indexed))}, extra={sorted(set(indexed) - expected_paths)}')
    manifest = indexed['FREEZE.json']
    if manifest['bytes'] != EXPECTED_FREEZE_BYTES or manifest['sha256'] != EXPECTED_FREEZE_SHA256:
        raise BindingError('frozen V1 manifest inventory drift')
    rows: list[dict[str, Any]] = []
    for relative, expected in EXPECTED_FILES.items():
        row = indexed[relative]
        if row['bytes'] != expected['bytes'] or row['sha256'] != expected['sha256']:
            raise BindingError(f'frozen V1 file identity drift: {relative}')
        rows.append(dict(row))
    return rows

def _project_rows(rows: Sequence[Mapping[str, Any]], source_files: Sequence[str]) -> list[dict[str, Any]]:
    indexed = {row['path']: row for row in rows}
    projected: list[dict[str, Any]] = []
    for relative in source_files:
        relative = safe_relative(relative, 'opponent source path')
        source = indexed.get(relative)
        if source is None:
            raise BindingError(f'opponent source path absent from freeze: {relative}')
        target = Path(relative).name if len(source_files) == 1 else relative
        row = dict(source)
        row['path'] = target
        row['source_path'] = relative
        projected.append(row)
    return sorted(projected, key=lambda row: row['path'])

def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise BindingError(f'cannot create {path}: {exc}') from exc

def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise

def _wrapper_source(*, label: str, entry_name: str, expected_files: Mapping[str, Mapping[str, Any]], expected_closure: str, module_origins: Mapping[str, str], attribute_origins: Mapping[str, str], git_head: str) -> str:
    """Return a path-relative wrapper whose bytes identify the bound closure."""
    label = str(label)
    entry_name = safe_relative(entry_name, 'wrapper entry name')
    expected_closure = lower_hex(expected_closure, 64, 'wrapper closure')
    git_head = lower_hex(git_head, 40, 'wrapper git head')
    for path, metadata in expected_files.items():
        safe_relative(path, 'wrapper payload path')
        if type(metadata.get('bytes')) is not int or metadata['bytes'] < 0:
            raise BindingError(f'wrapper payload byte count invalid: {path}')
        lower_hex(metadata.get('sha256'), 64, f'wrapper payload hash {path}')
    for name, path in module_origins.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise BindingError(f'invalid local module name {name!r}')
        safe_relative(path, f'module origin {name}')
    for dotted, path in attribute_origins.items():
        pieces = dotted.split('.')
        if len(pieces) != 2 or any((not piece.isidentifier() for piece in pieces)):
            raise BindingError(f'invalid module attribute origin {dotted!r}')
        safe_relative(path, f'attribute origin {dotted}')
    module_name = f'_sol_pro_bound_{label}_{expected_closure[:16]}'
    files_literal = repr({path: {'bytes': metadata['bytes'], 'sha256': metadata['sha256']} for path, metadata in sorted(expected_files.items())})
    modules_literal = repr(dict(sorted(module_origins.items())))
    attributes_literal = repr(dict(sorted(attribute_origins.items())))
    return f"""# SPDX-License-Identifier: Apache-2.0
# Generated by bind_opponents.py; do not edit.
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path, PurePosixPath
import stat
import sys

_LABEL = {label!r}
_PAYLOAD = Path(__file__).resolve().parent / "payload"
_ENTRY_NAME = {entry_name!r}
_EXPECTED_FILES = {files_literal}
_EXPECTED_CLOSURE = {expected_closure!r}
_EXPECTED_HEAD = {git_head!r}
_MODULE_NAME = {module_name!r}
_MODULE_ORIGINS = {modules_literal}
_ATTRIBUTE_ORIGINS = {attributes_literal}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _safe_relative(value):
    if not isinstance(value, str) or not value or "\\\\" in value or "\\x00" in value:
        raise RuntimeError(f"unsafe payload path: {{value!r}}")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
        or PurePosixPath(*pure.parts).as_posix() != value
    ):
        raise RuntimeError(f"noncanonical payload path: {{value!r}}")
    return value


def _inventory(root):
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"payload root is not a directory: {{root}}")
    rows = {{}}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = _safe_relative(path.relative_to(root).as_posix())
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"non-regular payload member: {{relative}}")
        data = path.read_bytes()
        if relative in rows:
            raise RuntimeError(f"duplicate payload member: {{relative}}")
        rows[relative] = {{"bytes": len(data), "sha256": _sha256(data)}}
    if rows != _EXPECTED_FILES:
        missing = sorted(set(_EXPECTED_FILES) - set(rows))
        extra = sorted(set(rows) - set(_EXPECTED_FILES))
        changed = sorted(
            name for name in set(rows) & set(_EXPECTED_FILES)
            if rows[name] != _EXPECTED_FILES[name]
        )
        raise RuntimeError(
            "bound payload mismatch: "
            f"missing={{missing}}, extra={{extra}}, changed={{changed}}"
        )
    return rows


def _closure(rows):
    digest = hashlib.sha256()
    for relative in sorted(rows):
        row = rows[relative]
        digest.update(relative.encode("utf-8"))
        digest.update(b"\\0")
        digest.update(str(row["bytes"]).encode("ascii"))
        digest.update(b"\\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\\0")
    return digest.hexdigest()


_rows = _inventory(_PAYLOAD)
_actual_closure = _closure(_rows)
if _actual_closure != _EXPECTED_CLOSURE:
    raise RuntimeError(
        f"bound payload closure mismatch: expected {{_EXPECTED_CLOSURE}}, "
        f"got {{_actual_closure}}"
    )

for _name in _MODULE_ORIGINS:
    if _name in sys.modules:
        _loaded = sys.modules[_name]
        raise RuntimeError(
            f"ambient local module collision: {{_name}} from "
            f"{{getattr(_loaded, '__file__', None)!r}}"
        )

_payload_text = str(_PAYLOAD)
while _payload_text in sys.path:
    sys.path.remove(_payload_text)
sys.path.insert(0, _payload_text)

_entry = _PAYLOAD / _ENTRY_NAME
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _entry)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load bound opponent entry: {{_entry}}")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _module
_spec.loader.exec_module(_module)
if Path(getattr(_module, "__file__", "")).resolve() != _entry.resolve():
    raise RuntimeError(f"opponent entry escaped bound payload: {{_module.__file__!r}}")

_verified_origins = {{"entry": _ENTRY_NAME}}
for _name, _relative in _MODULE_ORIGINS.items():
    _loaded = sys.modules.get(_name)
    _actual = getattr(_loaded, "__file__", None)
    _expected = (_PAYLOAD / _relative).resolve()
    if not isinstance(_actual, str) or Path(_actual).resolve() != _expected:
        raise RuntimeError(
            f"local module escaped bound payload: {{_name}} from {{_actual!r}}"
        )
    _verified_origins[_name] = _relative

for _dotted, _relative in _ATTRIBUTE_ORIGINS.items():
    _owner_name, _attribute = _dotted.split(".", 1)
    _owner = sys.modules.get(_owner_name)
    _loaded = getattr(_owner, _attribute, None)
    _actual = getattr(_loaded, "__file__", None)
    _expected = (_PAYLOAD / _relative).resolve()
    if not isinstance(_actual, str) or Path(_actual).resolve() != _expected:
        raise RuntimeError(
            f"module attribute escaped bound payload: {{_dotted}} from {{_actual!r}}"
        )
    _verified_origins[_dotted] = _relative

agent = getattr(_module, "agent", None)
if not callable(agent):
    raise TypeError("bound opponent agent is not callable")

__titan_binding__ = {{
    "label": _LABEL,
    "git_head": _EXPECTED_HEAD,
    "closure_sha256": _EXPECTED_CLOSURE,
    "entry": _ENTRY_NAME,
    "verified_origins": _verified_origins,
}}
__all__ = ["agent"]
"""

def _probe_wrapper(wrapper: Path, label: str) -> dict[str, Any]:
    script = '\nimport importlib.util\nimport json\nfrom pathlib import Path\nimport sys\npath = Path(sys.argv[1]).resolve()\nname = "_sol_pro_probe_" + path.parent.name\nspec = importlib.util.spec_from_file_location(name, path)\nif spec is None or spec.loader is None:\n    raise SystemExit("missing wrapper loader")\nmodule = importlib.util.module_from_spec(spec)\nsys.modules[name] = module\nspec.loader.exec_module(module)\nbinding = getattr(module, "__titan_binding__", None)\nagent = getattr(module, "agent", None)\nif not isinstance(binding, dict) or not callable(agent):\n    raise SystemExit("wrapper did not expose binding and agent")\nprint(json.dumps({\n    "binding": binding,\n    "agent_module": getattr(agent, "__module__", None),\n}, sort_keys=True))\n'
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        process = subprocess.run([sys.executable, '-I', '-c', script, str(wrapper)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='strict', timeout=30, check=False, env=env, cwd=wrapper.parent)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BindingError(f'{label} wrapper probe failed to run: {exc}') from exc
    if process.returncode != 0:
        raise BindingError(f'{label} wrapper probe failed ({process.returncode}): {process.stderr[-2000:]}')
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise BindingError(f'{label} wrapper probe emitted unexpected output')
    value = strict_object_bytes(lines[0].encode('utf-8'), f'{label} wrapper probe')
    binding = value.get('binding')
    if not isinstance(binding, dict) or binding.get('label') != label:
        raise BindingError(f'{label} wrapper probe identity drift')
    return value

def _copy_payload(source_rows: Sequence[Mapping[str, Any]], destination: Path, source_root: Path=V1_ROOT) -> list[dict[str, Any]]:
    destination.mkdir(parents=True, exist_ok=False)
    for row in source_rows:
        target_relative = safe_relative(row['path'], 'payload target')
        source_relative = safe_relative(row['source_path'], 'payload source')
        source = source_root / source_relative
        data = regular_bytes(source, f'source {source_relative}')
        if len(data) != row['bytes'] or sha256(data) != row['sha256']:
            raise BindingError(f'source changed during copy: {source_relative}')
        _write_bytes(destination / target_relative, data)
    return _inventory(destination, 'private opponent payload')

def _not_nested(output_dir: Path, source_root: Path) -> None:
    output = output_dir.resolve()
    source = source_root.resolve()
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise BindingError('opponent output may not be inside frozen source')
    try:
        source.relative_to(output)
    except ValueError:
        pass
    else:
        raise BindingError('frozen source may not be inside opponent output')

def build_binding(output_dir: Path, git_head: str) -> dict[str, Any]:
    git_head = lower_hex(git_head, 40, 'git head')
    output_dir = output_dir.resolve()
    _not_nested(output_dir, V1_ROOT)
    if output_dir.exists():
        raise BindingError(f'opponent output already exists: {output_dir}')
    source_rows = source_inventory(V1_ROOT)
    source_index = {row['path']: row for row in source_rows}
    output_dir.mkdir(parents=True, exist_ok=False)
    opponents: dict[str, dict[str, Any]] = {}
    for label in ('arlene', 'v1'):
        spec = OPPONENT_SPECS[label]
        label_root = output_dir / label
        payload_root = label_root / 'payload'
        projected = _project_rows(source_rows, spec['source_files'])
        payload_rows = _copy_payload(projected, payload_root)
        expected_payload = [{'path': row['path'], 'bytes': row['bytes'], 'sha256': row['sha256'], 'git_blob_sha1': row['git_blob_sha1']} for row in projected]
        if payload_rows != expected_payload:
            raise BindingError(f'{label} private payload changed while copying')
        closure = closure_sha256(payload_rows)
        wrapper_path = label_root / spec['entry_name']
        wrapper_text = _wrapper_source(label=label, entry_name=spec['entry_name'], expected_files={row['path']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in payload_rows}, expected_closure=closure, module_origins=spec['module_origins'], attribute_origins=spec['attribute_origins'], git_head=git_head)
        try:
            compile(wrapper_text, str(wrapper_path), 'exec')
        except SyntaxError as exc:
            raise BindingError(f'generated {label} wrapper does not compile: {exc}') from exc
        _write_bytes(wrapper_path, wrapper_text.encode('utf-8'))
        source_entry_relative = spec['entry_source']
        source_entry = dict(source_index[source_entry_relative])
        source_entry['path'] = 'revenue/kaggriculture/cloud-execution-lab/runtime/variants/v1/' + source_entry_relative
        wrapper_identity = identity(wrapper_path, f'{label} wrapper')
        wrapper_identity['path'] = f"{label}/{spec['entry_name']}"
        payload_record = {'root': f'{label}/payload', 'closure_sha256': closure, 'files': payload_rows}
        sidecar = {'schema_version': 1, 'operation': OPERATION, 'label': label, 'git_head': git_head, 'source_parent_head': PARENT_HEAD, 'source_entry': source_entry, 'source_closure_sha256': closure, 'payload': payload_record, 'wrapper': wrapper_identity}
        sidecar_path = label_root / 'BINDING.json'
        atomic_json(sidecar_path, sidecar)
        sidecar_identity = identity(sidecar_path, f'{label} binding sidecar')
        sidecar_identity['path'] = f'{label}/BINDING.json'
        probe = _probe_wrapper(wrapper_path, label)
        if probe['binding'].get('closure_sha256') != closure:
            raise BindingError(f'{label} wrapper probe closure drift')
        if _inventory(payload_root, f'{label} private opponent payload') != payload_rows:
            raise BindingError(f'{label} payload changed during import probe')
        if identity(wrapper_path, f'{label} wrapper')['sha256'] != wrapper_identity['sha256']:
            raise BindingError(f'{label} wrapper changed during import probe')
        opponents[label] = {'entry_name': spec['entry_name'], 'source_entry': source_entry, 'source_closure_sha256': closure, 'payload': payload_record, 'wrapper': wrapper_identity, 'sidecar': sidecar_identity, 'probe': probe}
    wrappers = {row['wrapper']['sha256'] for row in opponents.values()}
    if len(wrappers) != len(opponents):
        raise BindingError('opponent wrapper identities alias')
    return {'schema_version': 1, 'operation': OPERATION, 'git_head': git_head, 'source_parent_head': PARENT_HEAD, 'freeze': {'path': 'revenue/kaggriculture/cloud-execution-lab/runtime/variants/v1/FREEZE.json', 'bytes': EXPECTED_FREEZE_BYTES, 'sha256': EXPECTED_FREEZE_SHA256, 'runtime_files': len(EXPECTED_FILES), 'source_closure_sha256': closure_sha256(source_rows)}, 'binder': identity(Path(__file__).resolve(), 'opponent binder'), 'opponents': opponents}

def _same_inode(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except OSError as exc:
        raise BindingError(f'cannot compare file identity: {left}, {right}: {exc}') from exc

def _validate_binding_shape(binding: Mapping[str, Any], git_head: str) -> None:
    if binding.get('schema_version') != 1 or binding.get('operation') != OPERATION:
        raise BindingError('opponent binding receipt identity drift')
    if binding.get('git_head') != git_head or binding.get('source_parent_head') != PARENT_HEAD:
        raise BindingError('opponent binding head lineage drift')
    opponents = binding.get('opponents')
    if not isinstance(opponents, Mapping) or set(opponents) != set(OPPONENT_SPECS):
        raise BindingError('opponent binding bank drift')
    freeze = binding.get('freeze')
    if not isinstance(freeze, Mapping):
        raise BindingError('opponent binding freeze receipt missing')
    if freeze.get('bytes') != EXPECTED_FREEZE_BYTES or freeze.get('sha256') != EXPECTED_FREEZE_SHA256 or freeze.get('runtime_files') != len(EXPECTED_FILES):
        raise BindingError('opponent binding freeze identity drift')

def verify_binding(output_dir: Path, binding: Mapping[str, Any], git_head: str) -> dict[str, Any]:
    git_head = lower_hex(git_head, 40, 'git head')
    _validate_binding_shape(binding, git_head)
    output_dir = output_dir.resolve()
    _not_nested(output_dir, V1_ROOT)
    source_rows = source_inventory(V1_ROOT)
    source_index = {row['path']: row for row in source_rows}
    verified: dict[str, Any] = {}
    binder_now = identity(Path(__file__).resolve(), 'opponent binder')
    if binding.get('binder') != binder_now:
        raise BindingError('opponent binder bytes changed after build')
    for label in ('arlene', 'v1'):
        spec = OPPONENT_SPECS[label]
        record = binding['opponents'][label]
        if not isinstance(record, Mapping):
            raise BindingError(f'{label} binding row is invalid')
        projected = _project_rows(source_rows, spec['source_files'])
        expected_payload = [{'path': row['path'], 'bytes': row['bytes'], 'sha256': row['sha256'], 'git_blob_sha1': row['git_blob_sha1']} for row in projected]
        expected_closure = closure_sha256(expected_payload)
        if record.get('entry_name') != spec['entry_name'] or record.get('source_closure_sha256') != expected_closure:
            raise BindingError(f'{label} source closure receipt drift')
        expected_source_entry = dict(source_index[spec['entry_source']])
        expected_source_entry['path'] = 'revenue/kaggriculture/cloud-execution-lab/runtime/variants/v1/' + spec['entry_source']
        if record.get('source_entry') != expected_source_entry:
            raise BindingError(f'{label} source entry receipt drift')
        payload_root = output_dir / label / 'payload'
        payload_rows = _inventory(payload_root, f'{label} private opponent payload')
        payload = record.get('payload')
        if not isinstance(payload, Mapping):
            raise BindingError(f'{label} payload receipt missing')
        if payload.get('root') != f'{label}/payload' or payload.get('files') != expected_payload or payload_rows != expected_payload or (payload.get('closure_sha256') != expected_closure) or (closure_sha256(payload_rows) != expected_closure):
            raise BindingError(f'{label} private payload receipt drift')
        for row in projected:
            source = V1_ROOT / row['source_path']
            copy = payload_root / row['path']
            if _same_inode(source, copy):
                raise BindingError(f"{label} payload aliases source: {row['path']}")
            info = copy.lstat()
            if info.st_nlink != 1:
                raise BindingError(f"{label} payload has shared inode: {row['path']}")
        wrapper_path = output_dir / label / spec['entry_name']
        wrapper_now = identity(wrapper_path, f'{label} wrapper')
        wrapper_now['path'] = f"{label}/{spec['entry_name']}"
        if record.get('wrapper') != wrapper_now:
            raise BindingError(f'{label} wrapper receipt drift')
        if wrapper_path.lstat().st_nlink != 1:
            raise BindingError(f'{label} wrapper has shared inode')
        for row in projected:
            if _same_inode(wrapper_path, payload_root / row['path']):
                raise BindingError(f'{label} wrapper aliases payload')
        sidecar_path = output_dir / label / 'BINDING.json'
        sidecar_now = identity(sidecar_path, f'{label} binding sidecar')
        sidecar_now['path'] = f'{label}/BINDING.json'
        if record.get('sidecar') != sidecar_now:
            raise BindingError(f'{label} sidecar receipt drift')
        sidecar = strict_object(sidecar_path, f'{label} binding sidecar')
        if sidecar.get('schema_version') != 1 or sidecar.get('operation') != OPERATION or sidecar.get('label') != label or (sidecar.get('git_head') != git_head) or (sidecar.get('source_parent_head') != PARENT_HEAD) or (sidecar.get('source_entry') != expected_source_entry) or (sidecar.get('source_closure_sha256') != expected_closure) or (sidecar.get('payload') != payload) or (sidecar.get('wrapper') != wrapper_now):
            raise BindingError(f'{label} sidecar semantics drift')
        probe = _probe_wrapper(wrapper_path, label)
        if probe != record.get('probe'):
            raise BindingError(f'{label} post-panel probe changed')
        if probe['binding'].get('closure_sha256') != expected_closure:
            raise BindingError(f'{label} post-panel probe closure drift')
        verified[label] = {'source_entry': expected_source_entry, 'source_closure_sha256': expected_closure, 'payload_closure_sha256': expected_closure, 'wrapper': wrapper_now, 'sidecar': sidecar_now, 'probe': probe}
    wrappers = {row['wrapper']['sha256'] for row in verified.values()}
    if len(wrappers) != len(verified):
        raise BindingError('verified opponent wrapper identities alias')
    return {'schema_version': 1, 'operation': VERIFY_OPERATION, 'git_head': git_head, 'source_parent_head': PARENT_HEAD, 'binding_object_sha256': object_sha256(binding), 'binder': binder_now, 'opponents': verified, 'verified': True}

def _summary(value: Mapping[str, Any]) -> dict[str, Any]:
    return {'operation': value.get('operation'), 'git_head': value.get('git_head'), 'opponents': {label: {'closure_sha256': row.get('source_closure_sha256', row.get('payload_closure_sha256')), 'wrapper_sha256': row.get('wrapper', {}).get('sha256')} for label, row in value.get('opponents', {}).items() if isinstance(row, Mapping)}}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    build = subparsers.add_parser('build')
    build.add_argument('--output-dir', type=Path, required=True)
    build.add_argument('--receipt', type=Path, required=True)
    build.add_argument('--head', required=True)
    verify = subparsers.add_parser('verify')
    verify.add_argument('--output-dir', type=Path, required=True)
    verify.add_argument('--binding', type=Path, required=True)
    verify.add_argument('--output', type=Path, required=True)
    verify.add_argument('--head', required=True)
    args = parser.parse_args()
    if args.command == 'build':
        receipt = build_binding(args.output_dir, args.head)
        atomic_json(args.receipt, receipt)
        print(json.dumps(_summary(receipt), sort_keys=True))
        return 0
    binding = strict_object(args.binding, 'opponent binding receipt')
    receipt = verify_binding(args.output_dir, binding, args.head)
    atomic_json(args.output, receipt)
    print(json.dumps(_summary(receipt), sort_keys=True))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
