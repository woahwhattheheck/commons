from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .core import ProofCutError, sha256_bytes

@dataclass(frozen=True)
class GenerationRequest:
    shot_id: str
    prompt: str
    duration_seconds: int

@dataclass(frozen=True)
class GenerationResult:
    shot_id: str
    provider: str
    status: str
    output_url: str | None
    task_id: str | None
    estimated_credits: int

class Provider(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult: ...

class FakeProvider:
    """Deterministic zero-network provider for hostile tests and demos."""
    def __init__(self, *, fail_ids: set[str] | None = None):
        self.fail_ids = fail_ids or set()

    def generate(self, request: GenerationRequest) -> GenerationResult:
        cost = estimate_wan3_credits(request.duration_seconds, resolution="480p")
        if request.shot_id in self.fail_ids:
            return GenerationResult(request.shot_id, "fake", "FAILED", None, "fake-failed", cost)
        digest = sha256_bytes(f"{request.shot_id}\n{request.prompt}\n{request.duration_seconds}".encode())[:24]
        return GenerationResult(request.shot_id, "fake", "SUCCEEDED", f"fake://proofcut/{digest}.mp4", f"fake-{digest}", cost)


def estimate_wan3_credits(duration_seconds: int, *, resolution: str) -> int:
    rates = {"480p": 5, "720p": 10, "1080p": 20}
    if resolution not in rates:
        raise ProofCutError("unsupported WAN 3.0 resolution")
    if not isinstance(duration_seconds, int) or isinstance(duration_seconds, bool) or not 2 <= duration_seconds <= 30:
        raise ProofCutError("WAN 3.0 duration must be 2..30 seconds")
    return duration_seconds * rates[resolution]

class RunwayProvider:
    """Real provider adapter. Network/spend occurs only when caller opts in explicitly."""
    def __init__(self, *, execute: bool, max_credits: int, resolution: str = "480p"):
        if not execute:
            raise ProofCutError("real Runway execution requires execute=True")
        secret = os.environ.get("RUNWAYML_API_SECRET")
        if not secret:
            raise ProofCutError("RUNWAYML_API_SECRET is missing")
        if not isinstance(max_credits, int) or isinstance(max_credits, bool) or max_credits <= 0:
            raise ProofCutError("positive max_credits required")
        self.secret = secret
        self.max_credits = max_credits
        self.resolution = resolution
        self.spent_estimate = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        estimated = estimate_wan3_credits(request.duration_seconds, resolution=self.resolution)
        if self.spent_estimate + estimated > self.max_credits:
            raise ProofCutError("credit ceiling would be exceeded")
        try:
            from runwayml import RunwayML, TaskFailedError
        except ImportError as exc:
            raise ProofCutError("runwayml SDK not installed; install proofcut[runway]") from exc
        client = RunwayML(api_key=self.secret)
        try:
            # Current Runway docs expose text-to-video through image_to_video.create with prompt_image omitted.
            # WAN 3.0 pricing is deterministic by duration + resolution; generation never receives evidence text.
            kwargs = {
                "model": "wan3",
                "prompt_text": request.prompt,
                "duration": request.duration_seconds,
                "resolution": self.resolution,
            }
            task = client.image_to_video.create(**kwargs).wait_for_task_output()
        except TaskFailedError as exc:
            self.spent_estimate += estimated
            task_id = getattr(getattr(exc, "task_details", None), "id", None)
            return GenerationResult(request.shot_id, "runway", "FAILED", None, task_id, estimated)
        self.spent_estimate += estimated
        output = getattr(task, "output", None) or []
        task_id = getattr(task, "id", None)
        return GenerationResult(request.shot_id, "runway", "SUCCEEDED", output[0] if output else None, task_id, estimated)
