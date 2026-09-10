# SPDX-License-Identifier: Apache-2.0
"""Generate closure-bound canonical-main entrypoints and an execution receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import materialize

OPERATION = "titan-v3-all-shed-priority-current-binding-sol-orbit-01"
EXPECTED_SEEDS = (
    539131249,
    1834999074,
    2609097301,
    2609097302,
    2609097303,
    2609097304,
    2611092201,
    2611092207,
)
EXPECTED_AGENT_RNG_SEED = 20260909
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0,
}
EXPECTED_ENGINE_FILES = ("kaggriculture.py", "kaggriculture.json", "utils.py")
EXPECTED_OPPONENTS = ("arlene", "v1")
EXPECTED_ENTRY = "main.py"
EXPECTED_ENTRY_SHA256 = materialize.EXPECTED_ENTRY_SHA256


class BindingError(ValueError):
    """The execution package is incomplete, mutable, or not source-bound."""


def strict_object(path: Path) -> dict[str, Any]:
    def reject_pairs(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise BindingError(f"duplicate JSON key {key!r} in {path}")
            output[key] = value
        return output

    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                BindingError(f"non-finite JSON token {token} in {path}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise BindingError(f"{path} must contain one JSON object")
    return value


def _hex(value: Any, label: str, length: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise BindingError(f"{label} is not lowercase {length}-hex")
    return value


def _file_sha256(path: Path, label: str) -> str:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise BindingError(f"{label} is not one regular file: {path}")
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BindingError(f"cannot read {label} {path}: {exc}") from exc


def _fingerprint_spec(spec: str, label: str) -> dict[str, str]:
    path_text, separator, callable_name = spec.partition("::")
    if separator and callable_name != "agent":
        raise BindingError(f"{label} callable must be agent")
    path = Path(path_text).resolve()
    return {
        "entry": path.name,
        "callable": callable_name if separator else "agent",
        "sha256": _file_sha256(path, label),
    }


def _parse_opponents(values: list[str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for value in values:
        name, separator, spec = value.partition("=")
        if not separator or not name or not spec or name in output:
            raise BindingError(f"invalid or duplicate opponent: {value!r}")
        output[name] = spec
    if tuple(sorted(output)) != tuple(sorted(EXPECTED_OPPONENTS)):
        raise BindingError(f"opponents must be exactly {list(EXPECTED_OPPONENTS)!r}")
    return output


def _wrapper_source(
    *,
    label: str,
    root: Path,
    expected_closure: str,
    git_head: str,
) -> str:
    module_name = f"_sol_orbit_current_{label}_{expected_closure[:12]}"
    return f"""# SPDX-License-Identifier: Apache-2.0
# Generated closure-bound current-TITAN entrypoint for the {label} arm.
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys

_ROOT = Path({str(root)!r})
_EXPECTED_CLOSURE = {expected_closure!r}
_EXPECTED_ENTRY_SHA256 = {EXPECTED_ENTRY_SHA256!r}
_EXPECTED_HEAD = {git_head!r}
_MODULE_NAME = {module_name!r}


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _inside(root, path):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _origin(module):
    value = getattr(module, "__file__", None)
    if not value:
        return None
    try:
        return Path(value).resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _closure(root):
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError(f"bound root is not a regular directory: {{root}}")
    records = []
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError(f"non-regular bound member: {{relative}}")
        data = path.read_bytes()
        records.append((relative, len(data), _sha256(data)))
    if not records:
        raise RuntimeError("bound root inventory is empty")
    digest = hashlib.sha256()
    for relative, length, value in records:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\\0")
        digest.update(str(length).encode("ascii"))
        digest.update(b"\\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\\0")
    return digest.hexdigest()


_actual_closure = _closure(_ROOT)
if _actual_closure != _EXPECTED_CLOSURE:
    raise RuntimeError(
        f"bound closure mismatch: expected {{_EXPECTED_CLOSURE}}, got {{_actual_closure}}"
    )

_entry = _ROOT / {EXPECTED_ENTRY!r}
_actual_entry = _sha256(_entry.read_bytes())
if _actual_entry != _EXPECTED_ENTRY_SHA256:
    raise RuntimeError(
        f"bound main entry mismatch: expected {{_EXPECTED_ENTRY_SHA256}}, got {{_actual_entry}}"
    )

_manifest = json.loads((_ROOT / "SOURCE.json").read_text(encoding="utf-8"))
_runtime = _manifest.get("runtime")
if not isinstance(_runtime, dict):
    raise RuntimeError("bound SOURCE.json runtime is invalid")
_RUNTIME_NAMES = set()
for _name in _runtime:
    _path = Path(_name)
    if len(_path.parts) == 1 and _path.suffix == ".py" and _path.stem != "main":
        _RUNTIME_NAMES.add(_path.stem)
    elif len(_path.parts) > 1 and _path.parts[0] == "reference":
        _RUNTIME_NAMES.add("reference")


def _assert_runtime_origins():
    for name in sorted(_RUNTIME_NAMES):
        module = sys.modules.get(name)
        if module is None:
            continue
        origin = _origin(module)
        if origin is None or not _inside(_ROOT, origin):
            raise RuntimeError(
                f"runtime module escaped bound closure: {{name}} from {{origin}}"
            )


_assert_runtime_origins()
root_text = str(_ROOT)
while root_text in sys.path:
    sys.path.remove(root_text)
sys.path.insert(0, root_text)
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _entry)
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot import bound current entry: {{_entry}}")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _module
_spec.loader.exec_module(_module)
_agent = getattr(_module, "agent", None)
if not callable(_agent):
    raise TypeError("bound current main agent is not callable")


def agent(observation, configuration=None):
    _assert_runtime_origins()
    result = _agent(observation, configuration)
    _assert_runtime_origins()
    return result


__all__ = ["agent"]
"""


def build_binding(
    *,
    control_root: Path,
    candidate_root: Path,
    materialization_receipt: Mapping[str, Any],
    engine_dir: Path,
    loader: Path,
    evaluator: Path,
    opponents: Mapping[str, str],
    output_dir: Path,
    git_head: str,
) -> dict[str, Any]:
    git_head = _hex(git_head, "git head", 40)
    control_root = Path(control_root).resolve()
    candidate_root = Path(candidate_root).resolve()
    engine_dir = Path(engine_dir).resolve()
    loader = Path(loader).resolve()
    evaluator = Path(evaluator).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise BindingError(f"wrapper output already exists: {output_dir}")
    if tuple(sorted(opponents)) != tuple(sorted(EXPECTED_OPPONENTS)):
        raise BindingError("opponent bank mismatch")

    receipt = materialization_receipt
    source = receipt.get("source")
    ablation = receipt.get("ablation")
    archive = receipt.get("archive")
    if (
        receipt.get("schema_version") != 1
        or receipt.get("operation") != materialize.OPERATION
        or receipt.get("experiment") != materialize.EXPERIMENT
        or not isinstance(source, Mapping)
        or not isinstance(ablation, Mapping)
        or not isinstance(archive, Mapping)
        or ablation.get("changed_files") != ["scheduler.py"]
    ):
        raise BindingError("materialization receipt is incomplete or wrong experiment")
    if archive.get("sha256") != materialize.EXPECTED_ARCHIVE_SHA256:
        raise BindingError("materialization archive identity drift")
    expected_control = _hex(source.get("closure_sha256"), "control closure", 64)
    expected_candidate = _hex(
        ablation.get("closure_sha256"), "candidate closure", 64
    )
    if expected_control == expected_candidate:
        raise BindingError("control and candidate closures are equal")

    actual_control = materialize.closure_sha256(materialize.inventory(control_root))
    actual_candidate = materialize.closure_sha256(
        materialize.inventory(candidate_root)
    )
    if actual_control != expected_control:
        raise BindingError("control root closure is detached from receipt")
    if actual_candidate != expected_candidate:
        raise BindingError("candidate root closure is detached from receipt")

    for label, root in (("control", control_root), ("candidate", candidate_root)):
        actual_entry = _file_sha256(root / EXPECTED_ENTRY, f"{label} main entry")
        if actual_entry != EXPECTED_ENTRY_SHA256:
            raise BindingError(
                f"{label} main entry drift: expected {EXPECTED_ENTRY_SHA256}, "
                f"got {actual_entry}"
            )

    output_dir.mkdir(parents=True)
    arms: dict[str, dict[str, Any]] = {}
    for label, root, closure in (
        ("control", control_root, actual_control),
        ("candidate", candidate_root, actual_candidate),
    ):
        wrapper = output_dir / f"{label}_bound.py"
        source_text = _wrapper_source(
            label=label,
            root=root,
            expected_closure=closure,
            git_head=git_head,
        )
        try:
            compile(source_text, str(wrapper), "exec")
        except SyntaxError as exc:
            raise BindingError(f"generated {label} wrapper is invalid: {exc}") from exc
        materialize.atomic_write(wrapper, source_text.encode("utf-8"))
        arms[label] = {
            "closure_sha256": closure,
            "entry_sha256": EXPECTED_ENTRY_SHA256,
            "entrypoint": materialize.EXPECTED_ENTRYPOINT,
            "wrapper": {
                "entry": wrapper.name,
                "callable": "agent",
                "sha256": _file_sha256(wrapper, f"{label} wrapper"),
            },
        }
    if arms["control"]["wrapper"]["sha256"] == arms["candidate"]["wrapper"]["sha256"]:
        raise BindingError("control and candidate wrappers have equal identities")

    engine_sha256 = {
        name: _file_sha256(engine_dir / name, f"engine {name}")
        for name in EXPECTED_ENGINE_FILES
    }
    opponent_fingerprints = {
        name: _fingerprint_spec(opponents[name], f"opponent {name}")
        for name in EXPECTED_OPPONENTS
    }
    return {
        "schema_version": 1,
        "operation": OPERATION,
        "experiment": materialize.EXPERIMENT,
        "git_head": git_head,
        "arms": arms,
        "engine_sha256": engine_sha256,
        "loader_sha256": _file_sha256(loader, "loader"),
        "evaluator_sha256": _file_sha256(evaluator, "evaluator"),
        "opponents": opponent_fingerprints,
        "seeds": list(EXPECTED_SEEDS),
        "agent_rng_seed": EXPECTED_AGENT_RNG_SEED,
        "limits": dict(EXPECTED_LIMITS),
        "python": sys.version,
        "platform": sys.platform,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--materialization", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--opponent", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()

    receipt = build_binding(
        control_root=args.control_root,
        candidate_root=args.candidate_root,
        materialization_receipt=strict_object(args.materialization),
        engine_dir=args.engine_dir,
        loader=args.loader,
        evaluator=args.evaluator,
        opponents=_parse_opponents(args.opponent),
        output_dir=args.output_dir,
        git_head=args.head,
    )
    materialize.atomic_write(
        args.receipt,
        (
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "git_head": receipt["git_head"],
                "control_closure": receipt["arms"]["control"]["closure_sha256"],
                "candidate_closure": receipt["arms"]["candidate"]["closure_sha256"],
                "control_wrapper": receipt["arms"]["control"]["wrapper"]["sha256"],
                "candidate_wrapper": receipt["arms"]["candidate"]["wrapper"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
