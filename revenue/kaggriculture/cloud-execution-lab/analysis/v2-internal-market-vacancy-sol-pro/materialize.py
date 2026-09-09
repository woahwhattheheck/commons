# SPDX-License-Identifier: Apache-2.0
"""Materialize the frozen-V2 internal market-vacancy experiment.

The source tree is copied byte-for-byte, then one bounded mechanism is added:
when the executable first-N market window is raw-length saturated but contains
an internal empty row before a later inherited row, the scheduler may use that
exact row for one of its already-selected SELL orders. Existing non-empty rows
never move. Trailing empty rows are deliberately excluded; SOL-VACANCY owns
that separate mechanism.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any

EXPECTED_V2_SCHEDULER_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
EXPECTED_V2_SCHEDULER_SHA256 = (
    "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8"
)
EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"

HELPER_ANCHOR = "\n\nclass SellScheduler:\n"
HELPER = (
    "def _internal_market_vacancies(orders, limit):\n"
    "    \"\"\"Indices of empty executable rows before a later non-empty row.\"\"\"\n"
    "    window=list(orders[:max(0,int(limit))])\n"
    "    last_nonempty=max((i for i,row in enumerate(window) if row),default=-1)\n"
    "    return tuple(i for i,row in enumerate(window[:last_nonempty]) if not row)\n"
)
NEW_HELPER_ANCHOR = "\n\n" + HELPER + "\nclass SellScheduler:\n"

OLD_FEASIBILITY = """            def feasible(plan):
                for t,q in plan:
                    if q<=0:continue
                    orders=base['market'] if t==now else route[t].get('market',[]) if t<len(route) else []
                    if len(orders)>=int(config.get('maxMarketOrdersPerTurn',10)):
                        offered=sum(max(0,int(o[2])) for o in orders if o and o[0]=='SELL' and o[1]==item)
                        if q>offered:return False
                return receipt_feasible(plan)
"""
NEW_FEASIBILITY = """            def feasible(plan):
                for t,q in plan:
                    if q<=0:continue
                    orders=base['market'] if t==now else route[t].get('market',[]) if t<len(route) else []
                    limit=int(config.get('maxMarketOrdersPerTurn',10))
                    if len(orders)>=limit and not _internal_market_vacancies(orders,limit):
                        offered=sum(max(0,int(o[2])) for o in orders if o and o[0]=='SELL' and o[1]==item)
                        if q>offered:return False
                return receipt_feasible(plan)
"""

OLD_OUTPUT = """        for item in sorted(targets):
            q=min(remaining.get(item,0),max(0,available.get(item,0)))
            if q>0 and len(market)<int(config.get('maxMarketOrdersPerTurn',10)):
                market.append(['SELL',item,q]);available[item]=available.get(item,0)-q
        out['market']=market
"""
NEW_OUTPUT = """        limit=int(config.get('maxMarketOrdersPerTurn',10))
        for item in sorted(targets):
            q=min(remaining.get(item,0),max(0,available.get(item,0)))
            if q<=0:continue
            if len(market)>=limit:
                vacancies=_internal_market_vacancies(market,limit)
                if vacancies:
                    market[vacancies[-1]]=['SELL',item,q]
                    available[item]=available.get(item,0)-q
            else:
                market.append(['SELL',item,q]);available[item]=available.get(item,0)-q
        out['market']=market
"""


class MaterializeError(ValueError):
    """Frozen source or requested one-factor materialization is not exact."""


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def inventory(root: Path) -> dict[str, dict[str, Any]]:
    if not root.is_dir():
        raise MaterializeError(f"source is not a directory: {root}")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise MaterializeError(f"non-regular member is forbidden: {relative}")
        data = path.read_bytes()
        result[relative] = {
            "bytes": len(data),
            "sha256": sha256(data),
            "git_blob_sha1": git_blob_sha1(data),
        }
    if not result:
        raise MaterializeError("source inventory is empty")
    return result


def closure_sha256(items: dict[str, dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for relative, record in sorted(items.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def patch_scheduler(original: bytes) -> bytes:
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterializeError("scheduler is not UTF-8") from exc

    expected = (
        ("helper anchor", HELPER_ANCHOR, NEW_HELPER_ANCHOR),
        ("feasibility block", OLD_FEASIBILITY, NEW_FEASIBILITY),
        ("output block", OLD_OUTPUT, NEW_OUTPUT),
    )
    for label, old, new in expected:
        count = text.count(old)
        if count != 1:
            raise MaterializeError(f"expected exactly one {label}, found {count}")
        if new != NEW_HELPER_ANCHOR and new in text:
            raise MaterializeError(f"new {label} already exists in source")
    if HELPER in text:
        raise MaterializeError("internal-vacancy helper already exists in source")

    patched = text.replace(HELPER_ANCHOR, NEW_HELPER_ANCHOR, 1)
    patched = patched.replace(OLD_FEASIBILITY, NEW_FEASIBILITY, 1)
    patched = patched.replace(OLD_OUTPUT, NEW_OUTPUT, 1)
    try:
        compile(patched, "scheduler.py", "exec")
    except SyntaxError as exc:
        raise MaterializeError(f"patched scheduler does not compile: {exc}") from exc
    return patched.encode("utf-8")


def materialize(
    source: Path,
    output: Path,
    *,
    expected_scheduler_blob: str = EXPECTED_V2_SCHEDULER_BLOB,
    expected_scheduler_sha256: str = EXPECTED_V2_SCHEDULER_SHA256,
) -> dict[str, Any]:
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise MaterializeError(f"output already exists: {output}")
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise MaterializeError("output may not be nested inside source")

    before = inventory(source)
    if "scheduler.py" not in before or "candidate.py" not in before:
        raise MaterializeError("source is missing scheduler.py or candidate.py")
    original = (source / "scheduler.py").read_bytes()
    actual_blob = git_blob_sha1(original)
    actual_sha256 = sha256(original)
    if actual_blob != expected_scheduler_blob:
        raise MaterializeError(
            f"frozen V2 scheduler blob mismatch: expected {expected_scheduler_blob}, "
            f"got {actual_blob}"
        )
    if actual_sha256 != expected_scheduler_sha256:
        raise MaterializeError(
            f"frozen V2 scheduler SHA-256 mismatch: expected "
            f"{expected_scheduler_sha256}, got {actual_sha256}"
        )

    patched = patch_scheduler(original)
    shutil.copytree(source, output, symlinks=False)
    atomic_write(output / "scheduler.py", patched)

    after = inventory(output)
    if set(before) != set(after):
        raise MaterializeError("materialized file inventory differs from frozen V2")
    changed = [
        relative
        for relative in sorted(before)
        if before[relative]["sha256"] != after[relative]["sha256"]
    ]
    if changed != ["scheduler.py"]:
        raise MaterializeError(f"one-factor boundary violated: changed={changed!r}")
    if inventory(source) != before:
        raise MaterializeError("frozen source tree changed during materialization")

    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="v2/scheduler.py",
            tofile="v2-internal-vacancy/scheduler.py",
            n=4,
        )
    )
    return {
        "schema": "titan.v2.internal-market-vacancy.materialization.v1",
        "operation": "titan-v2-internal-market-vacancy-20260909-sol-pro-01",
        "scope": {
            "mechanism": "internal_empty_executable_rows_only",
            "trailing_empty_rows": "excluded",
            "inherited_nonempty_row_movement": "forbidden",
        },
        "source": {
            "scheduler_git_blob_sha1": actual_blob,
            "scheduler_sha256": actual_sha256,
            "closure_sha256": closure_sha256(before),
            "files": len(before),
        },
        "candidate": {
            "changed_files": changed,
            "scheduler_git_blob_sha1": git_blob_sha1(patched),
            "scheduler_sha256": sha256(patched),
            "closure_sha256": closure_sha256(after),
            "helper_anchor_occurrences": patched.count(HELPER.encode("utf-8")),
            "old_feasibility_occurrences": patched.count(
                OLD_FEASIBILITY.encode("utf-8")
            ),
            "new_feasibility_occurrences": patched.count(
                NEW_FEASIBILITY.encode("utf-8")
            ),
            "old_output_occurrences": patched.count(OLD_OUTPUT.encode("utf-8")),
            "new_output_occurrences": patched.count(NEW_OUTPUT.encode("utf-8")),
            "unified_diff": diff,
        },
        "frozen_v1_scheduler_git_blob_sha1": EXPECTED_V1_SCHEDULER_BLOB,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.source, args.output)
    atomic_write(
        args.receipt,
        (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )
    print(
        json.dumps(
            {
                "source_blob": receipt["source"]["scheduler_git_blob_sha1"],
                "candidate_blob": receipt["candidate"]["scheduler_git_blob_sha1"],
                "source_closure": receipt["source"]["closure_sha256"],
                "candidate_closure": receipt["candidate"]["closure_sha256"],
                "changed_files": receipt["candidate"]["changed_files"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
