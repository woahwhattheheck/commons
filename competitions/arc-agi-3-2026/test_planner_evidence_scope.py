from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import unittest

import _sage_symbolic_planner_core as predecessor
from sage_core import ActionToken as SageActionToken, Observation as SageObservation, Transition as SageTransition
from sage_symbolic_planner import (
    OBSERVATION_IDENTITY_POLICY,
    PLANNER_SCHEMA,
    PLANNER_VERSION,
    REACHABILITY_POLICY,
    ReceiptVerificationError,
    SageEvidenceAdapter,
    observation_digest,
    plan,
    verify_receipt,
)


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
    def __init__(self, transitions=()):
        self.transitions = list(transitions)
        self.seen = {}

    def novelty(self, obs):
        return 1.0 / (1 + self.seen.get(observation_digest(obs), 0))


class ExactEvidenceScopeTests(unittest.TestCase):
    def candidates(self, obs):
        return tuple(Token(name) for name in sorted(obs.available_actions))

    def test_real_observation_temporal_history_is_part_of_exact_identity(self):
        settled = ((0, 1),)
        before_a = SageObservation(
            frames=(((0, 0),), settled),
            available_actions=("ACTION1",),
        )
        current_b = SageObservation(
            frames=(((1, 1),), settled),
            available_actions=("ACTION1",),
        )
        win = SageObservation(
            frames=(settled, ((1, 0),)),
            available_actions=("ACTION1",),
            state="WIN",
            levels_completed=1,
        )
        action = SageActionToken("ACTION1")
        transition = SageTransition.build(before_a, action, win)

        # This is the exact predecessor killer: the preserved v1 core aliases the
        # two real SAGE observations because their final frame/metadata match.
        self.assertEqual(predecessor.observation_digest(before_a), predecessor.observation_digest(current_b))
        self.assertNotEqual(observation_digest(before_a), observation_digest(current_b))

        adapter = SageEvidenceAdapter(
            FakeModel([transition]),
            current_b,
            candidate_factory=lambda _obs: (action,),
        )
        hypothesis, = adapter.hypotheses(adapter.root_state())
        self.assertEqual(hypothesis.evidence_scope, "SCENE")
        self.assertEqual(hypothesis.terminal, "NOT_FINISHED")
        self.assertEqual(hypothesis.progress, 0)
        self.assertEqual(hypothesis.novelty_bps, 0)
        self.assertIsNone(hypothesis.successor_observation_digest)
        self.assertIsNone(hypothesis.successor_observation)

    def test_modal_exact_win_cannot_determinize_conflicting_exact_outcome(self):
        current = Obs(((0, 1),), ("ACTION1",))
        win = Obs(((1, 0),), ("ACTION1",), state="WIN", levels_completed=1)
        other = Obs(((2, 0),), ("ACTION1",))
        win_effect = Effect(h("win"), 1, 1, "WIN")
        other_effect = Effect(h("other"), 1, 0, "NOT_FINISHED")
        transitions = [
            Transition(current, Token("ACTION1"), win, win_effect),
            Transition(current, Token("ACTION1"), win, win_effect),
            Transition(current, Token("ACTION1"), other, other_effect),
        ]
        adapter = SageEvidenceAdapter(FakeModel(transitions), current, candidate_factory=self.candidates)
        hypothesis, = adapter.hypotheses(adapter.root_state())

        self.assertEqual(hypothesis.evidence_scope, "EXACT")
        self.assertEqual(hypothesis.support, 2)
        self.assertEqual(hypothesis.total, 3)
        self.assertEqual(hypothesis.progress, 0)
        self.assertEqual(hypothesis.terminal, "NOT_FINISHED")
        self.assertEqual(hypothesis.novelty_bps, 0)
        self.assertIsNone(hypothesis.successor_observation_digest)
        self.assertIsNone(hypothesis.successor_observation)

    def test_same_effect_but_conflicting_exact_successor_stays_fully_abstract(self):
        current = Obs(((3, 1),), ("ACTION1",))
        after_a = Obs(((4, 1),), ("ACTION1",), levels_completed=1)
        after_b = Obs(((5, 1),), ("ACTION1",), levels_completed=1)
        effect = Effect(h("same-effect"), 1, 1, "NOT_FINISHED")
        adapter = SageEvidenceAdapter(FakeModel([
            Transition(current, Token("ACTION1"), after_a, effect),
            Transition(current, Token("ACTION1"), after_b, effect),
        ]), current, candidate_factory=self.candidates)
        hypothesis, = adapter.hypotheses(adapter.root_state())

        self.assertEqual(hypothesis.evidence_scope, "EXACT")
        self.assertEqual(hypothesis.progress, 0)
        self.assertEqual(hypothesis.terminal, "NOT_FINISHED")
        self.assertEqual(hypothesis.novelty_bps, 0)
        self.assertIsNone(hypothesis.successor_observation)

    def test_unresolved_successor_has_no_inferred_future_action_space(self):
        current = Obs(((0, 1), (0, 0)), ("ACTION1", "ACTION2"))
        foreign = Obs(((1, 0), (0, 0)), ("ACTION1", "ACTION2"))
        foreign_after = Obs(((0, 0), (1, 0)), ("ACTION1", "ACTION2"), state="WIN", levels_completed=1)
        transition = Transition(
            foreign,
            Token("ACTION1"),
            foreign_after,
            Effect(h("foreign"), 1, 1, "WIN"),
        )
        adapter = SageEvidenceAdapter(FakeModel([transition]), current, candidate_factory=self.candidates)
        root = adapter.root_state()
        hypothesis = next(h for h in adapter.hypotheses(root) if h.action_key == "ACTION1")
        unresolved = adapter.simulate(root, hypothesis)

        self.assertIsNone(unresolved.observation)
        self.assertIsNone(unresolved.observation_digest)
        self.assertEqual(unresolved.available_actions, ())
        self.assertEqual(adapter.hypotheses(unresolved), ())

    def test_full_action_token_prevents_coordinate_alias_from_becoming_exact(self):
        current = Obs(((7, 0),), ("ACTION1",))
        foreign_after = Obs(((7, 1),), ("ACTION1",), state="WIN", levels_completed=1)
        transition = Transition(
            current,
            Token("ACTION1", 2, 2),
            foreign_after,
            Effect(h("coord-win"), 1, 1, "WIN"),
        )

        def candidate_factory(_obs):
            return (Token("ACTION1", 1, 1),)

        adapter = SageEvidenceAdapter(FakeModel([transition]), current, candidate_factory=candidate_factory)
        hypothesis, = adapter.hypotheses(adapter.root_state())
        self.assertEqual(hypothesis.action_key, "ACTION1@1,1")
        self.assertEqual(hypothesis.evidence_scope, "SCENE")
        self.assertEqual(hypothesis.terminal, "NOT_FINISHED")
        self.assertEqual(hypothesis.progress, 0)
        self.assertIsNone(hypothesis.successor_observation)

    def test_unanimous_exact_multi_step_path_remains_reachable(self):
        start = Obs(((1, 0),), ("ACTION1",))
        middle = Obs(((1, 1),), ("ACTION2",), levels_completed=1)
        win = Obs(((2, 2),), ("ACTION3",), state="WIN", levels_completed=2)
        transitions = [
            Transition(start, Token("ACTION1"), middle, Effect(h("step1"), 1, 1)),
            Transition(start, Token("ACTION1"), middle, Effect(h("step1"), 1, 1)),
            Transition(middle, Token("ACTION2"), win, Effect(h("step2"), 1, 1, "WIN")),
        ]
        adapter = SageEvidenceAdapter(FakeModel(transitions), start, candidate_factory=self.candidates)
        decision = plan(adapter, actions_left=2)
        self.assertEqual(decision.selected_prefix, ("ACTION1", "ACTION2"))
        self.assertEqual(decision.receipt["selected_progress"], 2)

    def test_receipt_v3_rejects_older_semantic_replay(self):
        current = Obs(((0, 1),), ("ACTION1",))
        after = Obs(((1, 0),), ("ACTION1",))
        transition = Transition(current, Token("ACTION1"), after, Effect(h("move"), 1))
        adapter = SageEvidenceAdapter(FakeModel([transition]), current, candidate_factory=self.candidates)
        decision = plan(adapter, actions_left=1)

        self.assertEqual(OBSERVATION_IDENTITY_POLICY, "ordered-animation-frames-plus-settled-metadata/v1")
        self.assertEqual(REACHABILITY_POLICY, "exact-predecessor-full-animation-unanimous-concrete-reachability/v3")
        self.assertEqual(PLANNER_SCHEMA, "commons.arc3-sage-symbolic-planner/v3")
        self.assertEqual(PLANNER_VERSION, 3)
        self.assertEqual(verify_receipt(adapter, decision.receipt, actions_left=1), "VERIFIED_OFFLINE")

        for legacy_schema, legacy_version in (
            (predecessor.PLANNER_SCHEMA, predecessor.PLANNER_VERSION),
            ("commons.arc3-sage-symbolic-planner/v2", 2),
        ):
            legacy = {key: value for key, value in decision.receipt.items() if key != "receipt_sha256"}
            legacy["schema"] = legacy_schema
            legacy["planner_version"] = legacy_version
            legacy = predecessor._seal_receipt(legacy)
            with self.assertRaises(ReceiptVerificationError):
                verify_receipt(adapter, legacy, actions_left=1)


if __name__ == "__main__":
    unittest.main()
