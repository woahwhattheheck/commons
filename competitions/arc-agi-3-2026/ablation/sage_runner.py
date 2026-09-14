"""SAGE-backed deterministic runner for the paired ARC3 ablation ledger."""
from __future__ import annotations

from pathlib import Path
from random import Random
import sys

ARC_ROOT = Path(__file__).resolve().parents[1]
if str(ARC_ROOT) not in sys.path:
    sys.path.insert(0, str(ARC_ROOT))

from mock_env import SwitchDoorEnv  # noqa: E402
from sage import SAGEAgent  # noqa: E402
from sage_core import ActionToken, Observation  # noqa: E402
from sage_policy import Decision, Policy  # noqa: E402

from harness import ExperimentPlan, TrialRecord, Variant  # noqa: E402


class LevelSwitchDoorEnv(SwitchDoorEnv):
    """Same latent controls, translated object layouts across pseudo-levels.

    The environment remains synthetic. Layout changes preserve shape/palette/component
    counts so current ScenePrecondition can attempt transfer without a game-ID table.
    """

    _LAYOUTS = (
        ((1, 5), (2, 3), (3, 2), (5, 1)),
        ((1, 1), (2, 4), (3, 3), (5, 4)),
        ((2, 5), (1, 2), (3, 4), (5, 2)),
    )

    def __init__(self, seed: int, level: int) -> None:
        if type(level) is not int or not 0 <= level < len(self._LAYOUTS):
            raise ValueError("unsupported synthetic level")
        self.level = level
        super().__init__(seed)

    def reset_state(self) -> None:
        agent, switch, door, goal = self._LAYOUTS[self.level]
        self.agent = agent
        self.switch = switch
        self.door = door
        self.goal = goal
        self.door_open = False
        self.actions = 0
        self.levels_completed = self.level
        self.state = "NOT_FINISHED"

    def step(self, action: ActionToken) -> Observation:
        obs = super().step(action)
        if obs.state != "WIN":
            return obs
        # Base mock has one level and writes levels_completed=1 on every win. This
        # translated multi-level wrapper normalizes progress to level+1 so the effect
        # model observes a +1 delta at every synthetic level boundary.
        self.levels_completed = self.level + 1
        return Observation(
            frames=obs.frames,
            available_actions=obs.available_actions,
            state=obs.state,
            levels_completed=self.levels_completed,
            win_levels=len(self._LAYOUTS),
        )


class AllGridPolicy(Policy):
    """One-factor coordinate ablation: expand ACTION6 to every board cell."""

    @staticmethod
    def candidate_actions(obs: Observation) -> tuple[ActionToken, ...]:
        tokens: list[ActionToken] = []
        h, w = obs.shape
        for name in sorted(obs.available_actions):
            if name == "ACTION6":
                tokens.extend(ActionToken(name, x, y) for y in range(h) for x in range(w))
            else:
                tokens.append(ActionToken(name))
        return tuple(tokens)


def _collapse_animation(obs: Observation) -> Observation:
    return Observation(
        frames=(obs.frame,),
        available_actions=obs.available_actions,
        state=obs.state,
        levels_completed=obs.levels_completed,
        win_levels=obs.win_levels,
    )


def _uniform_decision(agent: SAGEAgent, obs: Observation, rng: Random) -> Decision:
    candidates = agent.policy.candidate_actions(obs)
    if not candidates:
        raise ValueError("no candidate actions")
    action = candidates[rng.randrange(len(candidates))]
    return Decision(action, "ABLATION_UNIFORM_RANDOM", 0.0, (("uniform", 1.0),))


def _coordinate_candidates(agent: SAGEAgent, obs: Observation) -> int:
    return sum(token.x is not None for token in agent.policy.candidate_actions(obs))


def run_variant(plan: ExperimentPlan, variant: Variant) -> tuple[TrialRecord, ...]:
    if variant.name not in {v.name for v in plan.variants}:
        raise ValueError("variant is not in plan")
    rows: list[TrialRecord] = []
    for seed in plan.seeds:
        agent = SAGEAgent()
        if variant.coordinate_mode == "all_grid":
            agent.policy = AllGridPolicy(agent.model, agent.skills)
        rng = Random((seed + 1) * 1_000_003 + sum(ord(ch) for ch in variant.name))
        for level in plan.levels:
            if level and not variant.preserve_knowledge:
                agent = SAGEAgent()
                if variant.coordinate_mode == "all_grid":
                    agent.policy = AllGridPolicy(agent.model, agent.skills)
            else:
                agent.reset_episode(preserve_knowledge=True)
            env = LevelSwitchDoorEnv(seed, level)
            obs = env.reset()
            actions = no_effect = animation_frames = coordinate_candidates = coordinate_actions = skill_replays = 0
            first_progress: int | None = None
            for step in range(plan.max_actions):
                if obs.state != "NOT_FINISHED":
                    break
                coordinate_candidates += _coordinate_candidates(agent, obs)
                if variant.action_policy == "uniform_random":
                    decision = _uniform_decision(agent, obs, rng)
                else:
                    decision = agent.decide(obs, actions_left=plan.max_actions - step)
                raw_after = env.step(decision.action)
                observed_after = raw_after if variant.full_animation else _collapse_animation(raw_after)
                transition = agent.learn(obs, decision, observed_after)
                actions += 1
                animation_frames += len(observed_after.frames)
                coordinate_actions += int(decision.action.x is not None)
                skill_replays += int(decision.mode == "SKILL_REPLAY")
                if transition.effect.changed_count == 0 and transition.effect.level_delta <= 0 and observed_after.state == "NOT_FINISHED":
                    no_effect += 1
                if first_progress is None and (transition.effect.level_delta > 0 or observed_after.state == "WIN"):
                    first_progress = actions
                obs = observed_after
            rows.append(
                TrialRecord(
                    variant=variant.name,
                    seed=seed,
                    level=level,
                    won=obs.state == "WIN",
                    actions=actions,
                    no_effect_actions=no_effect,
                    first_progress_action=first_progress,
                    animation_frames_observed=animation_frames,
                    coordinate_candidates_considered=coordinate_candidates,
                    coordinate_actions_taken=coordinate_actions,
                    skill_replays=skill_replays,
                    learned_skills=len(agent.skills.skills),
                )
            )
    return tuple(rows)


def run_plan(plan: ExperimentPlan) -> tuple[TrialRecord, ...]:
    rows: list[TrialRecord] = []
    for variant in plan.variants:
        rows.extend(run_variant(plan, variant))
    return tuple(rows)
