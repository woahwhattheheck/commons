"""Public ARC3 SAGE planner facade with evidence-conditioned reachability.

The landed planner implementation is preserved byte-for-byte in the private
``_sage_symbolic_planner_core`` module. This facade narrows only the evidence
authority boundary:

* SCENE/GLOBAL fallback evidence may inform abstract effect/confidence/risk,
  but never a concrete successor, terminal state, progress or successor novelty.
* EXACT evidence carries a concrete future only when every transition matching
  the exact predecessor and full action token agrees on successor/progress/
  terminal semantics.
* unresolved abstract states have no inferred successor action space, so
  lookahead stops at the evidence boundary.
"""
from __future__ import annotations

from dataclasses import replace as _replace

try:
    from . import _sage_symbolic_planner_core as _core
except ImportError:  # direct module execution from the competition directory
    import _sage_symbolic_planner_core as _core  # type: ignore

REACHABILITY_POLICY = "exact-predecessor-unanimous-concrete-reachability/v2"
PLANNER_SCHEMA = "commons.arc3-sage-symbolic-planner/v2"
PLANNER_VERSION = 2

# Preserve the historical module surface. Keep the old implementation private
# and byte-exact; SageEvidenceAdapter, plan and verify_receipt are replaced below.
for _name, _value in vars(_core).items():
    if _name.startswith("__") or _name in {
        "SageEvidenceAdapter", "plan", "verify_receipt", "PLANNER_SCHEMA", "PLANNER_VERSION"
    }:
        continue
    globals()[_name] = _value
    if getattr(_value, "__module__", None) == _core.__name__:
        try:
            _value.__module__ = __name__
        except (AttributeError, TypeError):
            pass

_BaseSageEvidenceAdapter = _core.SageEvidenceAdapter


def _strip_concrete_reachability(hypothesis):
    return _replace(
        hypothesis,
        progress=0,
        terminal="NOT_FINISHED",
        novelty_bps=0,
        successor_observation_digest=None,
        successor_observation=None,
    )


class SageEvidenceAdapter(_BaseSageEvidenceAdapter):
    """SAGE adapter with exact, unanimous concrete-reachability authority."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Receipts bind evidence *and* the authority policy used to interpret it.
        self._model_digest = _core._digest({
            "schema": "sage-evidence-policy/v3",
            "evidence_digest": self._model_digest,
            "reachability_policy": REACHABILITY_POLICY,
        })

    def _resolved_observation(self, state):
        obs = state.observation
        if obs is None:
            obs = self._observations.get(state.observation_digest or "")
        return obs

    def hypotheses(self, state):
        obs = self._resolved_observation(state)
        if obs is None:
            # An abstract effect state is an evidence boundary, not a license to
            # reuse the predecessor action space and invent a deeper future.
            return ()

        hypotheses = super().hypotheses(state)
        hardened = []
        for hypothesis in hypotheses:
            strip = hypothesis.evidence_scope in {"SCENE", "GLOBAL"}
            if hypothesis.evidence_scope == "EXACT":
                scope, rows = self._evidence_rows(obs, hypothesis.action)
                if scope != "EXACT":
                    raise RuntimeError("internal error: exact hypothesis lost exact evidence rows")
                concrete_outcomes = {
                    (row["after"], row["progress"], row["terminal"])
                    for row in rows
                }
                # Modal agreement is useful scoring evidence but not reachability
                # authority. Every exact matching observation must agree before
                # a concrete successor/progress/terminal can enter the tree.
                strip = len(concrete_outcomes) != 1
            if strip:
                hypothesis = _strip_concrete_reachability(hypothesis)
            hardened.append(hypothesis)
        return tuple(hardened)

    def simulate(self, state, hypothesis):
        successor = super().simulate(state, hypothesis)
        if successor.observation is not None:
            return successor
        # Keep unresolved states explicitly terminal with respect to lookahead:
        # no future action space is asserted without concrete observation bytes.
        progress = successor.cumulative_progress
        digest = _core._digest({
            "schema": "sage-abstract-state/v2",
            "parent": state.digest,
            "action": hypothesis.action_key,
            "effect": hypothesis.effect_digest,
            "terminal": successor.terminal,
            "progress": progress,
            "available_actions": [],
            "reachability_policy": REACHABILITY_POLICY,
        })
        return _core.SymbolicState(
            digest=digest,
            available_actions=(),
            terminal=successor.terminal,
            cumulative_progress=progress,
            observation_digest=None,
            observation=None,
        )


def _v2_receipt_from_core(receipt):
    unsealed = {key: receipt[key] for key in receipt if key != "receipt_sha256"}
    unsealed["schema"] = PLANNER_SCHEMA
    unsealed["planner_version"] = PLANNER_VERSION
    return _core._seal_receipt(unsealed)


def plan(
    adapter,
    *,
    actions_left,
    budget=_core.PlannerBudget(),
    weights=_core.ScoreWeights(),
):
    """Run the bounded planner and emit a v2 policy-bound receipt."""
    decision = _core.plan(
        adapter,
        actions_left=actions_left,
        budget=budget,
        weights=weights,
    )
    receipt = _v2_receipt_from_core(decision.receipt)
    return _core.PlanDecision(
        decision.first_action,
        decision.selected_prefix,
        decision.simulated_nodes,
        receipt,
    )


def verify_receipt(
    adapter,
    receipt,
    *,
    actions_left,
    budget=_core.PlannerBudget(),
    weights=_core.ScoreWeights(),
):
    """Recompute a v2 receipt and reject tamper, drift or v1 semantic replay."""
    if not isinstance(receipt, dict) or frozenset(receipt) != _core.RECEIPT_KEYS:
        raise _core.ReceiptVerificationError("receipt field set mismatch")
    supplied_digest = receipt.get("receipt_sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise _core.ReceiptVerificationError("receipt digest malformed")
    unsealed = {key: receipt[key] for key in receipt if key != "receipt_sha256"}
    expected_digest = _core.sha256(_core._canonical_bytes(unsealed)).hexdigest()
    if supplied_digest != expected_digest:
        raise _core.ReceiptVerificationError("receipt digest mismatch")
    if receipt.get("schema") != PLANNER_SCHEMA or receipt.get("planner_version") != PLANNER_VERSION:
        raise _core.ReceiptVerificationError("receipt schema/version mismatch")
    recomputed = plan(
        adapter,
        actions_left=actions_left,
        budget=budget,
        weights=weights,
    ).receipt
    if _core._canonical_bytes(recomputed) != _core._canonical_bytes(receipt):
        raise _core.ReceiptVerificationError(
            "receipt no longer matches state/model/budget/policy"
        )
    return "VERIFIED_OFFLINE"
