#!/usr/bin/env python3
"""Materialize the authenticated TITAN V3 handoff and repair L01 idempotence.

This script is intentionally self-contained so the GitHub Actions carrier stays
small and YAML-safe. It fails closed on payload, member, source-preimage, or
changed-file drift.
"""
from __future__ import annotations

import base64
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import textwrap


PAYLOAD_SHA256 = "f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728"
PAYLOAD_SIZE = 27_500
REPO = Path(__file__).resolve().parents[4]
CANDIDATES = REPO / "revenue/kaggriculture/cloud-execution-lab/candidates"
TRANSPORT = CANDIDATES / ".v3-handoff-f68792.b64"
V3 = CANDIDATES / "v3"
OVERLAY = V3 / "overlay"
SOURCE = OVERLAY / "l01_mechanics.py"
TESTS = OVERLAY / "checks" / "test_v3_l01.py"

EXPECTED_MEMBERS = {
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/.gitignore",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/FILES.json",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/README.md",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/V3-MANIFEST.json",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/apply_v3.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/build_v3.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/checks/test_v3_features.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/checks/test_v3_l01.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/e11_rival_sell.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/e20_hire_guard.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/l01_mechanics.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/rival_model.py",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/shop_arb.py",
}

VULNERABLE = (
    "            extra = max(0, len(sites) - KEEP_WHEAT_PLANTS)\n"
    "            for t, i in sites[-extra:]:\n"
)
REPAIRED = (
    "            extra = max(0, len(sites) - KEEP_WHEAT_PLANTS)\n"
    "            if extra == 0:\n"
    "                continue\n"
    "            for t, i in sites[-extra:]:\n"
)

TEST_BLOCK = textwrap.dedent(r"""

# Predecessor killers for sites[-0:] / repeated-install / aliased-route corruption.
import importlib.util as _l01_importlib_util
from collections import Counter as _L01Counter
from pathlib import Path as _L01Path
import unittest as _L01Unittest


def _l01_mechanics_under_idempotence_test():
    path = _L01Path(__file__).resolve().parents[1] / "l01_mechanics.py"
    spec = _l01_importlib_util.spec_from_file_location(
        "l01_mechanics_idempotence_test", path
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load l01_mechanics.py")
    module = _l01_importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _l01_wheat_route(count):
    return [
        {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": []}
        for _ in range(count)
    ]


class TestL01LeanPlantIdempotence(_L01Unittest.TestCase):
    def test_exact_72_is_identity(self):
        mechanics = _l01_mechanics_under_idempotence_test()
        route = _l01_wheat_route(mechanics.KEEP_WHEAT_PLANTS)
        activations = _L01Counter()
        mechanics.patch_routes(
            {"main": route}, {"LEANPLANT": True}, activations, []
        )
        self.assertEqual(
            mechanics.plant_counts(route)["WHEAT"],
            mechanics.KEEP_WHEAT_PLANTS,
        )
        self.assertEqual(activations["LEANPLANT"], 0)

    def test_second_application_is_identity(self):
        mechanics = _l01_mechanics_under_idempotence_test()
        extra = 92
        route = _l01_wheat_route(mechanics.KEEP_WHEAT_PLANTS + extra)
        activations = _L01Counter()
        flags = {"LEANPLANT": True}
        mechanics.patch_routes({"main": route}, flags, activations, [])
        first = mechanics.plant_counts(route)
        first_activations = activations["LEANPLANT"]
        mechanics.patch_routes({"main": route}, flags, activations, [])
        self.assertEqual(mechanics.plant_counts(route), first)
        self.assertEqual(first["WHEAT"], mechanics.KEEP_WHEAT_PLANTS)
        self.assertEqual(first_activations, extra)
        self.assertEqual(activations["LEANPLANT"], extra)

    def test_two_keys_aliasing_one_route_convert_once(self):
        mechanics = _l01_mechanics_under_idempotence_test()
        extra = 92
        shared = _l01_wheat_route(mechanics.KEEP_WHEAT_PLANTS + extra)
        routes = {"first": shared, "second": shared}
        activations = _L01Counter()
        mechanics.patch_routes(routes, {"LEANPLANT": True}, activations, [])
        self.assertIs(routes["first"], routes["second"])
        self.assertEqual(
            mechanics.plant_counts(shared)["WHEAT"],
            mechanics.KEEP_WHEAT_PLANTS,
        )
        self.assertEqual(activations["LEANPLANT"], extra)
""")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_member(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise AssertionError(f"unsafe archive path: {name!r}")
    normalized = str(path)
    if not normalized:
        raise AssertionError("empty archive path")
    return normalized


def _read_and_verify_payload() -> bytes:
    encoded = TRANSPORT.read_bytes()
    try:
        payload = base64.b64decode(b"".join(encoded.split()), validate=True)
    except Exception as exc:
        raise AssertionError("invalid base64 transport") from exc
    digest = hashlib.sha256(payload).hexdigest()
    assert digest == PAYLOAD_SHA256, (digest, PAYLOAD_SHA256)
    assert len(payload) == PAYLOAD_SIZE, (len(payload), PAYLOAD_SIZE)
    return payload


def _safe_extract(payload: bytes) -> None:
    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
        tmp.write(payload)
        tmp.flush()
        with tarfile.open(tmp.name, mode="r:gz") as archive:
            regular = []
            seen = set()
            for member in archive.getmembers():
                normalized = _normalize_member(member.name)
                if member.isdir():
                    continue
                assert member.isfile(), (
                    "non-regular archive member",
                    normalized,
                    member.type,
                )
                assert normalized not in seen, ("duplicate archive member", normalized)
                seen.add(normalized)
                regular.append((member, normalized))
            assert seen == EXPECTED_MEMBERS, (
                sorted(seen - EXPECTED_MEMBERS),
                sorted(EXPECTED_MEMBERS - seen),
            )
            for member, normalized in regular:
                target = (REPO / normalized).resolve()
                expected_target = (REPO / normalized).resolve()
                assert target == expected_target
                assert target == REPO.resolve() / normalized
                assert REPO.resolve() in target.parents
                source = archive.extractfile(member)
                assert source is not None
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read())


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _route(count: int) -> list[dict]:
    return [
        {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": []}
        for _ in range(count)
    ]


def _run_direct_witnesses() -> None:
    mechanics = _load_module("l01_repair_direct_check", SOURCE)

    exact = _route(mechanics.KEEP_WHEAT_PLANTS)
    activations = Counter()
    mechanics.patch_routes(
        {"main": exact}, {"LEANPLANT": True}, activations, []
    )
    assert mechanics.plant_counts(exact)["WHEAT"] == mechanics.KEEP_WHEAT_PLANTS
    assert activations["LEANPLANT"] == 0

    extra = 92
    repeated = _route(mechanics.KEEP_WHEAT_PLANTS + extra)
    activations = Counter()
    mechanics.patch_routes(
        {"main": repeated}, {"LEANPLANT": True}, activations, []
    )
    first = mechanics.plant_counts(repeated)
    first_activations = activations["LEANPLANT"]
    mechanics.patch_routes(
        {"main": repeated}, {"LEANPLANT": True}, activations, []
    )
    assert mechanics.plant_counts(repeated) == first
    assert first["WHEAT"] == mechanics.KEEP_WHEAT_PLANTS
    assert first_activations == extra
    assert activations["LEANPLANT"] == extra

    shared = _route(mechanics.KEEP_WHEAT_PLANTS + extra)
    routes = {"first": shared, "second": shared}
    activations = Counter()
    mechanics.patch_routes(routes, {"LEANPLANT": True}, activations, [])
    assert routes["first"] is routes["second"]
    assert mechanics.plant_counts(shared)["WHEAT"] == mechanics.KEEP_WHEAT_PLANTS
    assert activations["LEANPLANT"] == extra


def _repair() -> None:
    before = {
        path.relative_to(V3).as_posix(): _sha256(path)
        for path in sorted(V3.rglob("*"))
        if path.is_file()
    }
    assert set(before) == {
        member.split("/candidates/v3/", 1)[1] for member in EXPECTED_MEMBERS
    }

    source = SOURCE.read_text(encoding="utf-8")
    assert source.count(VULNERABLE) == 1, (
        "vulnerable leanplant preimage missing or duplicated",
        source.count(VULNERABLE),
    )
    assert REPAIRED not in source, "repair already present in authenticated preimage"
    SOURCE.write_text(source.replace(VULNERABLE, REPAIRED), encoding="utf-8")

    tests = TESTS.read_text(encoding="utf-8")
    sentinel = "class TestL01LeanPlantIdempotence("
    assert sentinel not in tests, "idempotence tests already present in preimage"
    markers = ("\nif __name__ == '__main__':", '\nif __name__ == "__main__":')
    for marker in markers:
        if marker in tests:
            tests = tests.replace(marker, TEST_BLOCK + marker, 1)
            break
    else:
        tests += TEST_BLOCK
    TESTS.write_text(tests, encoding="utf-8")

    after = {
        path.relative_to(V3).as_posix(): _sha256(path)
        for path in sorted(V3.rglob("*"))
        if path.is_file()
    }
    assert set(after) == set(before)
    changed = {path for path in before if before[path] != after[path]}
    assert changed == {
        "overlay/l01_mechanics.py",
        "overlay/checks/test_v3_l01.py",
    }, changed

    compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec")
    compile(TESTS.read_text(encoding="utf-8"), str(TESTS), "exec")
    _run_direct_witnesses()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(TESTS.parent),
            "-p",
            "test_v3_l01*.py",
            "-v",
        ],
        cwd=OVERLAY,
        check=True,
    )

    print("HANDOFF_OK", len(EXPECTED_MEMBERS), "files")
    print("L01_IDEMPOTENCE_OK")
    print("SOURCE_SHA256", _sha256(SOURCE))
    print("TEST_SHA256", _sha256(TESTS))


def main() -> int:
    payload = _read_and_verify_payload()
    _safe_extract(payload)
    _repair()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
