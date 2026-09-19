#!/usr/bin/env python3
"""Deterministic 320-case falsifier panel for SAGE reachability authority.

This is synthetic offline evidence only. It does not call ARC, accept rules,
submit anything, spend provider actions, or estimate public/private game score.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from sage_symbolic_planner import REACHABILITY_POLICY, SageEvidenceAdapter, observation_digest


def h(text: str) -> str:
    return sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Token:
    name: str
    x: int | None = None
    y: int | None = None

    @property
    def key(self):
        return self.name if self.x is None else f"{self.name}@{self.x},{self.y}"


@dataclass(frozen=True)
class Obs:
    frame: tuple[tuple[int, ...], ...]
    available_actions: tuple[str, ...]
    state: str = "NOT_FINISHED"
    levels_completed: int = 0
    win_levels: int = 0


@dataclass(frozen=True)
class Effect:
    digest: str
    changed_count: int = 0
    level_delta: int = 0
    terminal: str = "NOT_FINISHED"


@dataclass(frozen=True)
class Transition:
    before: Obs
    action: Token
    after: Obs
    effect: Effect


class FakeModel:
    def __init__(self, transitions):
        self.transitions = list(transitions)
        self.seen = {}

    def novelty(self, obs):
        return 1.0 / (1 + self.seen.get(observation_digest(obs), 0))


def candidates(obs):
    return tuple(Token(name) for name in sorted(obs.available_actions))


def build_case(seed: int, family: str):
    a = (seed * 17 + 3) % 240
    b = (seed * 29 + 11) % 240
    if a == b:
        b = (b + 1) % 240
    current = Obs(((a, b),), ("ACTION1",))

    if family == "SCENE_FOREIGN_WIN":
        foreign = Obs(((b, a),), ("ACTION1",))
        after = Obs(((a, (b + 1) % 256),), ("ACTION1",), state="WIN", levels_completed=1)
        transitions = [Transition(foreign, Token("ACTION1"), after, Effect(h(f"scene:{seed}"), 1, 1, "WIN"))]
        return SageEvidenceAdapter(FakeModel(transitions), current, candidate_factory=candidates)

    if family == "GLOBAL_FOREIGN_WIN":
        foreign = Obs((((a + 7) % 256, (b + 13) % 256),), ("ACTION1",))
        after = Obs((((a + 1) % 256, b),), ("ACTION1",), state="WIN", levels_completed=1)
        transitions = [Transition(foreign, Token("ACTION1"), after, Effect(h(f"global:{seed}"), 1, 1, "WIN"))]
        return SageEvidenceAdapter(FakeModel(transitions), current, candidate_factory=candidates)

    if family == "EXACT_MODAL_WIN":
        win = Obs((((a + 1) % 256, b),), ("ACTION1",), state="WIN", levels_completed=1)
        other = Obs(((a, (b + 1) % 256),), ("ACTION1",))
        win_effect = Effect(h(f"modal-win:{seed}"), 1, 1, "WIN")
        other_effect = Effect(h(f"modal-other:{seed}"), 1, 0, "NOT_FINISHED")
        transitions = [
            Transition(current, Token("ACTION1"), win, win_effect),
            Transition(current, Token("ACTION1"), win, win_effect),
            Transition(current, Token("ACTION1"), other, other_effect),
        ]
        return SageEvidenceAdapter(FakeModel(transitions), current, candidate_factory=candidates)

    if family == "EXACT_SUCCESSOR_SPLIT":
        after_a = Obs((((a + 1) % 256, b),), ("ACTION1",), levels_completed=1)
        after_b = Obs(((a, (b + 1) % 256),), ("ACTION1",), levels_completed=1)
        effect = Effect(h(f"split:{seed}"), 1, 1, "NOT_FINISHED")
        transitions = [
            Transition(current, Token("ACTION1"), after_a, effect),
            Transition(current, Token("ACTION1"), after_b, effect),
        ]
        return SageEvidenceAdapter(FakeModel(transitions), current, candidate_factory=candidates)

    if family == "COORDINATE_ALIAS_WIN":
        after = Obs((((a + 1) % 256, b),), ("ACTION1",), state="WIN", levels_completed=1)
        transitions = [
            Transition(current, Token("ACTION1", 2, 2), after, Effect(h(f"coord:{seed}"), 1, 1, "WIN")),
        ]
        return SageEvidenceAdapter(
            FakeModel(transitions),
            current,
            candidate_factory=lambda _obs: (Token("ACTION1", 1, 1),),
        )

    raise ValueError(f"unknown family: {family}")


def main() -> None:
    families = (
        "SCENE_FOREIGN_WIN",
        "GLOBAL_FOREIGN_WIN",
        "EXACT_MODAL_WIN",
        "EXACT_SUCCESSOR_SPLIT",
        "COORDINATE_ALIAS_WIN",
    )
    total = 0
    concrete_violations = 0
    authority_violations = 0
    continuation_violations = 0
    scopes: dict[str, int] = {}

    for seed in range(64):
        for family in families:
            adapter = build_case(seed, family)
            root = adapter.root_state()
            hypothesis, = adapter.hypotheses(root)
            total += 1
            scopes[hypothesis.evidence_scope] = scopes.get(hypothesis.evidence_scope, 0) + 1
            if hypothesis.successor_observation is not None or hypothesis.successor_observation_digest is not None:
                concrete_violations += 1
            if hypothesis.terminal != "NOT_FINISHED" or hypothesis.progress != 0 or hypothesis.novelty_bps != 0:
                authority_violations += 1
            unresolved = adapter.simulate(root, hypothesis)
            if unresolved.available_actions or adapter.hypotheses(unresolved):
                continuation_violations += 1

    receipt = {
        "schema": "commons.arc3-sage-evidence-scope-falsifier/v1",
        "policy": REACHABILITY_POLICY,
        "cases": total,
        "families": list(families),
        "scope_counts": dict(sorted(scopes.items())),
        "unsupported_concrete_successors": concrete_violations,
        "unsupported_terminal_progress_or_novelty": authority_violations,
        "unsupported_abstract_continuations": continuation_violations,
        "authority": {
            "arc_account_action": False,
            "submission": False,
            "provider_call": False,
            "leaderboard_or_prize_claim": False,
        },
    }
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    if total != 320 or concrete_violations or authority_violations or continuation_violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
