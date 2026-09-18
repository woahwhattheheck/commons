"""Public ARC3 SAGE planner facade with predecessor-conditioned reachability.

The landed planner implementation is preserved byte-for-byte in the private
``_sage_symbolic_planner_core`` module.  This facade narrows only the evidence
authority boundary: SCENE/GLOBAL fallback evidence may inform abstract effect,
confidence, changed/risk scoring, but it may not assert that another
predecessor's concrete successor, terminal state, level progress, or
successor-derived novelty is reachable from the state being planned.
"""
from __future__ import annotations

from dataclasses import replace as _replace

try:
    from . import _sage_symbolic_planner_core as _core
except ImportError:  # direct module execution from the competition directory
    import _sage_symbolic_planner_core as _core  # type: ignore

REACHABILITY_POLICY = "exact-predecessor-concrete-reachability/v1"

# Preserve the historical module surface.  Keep the old implementation private
# and byte-exact; only SageEvidenceAdapter is replaced below.
for _name, _value in vars(_core).items():
    if _name.startswith("__") or _name == "SageEvidenceAdapter":
        continue
    globals()[_name] = _value
    if getattr(_value, "__module__", None) == _core.__name__:
        try:
            _value.__module__ = __name__
        except (AttributeError, TypeError):
            pass

_BaseSageEvidenceAdapter = _core.SageEvidenceAdapter


class SageEvidenceAdapter(_BaseSageEvidenceAdapter):
    """SAGE adapter whose concrete reachability requires exact predecessor evidence."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Receipts bind evidence *and* the authority policy used to interpret it.
        self._model_digest = _core._digest({
            "schema": "sage-evidence-policy/v2",
            "evidence_digest": self._model_digest,
            "reachability_policy": REACHABILITY_POLICY,
        })

    def hypotheses(self, state):
        hypotheses = super().hypotheses(state)
        hardened = []
        for hypothesis in hypotheses:
            if hypothesis.evidence_scope in {"SCENE", "GLOBAL"}:
                # Fallback rows describe how an action behaved under another
                # predecessor.  Preserve abstract effect statistics, but never
                # promote that other predecessor's concrete future into this
                # state's reachable search tree.
                hypothesis = _replace(
                    hypothesis,
                    progress=0,
                    terminal="NOT_FINISHED",
                    novelty_bps=0,
                    successor_observation_digest=None,
                    successor_observation=None,
                )
            hardened.append(hypothesis)
        return tuple(hardened)
