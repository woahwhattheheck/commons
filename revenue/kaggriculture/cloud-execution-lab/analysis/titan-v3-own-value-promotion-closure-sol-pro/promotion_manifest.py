# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from promotion_core import *

CLOSURE_KEYS = {
    "schema_version",
    "entry",
    "members",
    "modules",
    "closure_sha256",
}


def _closure_payload(
    entry: str,
    members: list[dict[str, Any]],
    modules: dict[str, dict[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": CLOSURE_SCHEMA,
        "entry": entry,
        "members": members,
        "modules": modules,
    }


def build_closure_manifest(
    root: Path,
    *,
    entry: str,
    module_origins: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise PromotionClosureError("closure root must be a real directory")
    root = root.resolve(strict=True)
    entry = canonical_name(entry, "closure entry")
    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    for directory, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        for dirname in list(dirnames):
            child = directory_path / dirname
            if child.is_symlink():
                raise PromotionClosureError(f"closure directory is symlinked: {child}")
        for filename in filenames:
            path = directory_path / filename
            if path.is_symlink():
                raise PromotionClosureError(f"closure member is symlinked: {path}")
            mode = path.stat().st_mode
            if not stat.S_ISREG(mode):
                raise PromotionClosureError(f"closure member is not regular: {path}")
            relative = canonical_name(path.relative_to(root).as_posix(), "closure member")
            if relative in seen:
                raise PromotionClosureError(f"duplicate closure member: {relative}")
            seen.add(relative)
            data = path.read_bytes()
            members.append(
                {
                    "path": relative,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "git_blob_sha1": hashlib.sha1(
                        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
                    ).hexdigest(),
                }
            )
    members.sort(key=lambda row: row["path"])
    if entry not in {row["path"] for row in members}:
        raise PromotionClosureError(f"closure entry is absent: {entry}")

    modules: dict[str, dict[str, str]] = {}
    member_by_path = {row["path"]: row for row in members}
    for module, raw_path in sorted((module_origins or {}).items()):
        module = nonempty_string(module, "module name")
        relative = canonical_name(raw_path, f"module origin {module}")
        if relative not in member_by_path:
            raise PromotionClosureError(
                f"module {module!r} resolves outside closure members: {relative}"
            )
        modules[module] = {
            "path": relative,
            "sha256": member_by_path[relative]["sha256"],
        }
    payload = _closure_payload(entry, members, modules)
    return {**payload, "closure_sha256": json_sha256(payload)}


def validate_closure_receipt(manifest: Mapping[str, Any], label: str = "closure manifest") -> dict[str, Any]:
    """Validate a retained closure object without trusting its declared digest."""
    if not isinstance(manifest, Mapping):
        raise PromotionClosureError(f"{label} must be an object")
    require_keys(manifest, CLOSURE_KEYS, label)
    if manifest["schema_version"] != CLOSURE_SCHEMA:
        raise PromotionClosureError(f"unsupported {label} schema")
    entry = canonical_name(manifest["entry"], f"{label} entry")

    raw_members = manifest["members"]
    if not isinstance(raw_members, list) or not raw_members:
        raise PromotionClosureError(f"{label} members must be a nonempty list")
    members: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, raw in enumerate(raw_members):
        if not isinstance(raw, Mapping):
            raise PromotionClosureError(f"{label} member {index} must be an object")
        require_keys(raw, {"path", "bytes", "sha256", "git_blob_sha1"}, f"{label} member {index}")
        path = canonical_name(raw["path"], f"{label} member path")
        if path in seen_paths:
            raise PromotionClosureError(f"{label} duplicates member {path!r}")
        seen_paths.add(path)
        members.append(
            {
                "path": path,
                "bytes": true_int(raw["bytes"], f"{label} member bytes"),
                "sha256": sha64(raw["sha256"], f"{label} member SHA-256"),
                "git_blob_sha1": sha40(raw["git_blob_sha1"], f"{label} member Git blob"),
            }
        )
    if members != sorted(members, key=lambda row: row["path"]):
        raise PromotionClosureError(f"{label} members are not canonically sorted")
    member_by_path = {row["path"]: row for row in members}
    if entry not in member_by_path:
        raise PromotionClosureError(f"{label} entry is absent from members")

    raw_modules = manifest["modules"]
    if not isinstance(raw_modules, Mapping):
        raise PromotionClosureError(f"{label} modules must be an object")
    modules: dict[str, dict[str, str]] = {}
    for module, record in sorted(raw_modules.items()):
        module = nonempty_string(module, f"{label} module name")
        if not isinstance(record, Mapping):
            raise PromotionClosureError(f"{label} module record must be an object")
        require_keys(record, {"path", "sha256"}, f"{label} module {module}")
        path = canonical_name(record["path"], f"{label} module origin {module}")
        if path not in member_by_path:
            raise PromotionClosureError(f"{label} module {module!r} is outside members")
        digest_value = sha64(record["sha256"], f"{label} module SHA-256 {module}")
        if digest_value != member_by_path[path]["sha256"]:
            raise PromotionClosureError(f"{label} module {module!r} digest is detached")
        modules[module] = {"path": path, "sha256": digest_value}

    payload = _closure_payload(entry, members, modules)
    supplied = sha64(manifest["closure_sha256"], f"{label} closure SHA-256")
    computed = json_sha256(payload)
    if supplied != computed:
        raise PromotionClosureError(f"{label} closure digest is detached")
    return {**payload, "closure_sha256": supplied}


def validate_closure_manifest(root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    retained = validate_closure_receipt(manifest)
    origins = {module: record["path"] for module, record in retained["modules"].items()}
    rebuilt = build_closure_manifest(root, entry=retained["entry"], module_origins=origins)
    if retained != rebuilt:
        raise PromotionClosureError("closure manifest differs from live root")
    return rebuilt


