#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One-shot exact-anchor integration of the submitted-V3.1 floor into #13409."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
GATE = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/promotion-gate"
RELEASE = GATE / "release_transaction.py"
WORKFLOW = ROOT / ".github/workflows/titan-v5-promotion-release-gates.yml"


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exact anchor once, found {count}")
    return text.replace(old, new, 1)


def patch_release() -> None:
    text = RELEASE.read_text()
    if 'V31_SCHEMA = "titan-v5-release-transaction/v4"' in text:
        return
    text = once(
        text,
        'SCHEMA = "titan-v5-release-transaction/v3"\nTRANSITION_PREFIX = "v5tx:"',
        'SCHEMA = "titan-v5-release-transaction/v3"\n'
        'V31_SCHEMA = "titan-v5-release-transaction/v4"\n'
        'V31_FLOOR_ID = "kaggle-submission:56172377"\n'
        'V31_FLOOR_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"\n'
        'TRANSITION_PREFIX = "v5tx:"',
        "schema constants",
    )
    marker = '\n\ndef _trust_digest(files: Mapping[str, bytes]) -> str:\n'
    replay = '''\n\ndef _v31_floor_replay(\n    floor_builder: Callable[..., Mapping[str, Any]],\n    floor_raw: bytes,\n    economics_raw: bytes,\n    economics_receipt: Mapping[str, Any],\n    *,\n    candidate_id: str,\n    engine_id: Any,\n    opponent_pack_id: Any,\n    candidate_archive_sha256: str,\n) -> dict[str, Any]:\n    floor_report = _loads(floor_raw, "V3.1 floor report")\n    economics_report = _loads(economics_raw, "economics report for V3.1 floor")\n    if type(floor_report) is not dict or type(economics_report) is not dict:\n        raise TransactionError("V3.1 floor inputs must be objects")\n    try:\n        receipt = floor_builder(\n            floor_report, economics_report, candidate_id=candidate_id,\n            engine_id=engine_id, opponent_pack_id=opponent_pack_id,\n            candidate_archive_sha256=candidate_archive_sha256,\n        )\n    except Exception as exc:\n        raise TransactionError(f"V3.1 floor gate replay failed: {exc}") from exc\n    if type(receipt) is not dict:\n        raise TransactionError("V3.1 floor gate did not return an object")\n    if receipt.get("classification") != "PASS" or receipt.get("release_ready") is not True:\n        raise TransactionError("V3.1 floor gate is not a release-ready PASS")\n    expected = {\n        "floor_id": V31_FLOOR_ID, "candidate_id": candidate_id,\n        "engine_id": engine_id, "opponent_pack_id": opponent_pack_id,\n        "floor_archive_sha256": V31_FLOOR_ARCHIVE_SHA256,\n        "candidate_archive_sha256": candidate_archive_sha256,\n    }\n    for key, value in expected.items():\n        if receipt.get(key) != value:\n            raise TransactionError(f"V3.1 floor receipt {key} disagrees with release authority")\n    for key in ("opponent_count", "opponent_ids", "cell_count", "seed_count"):\n        if receipt.get(key) != economics_receipt.get(key):\n            raise TransactionError(f"V3.1 floor receipt {key} disagrees with paired economics topology")\n    delta = receipt.get("sum_margin_delta_vs_v31")\n    if type(delta) is not int or delta <= 0:\n        raise TransactionError("V3.1 floor receipt must have strictly positive aggregate delta")\n    return receipt\n'''
    text = once(text, marker, replay + marker, "floor replay")
    text = once(
        text,
        '    economics_builder: Callable[..., Mapping[str, Any]],\n'
        '    trust_result: Mapping[str, Any],\n'
        '    trust_files: Mapping[str, bytes],\n'
        ') -> dict[str, Any]:',
        '    economics_builder: Callable[..., Mapping[str, Any]],\n'
        '    trust_result: Mapping[str, Any],\n'
        '    trust_files: Mapping[str, bytes],\n'
        '    v31_floor_raw: bytes | None = None,\n'
        '    v31_floor_builder: Callable[..., Mapping[str, Any]] | None = None,\n'
        ') -> dict[str, Any]:',
        "build signature",
    )
    economics = '''    economics = _economics_replay(\n        economics_builder,\n        economics_raw,\n        candidate_id=promotion["candidate_id"],\n        control_id=promotion["control_id"],\n        engine_id=manifest.get("engine_id"),\n        opponent_pack_id=manifest.get("opponent_pack_id"),\n        control_archive_sha256=old_pointer["sha256"],\n        candidate_archive_sha256=new_pointer["sha256"],\n    )\n    bind_promoted_sources(manifest, source_manifest, archive_members)\n'''
    economics_new = economics.replace(
        '    bind_promoted_sources(manifest, source_manifest, archive_members)\n',
        '''    v31_floor = None\n    if (v31_floor_raw is None) != (v31_floor_builder is None):\n        raise TransactionError("V3.1 floor raw evidence and builder must be supplied together")\n    if v31_floor_raw is not None and v31_floor_builder is not None:\n        v31_floor = _v31_floor_replay(\n            v31_floor_builder, v31_floor_raw, economics_raw, economics,\n            candidate_id=promotion["candidate_id"],\n            engine_id=manifest.get("engine_id"),\n            opponent_pack_id=manifest.get("opponent_pack_id"),\n            candidate_archive_sha256=new_pointer["sha256"],\n        )\n    bind_promoted_sources(manifest, source_manifest, archive_members)\n''',
    )
    text = once(text, economics, economics_new, "floor build invocation")
    tail = '''        "trusted_base": {\n            "control_plane_sha256": trust_sha,\n            "validator_sha256": _sha(trust_files["check_control_plane.py"]),\n        },\n    }\n    transition_id = TRANSITION_PREFIX + _sha(_canonical(core))\n    return {\n        "schema": SCHEMA,\n'''
    tail_new = '''        "trusted_base": {\n            "control_plane_sha256": trust_sha,\n            "validator_sha256": _sha(trust_files["check_control_plane.py"]),\n        },\n    }\n    if v31_floor is not None:\n        core["v31_floor"] = {\n            "report_sha256": _sha(v31_floor_raw),\n            "floor_id": v31_floor["floor_id"],\n            "floor_archive_sha256": v31_floor["floor_archive_sha256"],\n            "candidate_archive_sha256": v31_floor["candidate_archive_sha256"],\n            "opponent_count": v31_floor["opponent_count"],\n            "opponent_ids": v31_floor["opponent_ids"],\n            "cell_count": v31_floor["cell_count"],\n            "seed_count": v31_floor["seed_count"],\n            "sum_margin_delta_vs_v31": v31_floor["sum_margin_delta_vs_v31"],\n            "mean_margin_delta_vs_v31": v31_floor["mean_margin_delta_vs_v31"],\n            "topology_sha256": v31_floor["topology_sha256"],\n            "candidate_scores_sha256": v31_floor["candidate_scores_sha256"],\n            "floor_panel_sha256": v31_floor["floor_panel_sha256"],\n        }\n    transition_id = TRANSITION_PREFIX + _sha(_canonical(core))\n    return {\n        "schema": V31_SCHEMA if v31_floor is not None else SCHEMA,\n'''
    text = once(text, tail, tail_new, "transaction core")
    text = once(
        text,
        '    parser.add_argument("--economics-report", type=Path, required=True)\n',
        '    parser.add_argument("--economics-report", type=Path, required=True)\n'
        '    parser.add_argument("--v31-floor-report", type=Path, required=True)\n',
        "cli floor arg",
    )
    text = once(
        text,
        '        economics_module, _ = _load_module(here.with_name("economics_gate.py"), "_titan_v5_economics_gate")\n',
        '        economics_module, _ = _load_module(here.with_name("economics_gate.py"), "_titan_v5_economics_gate")\n'
        '        floor_module, _ = _load_module(here.with_name("v31_floor_gate.py"), "_titan_v5_v31_floor_gate")\n',
        "floor module load",
    )
    text = once(
        text,
        '            economics_raw=_read(args.economics_report, "economics report"),\n'
        '            promotion_builder=promotion_module.build_receipt,\n'
        '            economics_builder=economics_module.validate_report,\n'
        '            trust_result=trust_result,\n'
        '            trust_files=trust_files,\n',
        '            economics_raw=_read(args.economics_report, "economics report"),\n'
        '            promotion_builder=promotion_module.build_receipt,\n'
        '            economics_builder=economics_module.validate_report,\n'
        '            trust_result=trust_result,\n'
        '            trust_files=trust_files,\n'
        '            v31_floor_raw=_read(args.v31_floor_report, "V3.1 floor report"),\n'
        '            v31_floor_builder=floor_module.validate_report,\n',
        "cli build floor",
    )
    RELEASE.write_text(text)


def patch_workflow() -> None:
    text = WORKFLOW.read_text()
    if "test_v31_floor_gate" in text:
        return
    text = once(
        text,
        "            economics_gate.py release_transaction.py promotion_gate.py \\\n            test_economics_gate.py test_release_transaction.py test_promotion_gate.py\n",
        "            economics_gate.py v31_floor_gate.py release_transaction.py promotion_gate.py \\\n            test_economics_gate.py test_v31_floor_gate.py test_release_transaction.py \\\n            test_release_v31_floor.py test_promotion_gate.py\n",
        "workflow compile",
    )
    old = """          python -B -m unittest -v \\
            test_economics_gate test_release_transaction test_promotion_gate
          python -O -B -m unittest -v \\
            test_economics_gate test_release_transaction test_promotion_gate
"""
    new = """          python -B -m unittest -v \\
            test_economics_gate test_v31_floor_gate test_release_transaction \\
            test_release_v31_floor test_promotion_gate
          python -O -B -m unittest -v \\
            test_economics_gate test_v31_floor_gate test_release_transaction \\
            test_release_v31_floor test_promotion_gate
"""
    text = once(text, old, new, "workflow tests")
    WORKFLOW.write_text(text)


def main() -> int:
    patch_release()
    patch_workflow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
