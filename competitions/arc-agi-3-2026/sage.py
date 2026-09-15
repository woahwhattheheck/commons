"""Public SAGE API assembled from dependency-free research modules."""
from __future__ import annotations

from sage_core import *  # re-export stable research primitives
from sage_model import EffectStats, ScenePrecondition, Skill, SkillLibrary, WorldModel
from sage_policy import Decision, Policy

class SAGEAgent:
    """Stateful agent facade used by both the mock benchmark and official adapter."""

    def __init__(self) -> None:
        self.model = WorldModel()
        self.skills = SkillLibrary()
        self.policy = Policy(self.model, self.skills)
        self.trace: list[Transition] = []

    def decide(self, obs: Observation, *, actions_left: int) -> Decision:
        return self.policy.choose(obs, actions_left=actions_left)

    def learn(self, before: Observation, decision: Decision, after: Observation) -> Transition:
        transition = Transition.build(before, decision.action, after)
        self.model.observe(transition)
        self.policy.record_transition(transition)
        self.trace.append(transition)
        if transition.effect.level_delta > 0 or after.state == "WIN":
            self.skills.learn_success_suffix(self.trace)
        return transition

    def reset_episode(self, *, preserve_knowledge: bool = True) -> None:
        self.trace.clear()
        self.policy._last_actions.clear()
        if not preserve_knowledge:
            self.model = WorldModel()
            self.skills = SkillLibrary()
            self.policy = Policy(self.model, self.skills)
