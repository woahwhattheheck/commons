#!/usr/bin/env python3
"""Fail closed when a retired product reappears on an active Commons surface."""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

SCHEMA = "commons.product-lifecycle.v1"
STATES = frozenset({"ACTIVE", "RETIRING", "RETIRED"})
ACTIVE_STATIC_PATHS = (
    Path("host/payment_capability.py"),
    Path("revenue/outcome_commerce/catalog.json"),
)
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
PRODUCT_KEYS = frozenset(
    {
        "id",
        "state",
        "checkout_urls",
        "catalog_sources",
        "effective_at",
        "provenance",
        "note",
    }
)


class LifecycleError(ValueError):
    """The lifecycle registry or one of its identities is invalid."""


@dataclass(frozen=True)
class Product:
    id: str
    state: str
    checkout_urls: tuple[str, ...]
    catalog_sources: tuple[str, ...]
    effective_at: str | None
    provenance: str | None
    note: str | None


@dataclass(frozen=True)
class Violation:
    product_id: str
    path: str
    kind: str
    identity: str


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise LifecycleError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json_bytes(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise LifecycleError("registry must be UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=lambda _raw: (_ for _ in ()).throw(
                LifecycleError("floating-point values are forbidden")
            ),
            parse_constant=lambda raw_value: (_ for _ in ()).throw(
                LifecycleError(f"non-finite JSON value forbidden: {raw_value}")
            ),
        )
    except LifecycleError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LifecycleError(f"invalid registry JSON: {exc}") from exc


def _plain_str(value: Any, field: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if type(value) is not str or not value.strip():
        raise LifecycleError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise LifecycleError(f"{field} must not have surrounding whitespace")
    return value


def canonical_checkout_identity(value: str) -> str:
    raw = _plain_str(value, "checkout URL")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise LifecycleError(f"invalid checkout URL: {raw}") from exc
    if parsed.scheme.lower() != "https":
        raise LifecycleError(f"checkout URL must use https: {raw}")
    if parsed.username is not None or parsed.password is not None:
        raise LifecycleError(f"checkout URL must not contain credentials: {raw}")
    if port not in (None, 443):
        raise LifecycleError(f"checkout URL must not use a non-default port: {raw}")
    if parsed.query or parsed.fragment:
        raise LifecycleError(f"checkout URL must not contain query/fragment: {raw}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise LifecycleError(f"checkout URL missing host: {raw}")
    path = unquote(parsed.path)
    if not path or path == "/":
        raise LifecycleError(f"checkout URL missing checkout path: {raw}")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
        raise LifecycleError(f"checkout URL contains control characters: {raw}")
    while len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return f"https://{host}{path}"


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if type(value) is not list:
        raise LifecycleError(f"{field} must be an array")
    out: list[str] = []
    for index, item in enumerate(value):
        parsed = _plain_str(item, f"{field}[{index}]")
        if not isinstance(parsed, str):
            raise LifecycleError(f"{field}[{index}] must be a string")
        out.append(parsed)
    return tuple(out)


def validate_registry(doc: Any) -> tuple[Product, ...]:
    if type(doc) is not dict:
        raise LifecycleError("registry root must be an object")
    if set(doc) != {"schema", "products"}:
        raise LifecycleError("registry root keys must be exactly schema, products")
    if doc["schema"] != SCHEMA:
        raise LifecycleError(f"unsupported lifecycle schema: {doc['schema']!r}")
    if type(doc["products"]) is not list:
        raise LifecycleError("products must be an array")

    products: list[Product] = []
    ids: set[str] = set()
    checkout_owners: dict[str, str] = {}

    for index, raw_product in enumerate(doc["products"]):
        if type(raw_product) is not dict:
            raise LifecycleError(f"products[{index}] must be an object")
        unknown = set(raw_product) - PRODUCT_KEYS
        required = {"id", "state", "checkout_urls", "catalog_sources"}
        missing = required - set(raw_product)
        if unknown:
            raise LifecycleError(
                f"products[{index}] has unknown keys: {', '.join(sorted(unknown))}"
            )
        if missing:
            raise LifecycleError(
                f"products[{index}] missing keys: {', '.join(sorted(missing))}"
            )
        product_id = _plain_str(raw_product["id"], f"products[{index}].id")
        state = _plain_str(raw_product["state"], f"products[{index}].state")
        if not isinstance(product_id, str) or not isinstance(state, str):
            raise LifecycleError(f"products[{index}] id/state must be strings")
        if product_id in ids:
            raise LifecycleError(f"duplicate product id: {product_id}")
        ids.add(product_id)
        if state not in STATES:
            raise LifecycleError(f"invalid lifecycle state for {product_id}: {state}")

        checkout_urls = _string_list(
            raw_product["checkout_urls"], f"products[{index}].checkout_urls"
        )
        catalog_sources = _string_list(
            raw_product["catalog_sources"], f"products[{index}].catalog_sources"
        )
        canonical_urls: list[str] = []
        local_urls: set[str] = set()
        for url in checkout_urls:
            canonical = canonical_checkout_identity(url)
            if canonical in local_urls:
                raise LifecycleError(
                    f"duplicate checkout identity within {product_id}: {canonical}"
                )
            local_urls.add(canonical)
            prior = checkout_owners.get(canonical)
            if prior is not None:
                raise LifecycleError(
                    f"checkout identity shared by {prior} and {product_id}: {canonical}"
                )
            checkout_owners[canonical] = product_id
            canonical_urls.append(canonical)

        seen_sources: set[str] = set()
        for source in catalog_sources:
            if source.startswith("/") or "\\" in source or ".." in Path(source).parts:
                raise LifecycleError(
                    f"catalog source must be a normalized repository-relative path: {source}"
                )
            if source in seen_sources:
                raise LifecycleError(
                    f"duplicate catalog source within {product_id}: {source}"
                )
            seen_sources.add(source)

        effective_at = _plain_str(
            raw_product.get("effective_at"),
            f"products[{index}].effective_at",
            allow_none=True,
        )
        provenance = _plain_str(
            raw_product.get("provenance"),
            f"products[{index}].provenance",
            allow_none=True,
        )
        note = _plain_str(
            raw_product.get("note"),
            f"products[{index}].note",
            allow_none=True,
        )
        if state == "RETIRED" and effective_at is None:
            raise LifecycleError(f"RETIRED product {product_id} requires effective_at")

        products.append(
            Product(
                id=product_id,
                state=state,
                checkout_urls=tuple(canonical_urls),
                catalog_sources=catalog_sources,
                effective_at=effective_at,
                provenance=provenance,
                note=note,
            )
        )
    return tuple(products)


def load_registry(path: Path) -> tuple[Product, ...]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LifecycleError(f"cannot read lifecycle registry: {path}") from exc
    return validate_registry(load_json_bytes(raw))


def active_surface_paths(repo_root: Path) -> tuple[Path, ...]:
    paths: set[Path] = set()
    for candidate in repo_root.glob("*.html"):
        if candidate.is_file():
            paths.add(candidate)
    for rel in ACTIVE_STATIC_PATHS:
        candidate = repo_root / rel
        if candidate.is_file():
            paths.add(candidate)
    return tuple(sorted(paths, key=lambda p: p.as_posix()))


def _url_identities(text: str) -> set[str]:
    identities: set[str] = set()
    for match in URL_RE.finditer(html.unescape(text)):
        token = match.group(0).rstrip(".,);]")
        try:
            identities.add(canonical_checkout_identity(token))
        except LifecycleError:
            continue
    return identities


def scan_active_surfaces(
    repo_root: Path, products: Iterable[Product]
) -> tuple[Violation, ...]:
    retired = tuple(product for product in products if product.state == "RETIRED")
    if not retired:
        return ()
    violations: list[Violation] = []
    for path in active_surface_paths(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as exc:
            raise LifecycleError(f"cannot read active surface: {path}") from exc
        found_urls = _url_identities(text)
        rel = path.relative_to(repo_root).as_posix()
        for product in retired:
            for checkout in product.checkout_urls:
                if checkout in found_urls:
                    violations.append(
                        Violation(product.id, rel, "checkout_url", checkout)
                    )
            for source in product.catalog_sources:
                if source in text:
                    violations.append(
                        Violation(product.id, rel, "catalog_source", source)
                    )
    return tuple(
        sorted(
            set(violations),
            key=lambda row: (row.product_id, row.path, row.kind, row.identity),
        )
    )


def check_repo(repo_root: Path, registry_path: Path | None = None) -> tuple[Violation, ...]:
    registry = registry_path or repo_root / "revenue/product_lifecycle/registry.json"
    products = load_registry(registry)
    return scan_active_surfaces(repo_root, products)


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--registry")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    registry = Path(args.registry).resolve() if args.registry else None
    try:
        violations = check_repo(repo_root, registry)
    except LifecycleError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    if violations:
        print(
            json.dumps(
                {
                    "ok": False,
                    "violations": [
                        {
                            "product_id": row.product_id,
                            "path": row.path,
                            "kind": row.kind,
                            "identity": row.identity,
                        }
                        for row in violations
                    ],
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps({"ok": True, "violations": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
