# SPDX-License-Identifier: Apache-2.0
"""Reproduce the L01 day-zero grammar defect with the pinned official interpreter.

The verifier reads only the three already-vendored engine members from a TITAN archive,
checks their exact hashes, initializes two ordinary players, and interprets one market
turn with a PASS rival.  It performs no network access and writes no source tree files.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import random
import sys
import tarfile
import tempfile
import types
from typing import Any, Callable

from l01_day0_guard import DAY0_ORDERS, certify_buy_product_basket

ENGINE_MEMBERS = {
    "kaggriculture.py": "checks/reference/engine/kaggriculture.py",
    "kaggriculture.json": "checks/reference/engine/kaggriculture.json",
    "utils.py": "checks/reference/engine/utils.py",
}
ENGINE_SHA256 = {
    "kaggriculture.py": "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e",
    "kaggriculture.json": "a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867",
    "utils.py": "537b627b11784d424147ef57ebb0369b039bf83c9f891e81f10486b1f552334b",
}
CONTROL_ACTION = {
    "farmer": ["PASS"],
    "hands": [],
    "market": [["BUY_PRODUCT", "WHEAT", 13]],
}
SHIPPED_ACTION = {
    "farmer": ["PASS"],
    "hands": [],
    "market": [list(order) for order in DAY0_ORDERS],
}
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}


class Struct(dict):
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def read_pinned_engine(archive_path: Path) -> dict[str, bytes]:
    """Read exact regular-file members without extracting the archive."""
    members: dict[str, bytes] = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        by_name = {member.name: member for member in archive.getmembers()}
        for short, member_name in ENGINE_MEMBERS.items():
            if not _canonical_member(member_name):
                raise ValueError(f"noncanonical engine member: {member_name!r}")
            member = by_name.get(member_name)
            if member is None or not member.isfile():
                raise ValueError(f"missing regular engine member: {member_name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"unreadable engine member: {member_name}")
            data = stream.read()
            if len(data) != member.size:
                raise ValueError(f"short engine member: {member_name}")
            actual = sha256(data)
            expected = ENGINE_SHA256[short]
            if actual != expected:
                raise ValueError(f"engine hash mismatch {short}: {actual} != {expected}")
            members[short] = data
    return members


def load_engine(members: dict[str, bytes], temp_root: Path):
    for name, data in members.items():
        (temp_root / name).write_bytes(data)

    parsed = ast.parse(members["utils.py"].decode("utf-8"))
    helper = next(
        node for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_episode_seed"
    )
    namespace = {"Any": Any, "Callable": Callable, "random": random}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), "pinned_seed_helper", "exec"), namespace)

    old_package = sys.modules.get("kaggle_environments")
    old_utils = sys.modules.get("kaggle_environments.utils")
    package = types.ModuleType("kaggle_environments")
    utils = types.ModuleType("kaggle_environments.utils")
    utils.resolve_episode_seed = namespace["resolve_episode_seed"]
    sys.modules["kaggle_environments"] = package
    sys.modules["kaggle_environments.utils"] = utils
    try:
        spec = importlib.util.spec_from_file_location(
            "official_kaggriculture_l01_day0_witness", temp_root / "kaggriculture.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot create engine import spec")
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        return engine
    finally:
        if old_package is None:
            sys.modules.pop("kaggle_environments", None)
        else:
            sys.modules["kaggle_environments"] = old_package
        if old_utils is None:
            sys.modules.pop("kaggle_environments.utils", None)
        else:
            sys.modules["kaggle_environments.utils"] = old_utils


def initialized(engine, seed: int = 1):
    cfg = Struct()
    for key, value in engine.specification["configuration"].items():
        cfg[key] = value.get("default") if isinstance(value, dict) else value
    cfg.seed = seed
    env = Struct(configuration=cfg, done=False, info={})
    state = [
        Struct(observation=Struct(), action={}, status="ACTIVE", reward=0)
        for _ in range(2)
    ]
    engine.interpreter(state, env)
    for player in state:
        player.observation.step = 0
    return cfg, env, state


def one_turn(engine, action: dict[str, Any], seed: int = 1) -> dict[str, Any]:
    _, env, state = initialized(engine, seed)
    state[0].action = copy.deepcopy(action)
    state[1].action = copy.deepcopy(PASS_ACTION)
    engine.interpreter(state, env)
    own = state[0].observation
    farm = own.farms[0]
    private = own.private
    return {
        "money": farm["money"],
        "shed": {key: value for key, value in private["shed"].items() if value},
        "seeds": {key: value for key, value in private["seeds"].items() if value},
        "wheat_market_inventory": own.market["inventory"]["WHEAT"],
        "wheat_market_price": own.market["prices"]["WHEAT"],
    }


def run_witness(archive_path: Path, seed: int = 1) -> dict[str, Any]:
    members = read_pinned_engine(archive_path)
    with tempfile.TemporaryDirectory(prefix="titan-l01-day0-engine-") as directory:
        engine = load_engine(members, Path(directory))
        control = one_turn(engine, CONTROL_ACTION, seed)
        shipped = one_turn(engine, SHIPPED_ACTION, seed)

    certificate = certify_buy_product_basket(DAY0_ORDERS)
    result = {
        "schema": "titan.l01-day0-engine-witness.v1",
        "engine_sha256": {name: sha256(data) for name, data in sorted(members.items())},
        "seed": seed,
        "rival_action": PASS_ACTION,
        "control_action": CONTROL_ACTION,
        "shipped_action": SHIPPED_ACTION,
        "source_certificate": certificate.as_dict(),
        "control": control,
        "shipped": shipped,
        "control_minus_shipped_wheat": control["shed"].get("WHEAT", 0) - shipped["shed"].get("WHEAT", 0),
        "shipped_minus_control_money": shipped["money"] - control["money"],
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["receipt_sha256"] = sha256(canonical.encode("utf-8"))
    return result


def default_archive() -> Path:
    candidate = Path(__file__).resolve().parents[3] / "exports" / "titan-current.tar.gz"
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=default_archive())
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_witness(args.archive, args.seed)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
