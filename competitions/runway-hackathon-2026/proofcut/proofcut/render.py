from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .core import ProofCutError, canonical_json, sha256_bytes
from .providers import GenerationRequest, Provider


def execute_generated_shots(manifest: dict[str, Any], provider: Provider) -> dict[str, Any]:
    if manifest.get("schema") != "proofcut.manifest.v1":
        raise ProofCutError("bad manifest schema")
    shots = []
    all_generated_ok = True
    for shot in manifest.get("shots", []):
        shot = dict(shot)
        if shot.get("type") == "generated":
            result = provider.generate(GenerationRequest(
                shot_id=shot["id"],
                prompt=shot["prompt"],
                duration_seconds=shot["duration_seconds"],
            ))
            shot["generation"] = asdict(result)
            shot["status"] = result.status
            all_generated_ok &= result.status == "SUCCEEDED" and bool(result.output_url)
        shots.append(shot)
    core = {
        "schema": "proofcut.render-plan.v1",
        "manifest_sha256": manifest.get("manifest_sha256"),
        "shots": shots,
        "publish_status": "READY_FOR_HUMAN_REVIEW" if all_generated_ok else "HOLD_PROVIDER",
    }
    return {**core, "render_plan_sha256": sha256_bytes(canonical_json(core))}
