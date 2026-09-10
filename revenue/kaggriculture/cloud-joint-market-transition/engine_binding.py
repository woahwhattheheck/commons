# SPDX-License-Identifier: Apache-2.0
"""Internal support for the exact TITAN joint transition oracle."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SCHEMA = "titan-joint-market-transition-v1"
ENGINE_REPOSITORY = "Kaggle/kaggle-environments"
ENGINE_COMMIT = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
ENGINE_PATH = "kaggle_environments/envs/kaggriculture/kaggriculture.py"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"

TRANSITION_DEFINITIONS = frozenset((
    "CROPS ANIMALS PRODUCTS MARKET_I0 PRICE_FLOOR MARKET_PARAMS HINGE_GAIN "
    "LAND_ORDER LAND_PRICES FARM_HAND_COST_MULT SHOPS TOWN_CENTER_PRODUCTS MAX_SHOP_INSTANCES "
    "get _shape _quadrant_of _shed_access_tiles market_price _refresh_prices "
    "_spawn_hand _process_market _parse_order _commit_unit _fib _hire_cost "
    "_do_hire _do_buy_land _town_consume"
).split())


class Struct(dict):
    """Small attribute dictionary matching the official interpreter's inputs."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None


class BudgetExceeded(RuntimeError):
    """Raised internally when a request exceeds a declared deterministic bound."""


def git_blob_sha1(body: bytes) -> str:
    return hashlib.sha1(f"blob {len(body)}\0".encode("ascii") + body).hexdigest()


def _definition_names(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def load_transition_engine(path: str | Path) -> Any:
    """Load only exact pinned market/town definitions from official source bytes.

    Both Git's blob identity and the raw SHA-256 are required. A same-shaped local
    reimplementation is deliberately rejected.
    """

    source = Path(path)
    body = source.read_bytes()
    actual_blob = git_blob_sha1(body)
    actual_sha256 = hashlib.sha256(body).hexdigest()
    if actual_blob != ENGINE_GIT_BLOB:
        raise ValueError(f"engine_git_blob_mismatch:{actual_blob}")
    if actual_sha256 != ENGINE_SHA256:
        raise ValueError(f"engine_sha256_mismatch:{actual_sha256}")

    tree = ast.parse(body, filename=str(source))
    selected: list[ast.AST] = []
    found: set[str] = set()
    for node in tree.body:
        names = set(_definition_names(node))
        if names & TRANSITION_DEFINITIONS:
            selected.append(node)
            found.update(names)
    missing = TRANSITION_DEFINITIONS - found
    if missing:
        raise ValueError("missing_engine_definitions:" + ",".join(sorted(missing)))

    namespace: dict[str, Any] = {"math": math}
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(source), "exec"), namespace)
    namespace["source_sha256"] = actual_sha256
    namespace["git_blob_sha1"] = actual_blob
    namespace["source_path"] = str(source)
    return SimpleNamespace(**namespace)


def _validate_engine_identity(mechanics: Any) -> None:
    if getattr(mechanics, "git_blob_sha1", None) != ENGINE_GIT_BLOB:
        raise ValueError("unbound_engine_git_blob")
    if getattr(mechanics, "source_sha256", None) != ENGINE_SHA256:
        raise ValueError("unbound_engine_sha256")
    for name in ("_process_market", "_town_consume", "_parse_order", "market_price"):
        if not callable(getattr(mechanics, name, None)):
            raise ValueError(f"missing_engine_callable:{name}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)
