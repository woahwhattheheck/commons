# SPDX-License-Identifier: Apache-2.0
"""TITAN: one production selection, one explicit selected-action consumer."""
from copy import deepcopy
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


deadline = load('_titan_deadline', HERE/'reference/titan-current/deadline_adapter.py')


@dataclass(frozen=True)
class Features:
    consumer: str = 'frozen'
    seed: bool = True
    funding: bool = True
    terminal_route: bool = False
    committed: bool = True
    budget_seconds: float = 1.0
    reserve_seconds: float = 0.01

    def __post_init__(self):
        if self.consumer not in ('frozen', 'ordered', 'parent'):
            raise ValueError('consumer must be frozen, ordered or parent')
        if self.terminal_route and self.consumer != 'frozen':
            raise ValueError('terminal_route is the tested frozen SELL composition')
        if not 0 <= self.reserve_seconds < self.budget_seconds <= 1:
            raise ValueError('invalid action deadline')


class TitanAgent:
    """Construction is lazy so the guard includes the chosen parent's cold start.

    Ordered mode consumes its existing ledger, unit projection and seed funding
    internally. Frozen mode owns its frozen ledger and applies ALDER/JUNIPER once
    after SELL, matching the shipped seed_main order. Ledgers never compose twice.
    """
    def __init__(self, features=None):
        self.features = features or Features()
        self.ready = False
        self.diagnostics = {}
        self.selected = None

    def _initialize(self):
        f = self.features
        self.funding_module = load('_titan_funding', HERE/'reference/titan-current/seed_funding.py')
        selector = self.funding_module.select_seed_queue if f.funding else None
        if f.consumer == 'ordered':
            from integrated_selected import IntegratedSelectedAgent
            self.consumer = IntegratedSelectedAgent(seed=f.seed, committed=f.committed,
                                                   sell=True, seed_queue_selector=selector)
            self.production = self.consumer.production
            self.controller = self.consumer.controller
        else:
            from frozen_selected import FrozenSelected
            self.consumer = FrozenSelected()
            self.controller = self.consumer.controller
            self.production = self.controller
            if f.terminal_route:
                module = load('_titan_terminal_composition', HERE/'reference/titan-current/terminal_composition.py')
                self.production = module.TerminalOwner(self.controller)
                self.consumer.controller = self.production
            budget = load('_titan_seed_budget', HERE/'reference/integrated-selected/alder/seed_budget.py')
            self.seed_budget = budget.SeedBudget(self.controller.R)
        self.ready = True

    def _seed_selected(self, obs, cfg, selected):
        if not self.features.seed or not any(o and o[0] == 'BUY_SEED' for o in selected['market']):
            return selected
        from scheduler import post_units, m
        farm, private = post_units(obs, selected, cfg)
        proposed = self.seed_budget.apply(selected, private['seeds'], int(obs['step']),
                                         self.controller.cur, int(cfg.get('maxMarketOrdersPerTurn', 10)))
        edits = [i for i, (a, b) in enumerate(zip(selected['market'], proposed['market'])) if a != b]
        dependent = any(o and o[0] in ('HIRE', 'BUY_LAND', 'BUY_PRODUCT', 'BUY_ANIMAL')
                        for i in edits for o in selected['market'][i+1:])
        if not dependent:
            return proposed
        if not self.features.funding:
            return selected
        post = deepcopy(obs)
        post['farms'][int(obs['player'])] = farm
        post['private'] = private
        result, report = self.funding_module.select_seed_queue(
            m, post, deepcopy(selected), deepcopy(proposed), deepcopy(cfg))
        self.diagnostics['seed_funding'] = report
        return result

    def transform_selected(self, obs, cfg, selected):
        """Dispatch an already-selected action; never calls a producer."""
        if self.features.consumer == 'ordered':
            return self.consumer.transform(obs, cfg, selected, fallback_action=selected)
        result = (self.consumer.transform(obs, cfg, selected)
                  if self.features.consumer == 'frozen' else deepcopy(selected))
        return self._seed_selected(obs, cfg, result)

    def act(self, observation, configuration=None):
        started = time.perf_counter()
        cfg = dict(configuration or {})
        obs = dict(observation)
        obs['step'] = int(obs['step']) if obs.get('step') is not None else int(obs['day'])*int(cfg.get('turnsPerDay', 24))+int(obs['hour'])
        last = int(cfg.get('episodeSteps', 720))-2
        fallback = (deadline.terminal_liquidation_fallback(obs, cfg) if obs['step'] == last
                    else deadline.legal_pass(obs))
        self.selected = None
        self.diagnostics = {'consumer': self.features.consumer, 'parent_calls': 0}
        stage = 'cold_start'
        seconds = self.features.budget_seconds-self.features.reserve_seconds-(time.perf_counter()-started)
        timer = deadline._DeadlineTimer(max(0.000001, seconds))
        try:
            with timer:
                if not self.ready:
                    self._initialize()
                stage = 'production'
                if self.features.terminal_route:
                    self.production.configuration = cfg
                self.diagnostics['parent_calls'] = 1
                selected = self.production.act(obs)
                self.selected = deepcopy(selected)
                fallback = self.selected
                stage = 'selected_transform'
                output = self.transform_selected(obs, cfg, selected)
                self.diagnostics.update(status='completed', elapsed_seconds=time.perf_counter()-started)
                return output
        except deadline.DeadlineExceeded as error:
            if error is not timer.expired:
                raise
            # Cancellation can interrupt a state mutation. Reconstruct next turn
            # from observed state rather than reuse partially updated ledgers.
            self.ready = False
            self.diagnostics.update(status='deadline_fallback', fallback_stage=stage,
                                    elapsed_seconds=time.perf_counter()-started)
            return deepcopy(fallback)

    __call__ = act
