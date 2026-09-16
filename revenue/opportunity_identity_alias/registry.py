"""Repository-carried append-only opportunity alias registry."""
from __future__ import annotations

import stat
from pathlib import Path
from typing import Any

from .aliases import alias_key, machine_key, normalize_aliases
from .strict import (
    MAX_JSON_BYTES, MAX_SAFE_INTEGER, OBSERVATION_SCHEMA, REGISTRY_SCHEMA, SHA_RE,
    IdentityAliasError, exact_keys, sha256_json, strict_json_loads,
)

CURRENT_REGISTRY_PATH = Path(__file__).with_name("registry.json")


def compile_registry(raw: Any) -> dict[str, Any]:
    value = exact_keys(raw, {"schema", "generation", "prior_registry_sha256", "entries"}, "registry")
    if value["schema"] != REGISTRY_SCHEMA:
        raise IdentityAliasError("registry: unsupported schema")
    generation = value["generation"]
    if type(generation) is not int or type(generation) is bool or not (1 <= generation <= MAX_SAFE_INTEGER):
        raise IdentityAliasError("registry.generation: positive integer required")
    prior = value["prior_registry_sha256"]
    if generation == 1:
        if prior is not None:
            raise IdentityAliasError("registry.prior_registry_sha256: generation 1 requires null")
    elif type(prior) is not str or SHA_RE.fullmatch(prior) is None:
        raise IdentityAliasError("registry.prior_registry_sha256: lowercase SHA-256 required")
    entries_raw = value["entries"]
    if type(entries_raw) is not list or len(entries_raw) > 4096:
        raise IdentityAliasError("registry.entries: bounded array required")

    entries: list[dict[str, Any]] = []
    canonical_seen: set[str] = set()
    alias_owner: dict[tuple[str, str, str], str] = {}
    for raw_entry in entries_raw:
        entry = exact_keys(
            raw_entry, {"canonical_opportunity_key", "buyer_organization_key", "aliases"}, "registry entry"
        )
        canonical = machine_key(entry["canonical_opportunity_key"], "canonical_opportunity_key")
        buyer = machine_key(entry["buyer_organization_key"], "buyer_organization_key")
        if canonical in canonical_seen:
            raise IdentityAliasError("registry: duplicate canonical_opportunity_key")
        canonical_seen.add(canonical)
        aliases = normalize_aliases(entry["aliases"], require_nonempty=True)
        for alias in aliases:
            seam = (buyer, alias["type"], alias["value"])
            previous = alias_owner.get(seam)
            if previous is not None and previous != canonical:
                raise IdentityAliasError("registry: normalized alias assigned to multiple opportunities within buyer")
            alias_owner[seam] = canonical
        entries.append({
            "canonical_opportunity_key": canonical,
            "buyer_organization_key": buyer,
            "aliases": aliases,
        })
    entries.sort(key=lambda item: (item["buyer_organization_key"], item["canonical_opportunity_key"]))
    return {
        "schema": REGISTRY_SCHEMA,
        "generation": generation,
        "prior_registry_sha256": prior,
        "entries": entries,
    }


def registry_sha256(raw: Any) -> str:
    return sha256_json(compile_registry(raw))


def compile_observation(raw: Any) -> dict[str, Any]:
    value = exact_keys(raw, {"schema", "buyer_organization_key", "aliases"}, "observation")
    if value["schema"] != OBSERVATION_SCHEMA:
        raise IdentityAliasError("observation: unsupported schema")
    return {
        "schema": OBSERVATION_SCHEMA,
        "buyer_organization_key": machine_key(value["buyer_organization_key"], "buyer_organization_key"),
        "aliases": normalize_aliases(value["aliases"], require_nonempty=True),
    }


def alias_set_sha256(observation: Any) -> str:
    return sha256_json(compile_observation(observation)["aliases"])


def validate_transition(previous: Any, candidate: Any) -> dict[str, Any]:
    old = compile_registry(previous)
    new = compile_registry(candidate)
    if new["generation"] != old["generation"] + 1:
        raise IdentityAliasError("transition: generation must advance by exactly one")
    if new["prior_registry_sha256"] != sha256_json(old):
        raise IdentityAliasError("transition: prior_registry_sha256 mismatch")
    old_by_key = {e["canonical_opportunity_key"]: e for e in old["entries"]}
    new_by_key = {e["canonical_opportunity_key"]: e for e in new["entries"]}
    if not set(old_by_key).issubset(new_by_key):
        raise IdentityAliasError("transition: canonical opportunity removal forbidden")
    for key, old_entry in old_by_key.items():
        new_entry = new_by_key[key]
        if new_entry["buyer_organization_key"] != old_entry["buyer_organization_key"]:
            raise IdentityAliasError("transition: buyer reassignment forbidden")
        old_aliases = {alias_key(a) for a in old_entry["aliases"]}
        new_aliases = {alias_key(a) for a in new_entry["aliases"]}
        if not old_aliases.issubset(new_aliases):
            raise IdentityAliasError("transition: alias removal or reassignment forbidden")
    return new


def read_current_registry() -> dict[str, Any]:
    try:
        st = CURRENT_REGISTRY_PATH.lstat()
    except OSError as exc:
        raise IdentityAliasError("current registry unavailable") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise IdentityAliasError("current registry must be an ordinary non-symlink file")
    if st.st_size > MAX_JSON_BYTES:
        raise IdentityAliasError("current registry exceeds size limit")
    try:
        raw = CURRENT_REGISTRY_PATH.read_bytes()
    except OSError as exc:
        raise IdentityAliasError("current registry unavailable") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise IdentityAliasError("current registry exceeds size limit")
    try:
        return compile_registry(strict_json_loads(raw.decode("utf-8")))
    except UnicodeDecodeError as exc:
        raise IdentityAliasError("current registry is not UTF-8") from exc
