#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact submitted-V4 active frozen-seller early-pruning ablation helpers."""
from __future__ import annotations

import ast
import hashlib
import io
from pathlib import Path, PurePosixPath
import tarfile

BASELINE_SHA256 = "4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b"
V31_SOURCE = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V4_SOURCE = "4af1113154e78c662780e6658cd920daac7902e3"
V4_SELECTED_SELL_CORE_GIT_BLOB = "f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3"
TARGET_MEMBER = "selected_sell_core.py"
HISTORICAL_PR = 11017

_PRUNED_BLOCK = b"""    # Preserve the exact incumbent strict-dominance behavior and its cheap
    # no-rival prune. Alternative E18 rules deliberately evaluate the same
    # feasible candidate family without this economic prune.
    if reference_feasible and rule=='strict':
        for plan in sorted(candidates):
            if sum(q for _,q in plan)>quantity:continue
            if dict(plan).get(now,0)<minimum_now:continue
            first_score=model.score(plan,quantity,0,'paired',end==last)
            if first_score[0]-baseline[0][0] <= 0:
                continue
            if capacity_ok and not capacity_ok(plan):continue
            scores=[first_score]
            competitive=True
            for (_,r,a),b in zip(scenarios[1:],baseline[1:]):
                score=model.score(plan,quantity,r,a,end==last)
                if score[0]-b[0] <= 0:
                    competitive=False
                    break
                scores.append(score)
            if not competitive:continue
            deltas=[s[0]-b[0] for s,b in zip(scores,baseline)]
            key=(round(min(deltas),8),round(sum(deltas),8),float(dict(plan).get(now,0)))
            if key[0]>0 and key>best_key:
                best_key,best_plan,best_scores=key,plan,scores
                found_feasible=True
        accepted=best_key[0]>0
        acceptance_score=best_key[0] if accepted else 0.0
        chosen_deltas=[s[0]-b[0] for s,b in zip(best_scores,baseline)]
        weighted_expected_gain=_weighted_gain(chosen_deltas,names,weights)
"""

_FULL_EVALUATION_BLOCK = b"""    # Evidence-only ablation of V4's active frozen-seller early prune.
    # Preserve V4 strict-dominance selection, but restore the incumbent
    # evaluation order: physical capacity first, then every scenario.
    if reference_feasible and rule=='strict':
        for plan in sorted(candidates):
            if sum(q for _,q in plan)>quantity:continue
            if dict(plan).get(now,0)<minimum_now:continue
            if capacity_ok and not capacity_ok(plan):continue
            scores=[model.score(plan,quantity,r,a,end==last) for _,r,a in scenarios]
            deltas=[s[0]-b[0] for s,b in zip(scores,baseline)]
            key=(round(min(deltas),8),round(sum(deltas),8),float(dict(plan).get(now,0)))
            if key[0]>0 and key>best_key:
                best_key,best_plan,best_scores=key,plan,scores
                found_feasible=True
        accepted=best_key[0]>0
        acceptance_score=best_key[0] if accepted else 0.0
        chosen_deltas=[s[0]-b[0] for s,b in zip(best_scores,baseline)]
        weighted_expected_gain=_weighted_gain(chosen_deltas,names,weights)
"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def archive_members_bytes(raw: bytes) -> dict[str, bytes]:
    """Parse already-captured tar bytes without reopening an external path."""
    if type(raw) is not bytes:
        raise TypeError("archive bytes must be bytes")
    result: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as archive:
        for member in archive:
            rel = PurePosixPath(member.name)
            if (not member.name or "\\" in member.name or rel.is_absolute()
                    or ".." in rel.parts or str(rel) != member.name.rstrip("/")):
                raise ValueError(f"invalid archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile() or member.name in result:
                raise ValueError(f"non-file or duplicate member: {member.name}")
            if member.size > 100 * 1024**2:
                raise ValueError(f"oversized member: {member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"unreadable archive member: {member.name}")
            with stream:
                payload = stream.read()
            if len(payload) != member.size:
                raise ValueError(f"truncated archive member: {member.name}")
            result[member.name] = payload
    if "main.py" not in result or TARGET_MEMBER not in result:
        raise ValueError("expected canonical submitted-V4 flat archive layout")
    return result


def _rewrite_selected_sell_core(raw: bytes, expected_blob: str) -> bytes:
    if type(raw) is not bytes:
        raise TypeError("selected seller source must be bytes")
    actual = git_blob_bytes(raw)
    if actual != expected_blob:
        raise ValueError(
            f"submitted-V4 selected seller preimage drift: expected {expected_blob}, got {actual}"
        )
    if raw.count(_PRUNED_BLOCK) != 1:
        raise ValueError("expected exactly one V4 strict early-pruning block")
    if _FULL_EVALUATION_BLOCK in raw:
        raise ValueError("full-evaluation treatment already present")
    changed = raw.replace(_PRUNED_BLOCK, _FULL_EVALUATION_BLOCK, 1)
    if changed == raw or _PRUNED_BLOCK in changed:
        raise AssertionError("early-pruning ablation did not replace the exact block")
    ast.parse(changed.decode("utf-8"))
    marker = b"    elif not reference_feasible:\n"
    if raw.count(marker) != 1 or changed.count(marker) != 1:
        raise ValueError("V4 forced-feasibility boundary drift")
    if raw.split(marker, 1)[1] != changed.split(marker, 1)[1]:
        raise AssertionError("treatment changed V4 forced-feasibility/E18 tail")
    return changed


def rewrite_early_pruning_off(raw: bytes) -> bytes:
    """Disable only V4's strict early prune on the exact submitted source preimage."""
    return _rewrite_selected_sell_core(raw, V4_SELECTED_SELL_CORE_GIT_BLOB)


def exact_v4_arms(baseline_raw: bytes) -> dict[str, dict[str, bytes]]:
    """Return exact submitted-V4 control plus one-member pruning-off treatment."""
    if type(baseline_raw) is not bytes:
        raise TypeError("baseline archive capture must be bytes")
    actual = sha256_bytes(baseline_raw)
    if actual != BASELINE_SHA256:
        raise ValueError(f"baseline is not exact submitted V4: {actual}")
    control = archive_members_bytes(baseline_raw)
    selected = control[TARGET_MEMBER]
    if git_blob_bytes(selected) != V4_SELECTED_SELL_CORE_GIT_BLOB:
        raise ValueError("submitted V4 selected_sell_core.py preimage mismatch")
    treatment = dict(control)
    treatment[TARGET_MEMBER] = rewrite_early_pruning_off(selected)
    if set(treatment) != set(control):
        raise AssertionError("treatment changed archive membership")
    changed = [name for name in control if control[name] != treatment[name]]
    if changed != [TARGET_MEMBER]:
        raise AssertionError(f"expected only {TARGET_MEMBER} to change; got {changed}")
    return {"control": control, "early_pruning_off": treatment}


def treatment_receipt(control: dict[str, bytes], treatment: dict[str, bytes]) -> dict:
    changed = [name for name in control if treatment.get(name) != control[name]]
    if changed != [TARGET_MEMBER] or set(control) != set(treatment):
        raise ValueError("arms do not satisfy one-member treatment contract")
    return {
        "schema": "astra.v5.v31-v4-frozen-seller-pruning-ablation.v1",
        "baseline_archive_sha256": BASELINE_SHA256,
        "v31_source": V31_SOURCE,
        "v4_source": V4_SOURCE,
        "historical_pr": HISTORICAL_PR,
        "changed_members": changed,
        "control_selected_sell_core_git_blob": git_blob_bytes(control[TARGET_MEMBER]),
        "treatment_selected_sell_core_sha256": sha256_bytes(treatment[TARGET_MEMBER]),
        "semantic_delta": (
            "disable only submitted-V4 strict/reference-feasible early pruning; "
            "restore capacity-first/all-scenario evaluation while retaining V4 decision rule"
        ),
    }
