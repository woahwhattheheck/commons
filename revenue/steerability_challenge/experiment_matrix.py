"""Deterministic pre-registration experiment matrix for the Steerability Challenge."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

TOOLKIT_COMMIT = "f1d8b5fd6d9ed15d506f9445a93d55cb5c5b07df"
GUIDE_VERSION = "v0.2"
COMPETITION_MODELS = (
    "google/gemma-4-31B-it",
    "ibm-granite/granite-4.2-30b",
    "Qwen/Qwen3.8-27B",
)


@dataclass(frozen=True)
class ExperimentFamily:
    id: str
    track: str
    controls: tuple[str, ...]
    hypothesis: str
    sweeps: tuple[str, ...]
    public_basis: str
    compute_tier: str
    starter_kit_required: bool = True


FAMILIES: tuple[ExperimentFamily, ...] = (
    ExperimentFamily(
        id="bb-prompt-only",
        track="black-box",
        controls=("input",),
        hypothesis=(
            "A model-agnostic honesty instruction can improve dishonest behavior "
            "with minimal capability regression and establishes the cheapest floor."
        ),
        sweeps=("instruction wording", "instruction placement"),
        public_basis="Black-box controls may operate without weights, activations, or logits.",
        compute_tier="low",
    ),
    ExperimentFamily(
        id="bb-prompt-plus-search",
        track="black-box",
        controls=("input", "output"),
        hypothesis=(
            "Composing complementary prompt and output controls can dominate a "
            "single-control black-box baseline without requiring internals."
        ),
        sweeps=("candidate count", "output selection budget", "instruction wording"),
        public_basis="Guide §6.1 encourages pipelines with more than one control type.",
        compute_tier="medium",
    ),
    ExperimentFamily(
        id="wb-response-token-activation",
        track="white-box",
        controls=("state",),
        hypothesis=(
            "Response-token-only activation steering reduces the capability cost "
            "of honesty directions, especially for Gemma-family activation outliers."
        ),
        sweeps=("layer/fractional depth", "multiplier", "response-token scope"),
        public_basis=(
            "Guide §6.2 recommends layer sweeps and response-token/gated steering "
            "for Gemma-family large activations."
        ),
        compute_tier="high",
    ),
    ExperimentFamily(
        id="wb-gated-composition",
        track="white-box",
        controls=("input", "state"),
        hypothesis=(
            "A weak always-on honesty instruction plus a gated state intervention "
            "can reserve stronger steering for evidence-rich prompts and lower side effects."
        ),
        sweeps=("gate threshold", "layer", "state multiplier", "instruction wording"),
        public_basis="Guide §6.1 encourages complementary controls; hidden states may inform behavior.",
        compute_tier="high",
    ),
    ExperimentFamily(
        id="wb-contrastive-scenario-quality",
        track="white-box",
        controls=("state",),
        hypothesis=(
            "Scenario-diverse, label-verified contrastive examples matter more than "
            "raw sample count for an OOD honesty direction."
        ),
        sweeps=("scenario family", "10/20/40 pairs", "label-filter strictness"),
        public_basis=(
            "Guide §6.2 says contrastive type/quality matters strongly and notes "
            "directions can be extracted from about ten pairs."
        ),
        compute_tier="high",
    ),
    ExperimentFamily(
        id="open-weight-adapter",
        track="open",
        controls=("structure", "input"),
        hypothesis=(
            "A small trained structural adapter can exceed state-only steering, "
            "but should be attempted only after cheaper tracks establish a strong floor."
        ),
        sweeps=("adapter rank", "training mix", "honesty prompt"),
        public_basis="Open track may modify weights; competition rewards methodology across all models.",
        compute_tier="very-high",
    ),
)


def experiment_matrix() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "guide_version": GUIDE_VERSION,
        "toolkit_commit": TOOLKIT_COMMIT,
        "competition_models": list(COMPETITION_MODELS),
        "families": [asdict(family) for family in FAMILIES],
        "execution_order": [family.id for family in FAMILIES],
        "gates": [
            "Do not infer official score from local proxy metrics.",
            "Use the same pipeline structure across all three competition models; vary trained artifacts only.",
            "Preserve per-seed raw evaluation evidence before selecting a recipe.",
            "Require Starter Kit validation before any submission upload.",
            "Re-read the live guide before registration, evaluation intervals, and final upload.",
        ],
    }
