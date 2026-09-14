"""Deterministic mock-only drivers for the four SAGE hypotheses.

Run from the ARC3 competition root (or anywhere after it is added to ``sys.path``).
No public-game or leaderboard claims can be produced by this driver.
"""
from __future__ import annotations

from hashlib import sha256
import json
from random import Random
from typing import Callable

from .core import ExperimentSpec, TrialPair, compile_report, canonical_json


def _imports():
    # Delayed import keeps the evidence compiler independently testable/packagable.
    from mock_env import SwitchDoorEnv
    from sage import ActionToken, Observation, SAGEAgent
    return SwitchDoorEnv, ActionToken, Observation, SAGEAgent


def _obs_digest(obs: object) -> str:
    frames = getattr(obs, "frames")
    value = [[[int(v) for v in row] for row in frame] for frame in frames]
    return sha256(canonical_json(value).encode()).hexdigest()


def _run_agent(seed: int, *, budget: int, preserve_from=None) -> tuple[int, bool, object]:
    SwitchDoorEnv, _, _, SAGEAgent = _imports()
    env = SwitchDoorEnv(seed)
    agent = preserve_from if preserve_from is not None else SAGEAgent()
    if preserve_from is not None:
        agent.reset_episode(preserve_knowledge=True)
    obs = env.reset()
    for step in range(budget):
        if obs.state != "NOT_FINISHED":
            break
        decision = agent.decide(obs, actions_left=budget - step)
        after = env.step(decision.action)
        agent.learn(obs, decision, after)
        obs = after
    return len(agent.trace), obs.state == "WIN", agent


def h1_animation_pairs(seeds: range, *, budget: int, source_revision: str) -> tuple[ExperimentSpec, tuple[TrialPair, ...]]:
    """Measure temporal evidence retained by full observations vs settled-frame projection.

    We derive a state-changing ACTION6 candidate from policy output rather than hard-code a
    mock coordinate.  Both arms observe the same transition; only evidence projection differs.
    """
    SwitchDoorEnv, _, Observation, SAGEAgent = _imports()
    pairs = []
    for seed in seeds:
        env = SwitchDoorEnv(seed)
        agent = SAGEAgent()
        before = env.reset()
        obs = before
        best = obs
        for step in range(budget):
            if obs.state != "NOT_FINISHED":
                break
            decision = agent.decide(obs, actions_left=budget - step)
            after = env.step(decision.action)
            agent.learn(obs, decision, after)
            if len(after.frames) > len(best.frames):
                best = after
            obs = after
        settled = Observation(
            frames=(best.frames[-1],), available_actions=best.available_actions,
            state=best.state, levels_completed=best.levels_completed, win_levels=best.win_levels,
        )
        pairs.append(TrialPair(
            seed=seed,
            baseline_metrics={"temporal_frames": len(settled.frames)},
            candidate_metrics={"temporal_frames": len(best.frames)},
            observation_digest=_obs_digest(before),
        ))
    spec = ExperimentSpec("H1", "full animation retention", "settled-frame-only", "all-frames",
                          "temporal_frames", True, "mock", budget, source_revision,
                          {"control": "same transition; evidence projection only"})
    return spec, tuple(pairs)


def h2_information_gain_pairs(seeds: range, *, budget: int, source_revision: str) -> tuple[ExperimentSpec, tuple[TrialPair, ...]]:
    SwitchDoorEnv, _, _, SAGEAgent = _imports()
    pairs = []
    for seed in seeds:
        sage_actions, sage_won, _ = _run_agent(seed, budget=budget)
        env = SwitchDoorEnv(seed)
        candidate_source = SAGEAgent()
        obs = env.reset()
        rng = Random(seed ^ 0x5A6E)
        random_actions = 0
        while random_actions < budget and obs.state == "NOT_FINISHED":
            actions = candidate_source.policy.candidate_actions(obs)
            action = actions[rng.randrange(len(actions))]
            obs = env.step(action)
            random_actions += 1
        # Score guarantees equal-budget comparability and penalizes non-completion.
        baseline_score = (budget - random_actions + 1) if obs.state == "WIN" else 0
        candidate_score = (budget - sage_actions + 1) if sage_won else 0
        pairs.append(TrialPair(seed, {"budget_efficiency": baseline_score},
                               {"budget_efficiency": candidate_score}, _obs_digest(env.reset())))
    spec = ExperimentSpec("H2", "information-gain probing", "seeded-uniform", "SAGE-policy",
                          "budget_efficiency", True, "mock", budget, source_revision,
                          {"uniform_seed_xor": "0x5A6E", "noncompletion_score": 0})
    return spec, tuple(pairs)


def h3_skill_transfer_pairs(seeds: range, *, budget: int, source_revision: str) -> tuple[ExperimentSpec, tuple[TrialPair, ...]]:
    pairs = []
    for seed in seeds:
        first_actions, first_won, trained = _run_agent(seed, budget=budget)
        reset_actions, reset_won, _ = _run_agent(seed, budget=budget)
        transfer_actions, transfer_won, _ = _run_agent(seed, budget=budget, preserve_from=trained)
        baseline_score = (budget - reset_actions + 1) if reset_won else 0
        candidate_score = (budget - transfer_actions + 1) if transfer_won else 0
        pairs.append(TrialPair(seed, {"second_episode_efficiency": baseline_score},
                               {"second_episode_efficiency": candidate_score},
                               sha256(f"seed:{seed}:first:{first_actions}:{int(first_won)}".encode()).hexdigest()))
    spec = ExperimentSpec("H3", "cross-episode skill transfer", "knowledge-reset", "preserve-knowledge",
                          "second_episode_efficiency", True, "mock", budget, source_revision,
                          {"same_seed_second_episode": True})
    return spec, tuple(pairs)


def h4_coordinate_reduction_pairs(seeds: range, *, budget: int, source_revision: str) -> tuple[ExperimentSpec, tuple[TrialPair, ...]]:
    SwitchDoorEnv, _, _, SAGEAgent = _imports()
    pairs = []
    for seed in seeds:
        env = SwitchDoorEnv(seed)
        obs = env.reset()
        agent = SAGEAgent()
        reduced = sum(1 for a in agent.policy.candidate_actions(obs) if a.name == "ACTION6")
        h, w = obs.shape
        full = h * w
        pairs.append(TrialPair(seed, {"coordinate_reduction": 0},
                               {"coordinate_reduction": full - reduced}, _obs_digest(obs)))
    spec = ExperimentSpec("H4", "coordinate candidate reduction", "all-grid", "component-candidates",
                          "coordinate_reduction", True, "mock", budget, source_revision,
                          {"baseline": "all grid cells", "candidate": "centroid/bbox/corners+center"})
    return spec, tuple(pairs)


def run_all(*, seeds: int = 12, budget: int = 80, source_revision: str = "UNBOUND") -> dict[str, object]:
    if type(seeds) is not int or not 1 <= seeds <= 1000:
        raise ValueError("seeds must be an exact int in [1,1000]")
    if source_revision == "UNBOUND":
        raise ValueError("source_revision must be explicitly bound")
    builders: tuple[Callable[..., tuple[ExperimentSpec, tuple[TrialPair, ...]]], ...] = (
        h1_animation_pairs, h2_information_gain_pairs, h3_skill_transfer_pairs, h4_coordinate_reduction_pairs,
    )
    reports = [compile_report(*builder(range(seeds), budget=budget, source_revision=source_revision)) for builder in builders]
    return {
        "schema": "arc3-sage-ablation-suite/v1",
        "evidence_class": "mock",
        "reports": reports,
        "suite_sha256": sha256(canonical_json(reports).encode()).hexdigest(),
        "claim_ceiling": "MOCK_EVIDENCE_ONLY_NO_KAGGLE_SCORE",
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    print(json.dumps(run_all(seeds=args.seeds, budget=args.budget, source_revision=args.source_revision), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
