#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""F49: leakage-resistant opponent-family stratification from public action traces.

This module deliberately does not read leaderboard rank/score, team names, episode ids,
or any private/executable policy state into the feature vector.  The only model input
is the opponent's publicly recorded action stream.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

SCHEMA = "titan.f49.opponent-family.v1"
PROVENANCE = "public_recorded_actions"
EXPECTED_TARGETS = 41
EXPECTED_REPLAYS = 123
PHASES = ("early", "mid", "late")
CHANNELS = ("farmer", "hands", "market")
IDENTITY_FORBIDDEN = {
    "team_id", "team_name", "rank", "score", "leaderboard_score",
    "submission_id", "episode_id", "seed", "memberships",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool:true" if value else "bool:false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            return "num:nonfinite"
        return "num:zero" if float(value) == 0 else ("num:pos" if float(value) > 0 else "num:neg")
    return "str:" + str(value).strip().lower()


def _leaf_tokens(value, prefix="") -> List[str]:
    """Flatten an action payload into deterministic semantic tokens."""
    out: List[str] = []
    if isinstance(value, Mapping):
        for key in sorted(value):
            k = str(key).strip().lower()
            p = f"{prefix}.{k}" if prefix else k
            out.append("key:" + p)
            out.extend(_leaf_tokens(value[key], p))
    elif isinstance(value, list):
        for item in value:
            out.extend(_leaf_tokens(item, prefix + "[]"))
    else:
        out.append("val:" + prefix + "=" + _canon_scalar(value))
    return out


def _assert_no_identity_keys(value) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in IDENTITY_FORBIDDEN:
                raise ValueError("identity-like field is forbidden in action input: " + normalized)
            _assert_no_identity_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_identity_keys(nested)


def _is_active(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes, list, tuple, dict, set)):
        return len(value) > 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    return bool(value)


def feature_vector(actions: Sequence[Mapping]) -> Dict[str, float]:
    """Summarize a public action stream; accepts no identity metadata."""
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)) or not actions:
        raise ValueError("actions must be a non-empty sequence")
    n = len(actions)
    feature: Dict[str, float] = {}
    token_counts = Counter()
    unique_signatures = set()
    active_any = 0
    channel_counts = Counter()
    phase_channel_counts = Counter()
    phase_any_counts = Counter()

    for i, action in enumerate(actions):
        if not isinstance(action, Mapping):
            raise ValueError("each action must be an object")
        _assert_no_identity_keys(action)
        phase_idx = min(2, (3 * i) // n)
        phase = PHASES[phase_idx]
        normalized = {str(k).lower(): deepcopy(v) for k, v in action.items()}
        sig = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        unique_signatures.add(sha256_bytes(sig.encode("utf-8"))[:16])
        active = False
        for channel in CHANNELS:
            value = normalized.get(channel, [])
            if _is_active(value):
                channel_counts[channel] += 1
                phase_channel_counts[(phase, channel)] += 1
                active = True
            token_counts.update(_leaf_tokens(value, channel))
        if active:
            active_any += 1
            phase_any_counts[phase] += 1

    feature["activity.any"] = active_any / n
    feature["activity.noop"] = 1.0 - feature["activity.any"]
    feature["diversity.signature_per_turn"] = len(unique_signatures) / n
    for channel in CHANNELS:
        feature[f"channel.{channel}"] = channel_counts[channel] / n
    for phase in PHASES:
        lo = (PHASES.index(phase) * n) // 3
        hi = ((PHASES.index(phase) + 1) * n) // 3
        denom = max(1, hi - lo)
        feature[f"phase.{phase}.activity"] = phase_any_counts[phase] / denom
        for channel in CHANNELS:
            feature[f"phase.{phase}.{channel}"] = phase_channel_counts[(phase, channel)] / denom

    feature["skew.late_minus_early"] = feature["phase.late.activity"] - feature["phase.early.activity"]
    feature["skew.market_late_minus_early"] = feature["phase.late.market"] - feature["phase.early.market"]

    total_tokens = sum(token_counts.values()) or 1
    buckets = [0] * 16
    for token, count in token_counts.items():
        bucket = int(sha256_bytes(token.encode("utf-8"))[:8], 16) % len(buckets)
        buckets[bucket] += count
    for idx, count in enumerate(buckets):
        feature[f"token.bucket{idx:02d}"] = count / total_tokens
    return feature


def replay_actions(replay: Mapping, seat: int) -> List[Mapping]:
    steps = replay.get("steps")
    if seat not in (0, 1) or not isinstance(steps, list) or len(steps) < 2:
        raise ValueError("malformed replay/seat")
    if replay.get("statuses") not in (None, ["DONE", "DONE"]):
        raise ValueError("replay is not complete")
    actions = []
    for step in steps[1:]:
        if not isinstance(step, list) or len(step) != 2 or not isinstance(step[seat], Mapping):
            raise ValueError("malformed replay step")
        action = step[seat].get("action")
        if not isinstance(action, Mapping):
            raise ValueError("missing public action")
        actions.append(action)
    return actions


def read_fixture(corpus: Path, fixture: Mapping) -> List[Mapping]:
    rel = fixture.get("path")
    if not isinstance(rel, str):
        raise ValueError("fixture path missing")
    path = (corpus / rel).resolve(strict=True)
    root = corpus.resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("fixture escapes corpus")
    raw = path.read_bytes()
    expected = fixture.get("sha256")
    if not isinstance(expected, str) or sha256_bytes(raw) != expected:
        raise ValueError("fixture digest mismatch")
    replay = json.loads(gzip.decompress(raw))
    if fixture.get("seed") is not None and replay.get("info", {}).get("seed") != fixture.get("seed"):
        raise ValueError("fixture seed mismatch")
    return replay_actions(replay, fixture.get("recorded_opponent_seat"))


def aggregate(vectors: Sequence[Mapping[str, float]]) -> Dict[str, float]:
    if not vectors:
        raise ValueError("cannot aggregate zero vectors")
    keys = set(vectors[0])
    if any(set(v) != keys for v in vectors):
        raise ValueError("feature schema mismatch")
    return {k: float(median([float(v[k]) for v in vectors])) for k in sorted(keys)}


def robust_scale(vectors: Sequence[Mapping[str, float]]) -> Tuple[List[str], Dict[str, float], Dict[str, float]]:
    keys = sorted(vectors[0])
    centers, scales = {}, {}
    for k in keys:
        vals = sorted(float(v[k]) for v in vectors)
        centers[k] = float(median(vals))
        deviations = sorted(abs(x - centers[k]) for x in vals)
        mad = float(median(deviations))
        scales[k] = max(mad * 1.4826, 1e-6)
    return keys, centers, scales


def distance(a: Mapping[str, float], b: Mapping[str, float], keys: Sequence[str], scales: Mapping[str, float]) -> float:
    return sum(abs(float(a[k]) - float(b[k])) / scales[k] for k in keys) / max(1, len(keys))


def _vector_digest(v: Mapping[str, float]) -> str:
    payload = json.dumps({k: round(float(v[k]), 12) for k in sorted(v)}, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def deterministic_medoids(vectors: Sequence[Mapping[str, float]], k: int) -> Tuple[List[int], List[int], Dict[str, float]]:
    if not 2 <= k <= len(vectors):
        raise ValueError("k must be between 2 and number of vectors")
    keys, _centers, scales = robust_scale(vectors)
    digests = [_vector_digest(v) for v in vectors]
    first = min(range(len(vectors)), key=lambda i: digests[i])
    medoids = [first]
    while len(medoids) < k:
        candidates = [i for i in range(len(vectors)) if i not in medoids]
        next_idx = max(candidates, key=lambda i: (min(distance(vectors[i], vectors[m], keys, scales) for m in medoids), digests[i]))
        medoids.append(next_idx)

    for _ in range(50):
        assignment = [min(range(k), key=lambda j: (distance(v, vectors[medoids[j]], keys, scales), j)) for v in vectors]
        new_medoids = []
        for family in range(k):
            members = [i for i, a in enumerate(assignment) if a == family]
            if not members:
                new_medoids.append(medoids[family])
                continue
            new_medoids.append(min(members, key=lambda i: (sum(distance(vectors[i], vectors[j], keys, scales) for j in members), digests[i])))
        if new_medoids == medoids:
            break
        medoids = new_medoids
    assignment = [min(range(k), key=lambda j: (distance(v, vectors[medoids[j]], keys, scales), j)) for v in vectors]
    return assignment, medoids, scales


def phenotype(v: Mapping[str, float]) -> str:
    farmer, hands, market = (v.get("channel." + c, 0.0) for c in CHANNELS)
    noop = v.get("activity.noop", 0.0)
    late_market = v.get("skew.market_late_minus_early", 0.0)
    if late_market >= 0.18 and market >= max(farmer, hands) * 0.8:
        return "late-liquidator"
    if noop >= 0.45:
        return "sparse-reactive"
    dominant = max((farmer, "field-tempo"), (hands, "cargo-logistics"), (market, "market-active"))[1]
    return dominant if max(farmer, hands, market) >= 0.35 else "balanced"


def nomination(label: str) -> str:
    return {
        "sparse-reactive": "abstain by default; test only generic lower-tail guards",
        "late-liquidator": "prioritize F47 terminal congestion and F44 drop-before-last-sale diagnostics",
        "field-tempo": "prioritize F45 productive-harvest protection diagnostics",
        "cargo-logistics": "prioritize F43 deadline-cargo-return diagnostics",
        "market-active": "prioritize F46 saleable-quantity forecast diagnostics",
        "balanced": "no family-specific intervention; keep champion behavior",
    }[label]


def build_model(target_rows: Sequence[Mapping], k: int = 5, min_support: int = 3) -> Mapping:
    """Build families from per-target replay feature vectors.

    target_rows structure: {key: opaque bookkeeping id, vectors: [feature,...]}.
    The opaque key is emitted only as evidence membership and never enters geometry.
    """
    if len(target_rows) < max(k, min_support):
        raise ValueError("insufficient target support")
    training = []
    holdout = []
    keys = []
    for row in target_rows:
        vectors = row.get("vectors")
        if not isinstance(vectors, list) or len(vectors) < 3:
            raise ValueError("each target needs at least three fixtures")
        keys.append(str(row.get("key", len(keys))))
        training.append(aggregate(vectors[:-1]))
        holdout.append(vectors[-1])

    assignment, medoids, scales = deterministic_medoids(training, k)
    feature_keys = sorted(training[0])
    families = []
    medoid_vectors = [training[i] for i in medoids]
    support = Counter(assignment)
    family_ids = {}
    for j, medoid_vec in enumerate(medoid_vectors):
        family_ids[j] = "family-" + _vector_digest(medoid_vec)[:8]

    stable = 0
    abstained = 0
    held_out_rows = []
    for i, vector in enumerate(holdout):
        distances = sorted((distance(vector, medoid_vectors[j], feature_keys, scales), j) for j in range(k))
        best_d, best_j = distances[0]
        second_d = distances[1][0]
        margin = (second_d - best_d) / max(second_d, 1e-12)
        supported = support[best_j] >= min_support
        confident = margin >= 0.10
        predicted = family_ids[best_j] if supported and confident else "UNKNOWN"
        expected = family_ids[assignment[i]]
        if predicted == "UNKNOWN":
            abstained += 1
        if predicted == expected:
            stable += 1
        held_out_rows.append({"key": keys[i], "expected_family": expected,
                              "predicted_family": predicted, "margin": round(margin, 6),
                              "supported": supported})

    for j in range(k):
        medoid_vec = medoid_vectors[j]
        members = [keys[i] for i, a in enumerate(assignment) if a == j]
        label = phenotype(medoid_vec)
        families.append({
            "family_id": family_ids[j],
            "support_targets": len(members),
            "status": "ACTIVE" if len(members) >= min_support else "LOW_SUPPORT",
            "phenotype": label,
            "nomination": nomination(label),
            "medoid_feature_sha256": _vector_digest(medoid_vec),
            "members": sorted(members),
            "medoid": {key: round(float(medoid_vec[key]), 9) for key in feature_keys},
        })

    return {
        "schema": SCHEMA,
        "feature_input": "public opponent action streams only",
        "forbidden_model_inputs": sorted(IDENTITY_FORBIDDEN),
        "identity_used_for_geometry": False,
        "k": k,
        "min_support": min_support,
        "targets": len(target_rows),
        "held_out": {
            "fixtures": len(held_out_rows),
            "exact_family_matches": stable,
            "abstentions": abstained,
            "coverage": round((len(held_out_rows) - abstained) / len(held_out_rows), 6),
            "stable_accuracy_all": round(stable / len(held_out_rows), 6),
            "rows": held_out_rows,
        },
        "families": sorted(families, key=lambda x: x["family_id"]),
        "runtime_policy": {
            "unknown_is_noop": True,
            "classification_is_advisory": True,
            "candidate_policy_modified": False,
            "submission_hold": True,
        },
    }


def build_from_corpus(corpus: Path, manifest_path: Path, k: int, min_support: int) -> Mapping:
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest.get("schema") != "titan.gauntlet.top30-union.v1":
        raise ValueError("unexpected source manifest schema")
    targets = manifest.get("targets")
    if not isinstance(targets, list) or len(targets) != EXPECTED_TARGETS:
        raise ValueError(f"expected {EXPECTED_TARGETS} target versions")
    ids = [t.get("submission_id") for t in targets]
    if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("target submission bookkeeping ids must be unique positive integers")
    if sum(len(t.get("replays", [])) if isinstance(t.get("replays"), list) else 0 for t in targets) != EXPECTED_REPLAYS:
        raise ValueError(f"expected {EXPECTED_REPLAYS} replay fixtures")
    rows = []
    for target in targets:
        fixtures = target.get("replays")
        if not isinstance(fixtures, list) or len(fixtures) < 3:
            raise ValueError("target fixture set incomplete")
        vectors = [feature_vector(read_fixture(corpus, f)) for f in fixtures]
        rows.append({"key": str(target.get("submission_id")), "vectors": vectors})
    result = dict(build_model(rows, k=k, min_support=min_support))
    result["source"] = {
        "manifest_sha256": sha256_bytes(manifest_raw),
        "corpus_provenance": PROVENANCE,
        "targets": len(rows),
        "replays": sum(len(t.get("replays", [])) for t in targets),
    }
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--min-support", type=int, default=3)
    args = p.parse_args()
    result = build_from_corpus(args.corpus, args.manifest, args.k, args.min_support)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"families": len(result["families"]), "targets": result["targets"],
                      "coverage": result["held_out"]["coverage"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
