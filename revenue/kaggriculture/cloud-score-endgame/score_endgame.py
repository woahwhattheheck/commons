# SPDX-License-Identifier: Apache-2.0
"""Absolute terminal win-point consumption of the existing PORT/POLY/T15 APIs.

No optimizer, opponent model, controller or game runner is implemented here.
The virtual zero row is a dominated mathematical embedding, never an action.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import sys

OBJECTIVE = 'absolute_terminal_win_points'


def embedding(table):
    """Embed up to eight real plans in the unchanged nine-row POLY interface."""
    if table.get('schema') != 'titan.terminal-utility.v1':
        raise ValueError('Expected PORT terminal-utility table')
    if table.get('solver_ready') is not True or table.get('terminal') is not True:
        return None
    points = tuple(tuple(F(x) for x in row) for row in table['win_points'])
    n, m = len(points), len(table['scenario_ids'])
    if not 1 <= n <= 8 or not 1 <= m <= 32 or len(table['plan_ids']) != n:
        raise ValueError('Expected 1..8 real plans and 1..32 scenarios')
    if any(len(row) != m or any(x not in (F(0), F(1, 2), F(1)) for x in row)
           for row in points):
        raise ValueError('Expected rectangular exact terminal win points')
    return ((F(0),) * m,) + tuple(tuple(1 + x for x in row) for row in points)


def _consume(table, rows, raw, verify_certificate):
    """Translate a completed existing certificate, retaining the raw result."""
    raw = deepcopy(dict(raw))
    baseline = [F(int(i == 0)) for i in range(len(table['plan_ids']))]
    points = tuple(tuple(F(x) for x in row) for row in table['win_points'])
    baseline_floor = min(points[0])
    result = {'objective': OBJECTIVE, 'solver_called': True,
              'plan_ids': list(table['plan_ids']), 'scenario_ids': list(table['scenario_ids']),
              'raw_solver': raw, 'embedding': {'constant_shift': '1',
                  'virtual_row': 0, 'real_row_indices': list(range(1, len(points) + 1))},
              'baseline_worst_expected_win_points': str(baseline_floor),
              'win_probability': None, 'scenario_probabilities': None,
              'source': deepcopy(table.get('source')),
              'scope': 'Maximin expected terminal points over included scenarios, not a calibrated win probability.'}
    check = verify_certificate(rows, raw)
    result['embedding_certificate'] = deepcopy(check)
    weights = baseline
    result['status'] = 'invalid_certificate'
    if check.get('valid') is True:
        result['status'] = 'solver_incomplete'
        if raw.get('status') == 'optimal' and raw.get('exact') is True:
            supplied = tuple(F(x) for x in raw['weights'])
            if (len(supplied) != len(rows) or supplied[0] != 0
                    or any(w < 0 for w in supplied) or sum(supplied) != 1):
                raise ValueError('A completed optimum must assign zero mass to the dominated virtual row')
            candidate = supplied[1:]
            columns = [sum(candidate[i] * points[i][j] for i in range(len(points)))
                       for j in range(len(points[0]))]
            value, upper = F(raw['value']) - 1, F(raw['upper_bound']) - 1
            if value != min(columns) or value != upper:
                raise ValueError('Translated absolute bounds do not close')
            result['optimal_worst_expected_win_points'] = str(value)
            result['absolute_upper_bound'] = str(upper)
            if value > baseline_floor:
                weights = candidate
                result['status'] = 'selected'
            else:
                result['status'] = 'baseline_optimal'
    columns = [sum(weights[i] * points[i][j] for i in range(len(points)))
               for j in range(len(points[0]))]
    result.update(weights=list(map(str, weights)), value=str(min(columns)),
                  worst_expected_win_points=str(min(columns)),
                  column_expectations=list(map(str, columns)),
                  support=[i for i, weight in enumerate(weights) if weight],
                  fallback_preserved=result['status'] != 'selected')
    return result


def solve_absolute(document, build_table, solve_full_table, verify_certificate,
                   *, max_pivots=128, max_bits=512):
    """Consume raw PORT receipts. Missing/nonterminal cells never call a solver.

    Callers supply causally aligned, complete terminal rollouts of the SAME
    own plans against the SAME public-information-compatible rival scenarios.
    Receipt labels/hashes do not themselves establish rollout correctness.
    """
    table = build_table(deepcopy(document))
    rows = embedding(table)
    if rows is None:
        return {'status': 'terminal_receipts_incomplete', 'objective': OBJECTIVE,
                'solver_called': False, 'fallback_preserved': True,
                'weights': None, 'win_probability': None, 'scenario_probabilities': None,
                'incomplete_cells': deepcopy(table['incomplete_cells']),
                'nonterminal_cells': deepcopy(table['nonterminal_cells'])}
    raw = solve_full_table(rows, max_pivots=max_pivots, max_bits=max_bits)
    return _consume(table, rows, raw, verify_certificate)


def make_score_selector(selector_type, weighted_factory, build_table,
                        solve_full_table, verify_certificate, *, rng=None,
                        max_pivots=128, max_bits=512):
    """Reuse PRISM sampling/persistence and T15's unchanged single-lot transform.

    This optional selector's window['deltas'] is a raw PORT receipt DOCUMENT,
    not a numeric cash-delta matrix. Its receipt plan IDs must match the actual
    complete single-product sale schedules in window['plans'], baseline first.
    The caller is responsible for binding those schedules and the current
    public decision state to the supplied causal terminal rollouts. The usual
    physical feasibility callback is still required for EVERY real plan.

    One instance per actor/match. Inherit existing transform unchanged and use
    the established continuation wrapper for ongoing feasibility/skipped dates.
    No new receipt table is consulted after commitment. No production call.
    """
    context = {}

    def provider(rows):
        raw = solve_full_table(rows, max_pivots=max_pivots, max_bits=max_bits)
        answer = _consume(context['table'], rows, raw, verify_certificate)
        context['answer'] = answer
        if answer['status'] != 'selected':
            return {'status': answer['status']}
        return raw

    weighted_type = type(weighted_factory(selector_type, provider, rng=rng,
                                         max_plans=9, max_streams=32))

    class ScorePlanSelector(weighted_type):
        def __init__(self):
            super().__init__()
            self.last_objective = None

        def choose(self, key, plans, deltas, *, feasible, mode='mixed', learned_start=0):
            if self.active is not None:
                if self.active['key'] != key:
                    raise ValueError('Finish the committed window before another lot')
                return deepcopy(self.active)
            if key in self.completed:
                return None
            if mode == 'baseline':
                return self._fallback(key, 'baseline')
            if mode != 'mixed':
                return self._fallback(key, 'absolute_mode_unavailable')
            context.clear()
            self.last_objective = None
            try:
                table = build_table(deepcopy(deltas))
                rows = embedding(table)
                if rows is None:
                    return self._fallback(key, 'terminal_receipts_incomplete')
                frozen = deepcopy(plans)
                if [plan['id'] for plan in frozen] != table['plan_ids']:
                    return self._fallback(key, 'receipt_plan_order_mismatch')
                context['table'] = table
                virtual = deepcopy(frozen[0])
                virtual_id = '__score_embedding_zero__'
                while virtual_id in table['plan_ids']:
                    virtual_id += '_'
                virtual['id'] = virtual_id
                originals = {p['id']: p for p in frozen}
                verdicts = {}

                def supported(plan):
                    identity = frozen[0]['id'] if plan['id'] == virtual_id else plan['id']
                    if identity not in verdicts:
                        verdicts[identity] = feasible(deepcopy(originals[identity]))
                    return verdicts[identity]

                chosen = super().choose(key, [virtual] + frozen, rows,
                                        feasible=supported, mode='mixed')
            except Exception:
                return self._fallback(key, 'absolute_contract_unavailable')
            self.last_objective = deepcopy(context.get('answer'))
            if chosen is None:
                return None
            # PRISM's draw was over a zero-mass virtual row plus real rows.
            # Expose ONLY the original plan identity and absolute objective.
            if chosen['plan_index'] == 0:
                self.active = None
                return self._fallback(key, 'virtual_row_not_executable')
            self.active['plan_index'] -= 1
            self.active['weights'] = self.active['weights'][1:]
            self.active['solution'] = deepcopy(self.last_objective)
            self.last_decision = {'reason': 'committed', **deepcopy(self.active)}
            return deepcopy(self.active)

        def transform_terminal(self, observation, configuration, base_action, *,
                               document, feasible):
            """Select a complete market queue at the final actionable step only.

            Each terminal receipt must include that plan's identical own_action
            and the current step. The caller supplies all hypothetical scenario
            receipts, never the actual hidden rival action. Full market-queue
            feasibility must be tested on current own state by the callback.
            Production fields and non-SELL slots remain exactly as supplied.
            Unlike inherited transform, this supports multiple products in one
            terminal market queue. Reuses the SAME choose/sampling operation.
            """
            fallback = deepcopy(base_action)
            try:
                now = observation['step']
                if type(now) is not int or now != int((configuration or {}).get('episodeSteps', 720)) - 2:
                    return fallback
                key = ('terminal-score', observation['player'], now)
                table = build_table(deepcopy(document))
                if embedding(table) is None:
                    return fallback
                plans = []
                parent_fields = {k: v for k, v in fallback.items() if k != 'market'}
                parent_queue = fallback.get('market', [])
                def is_sale(order):
                    return isinstance(order, list) and len(order) >= 3 and order[0] == 'SELL'
                for identity, receipts in zip(table['plan_ids'], table['receipts']):
                    action = deepcopy(receipts[0]['own_action'])
                    if any(r.get('step') != now or r.get('own_action') != action for r in receipts):
                        return fallback
                    if {k: v for k, v in action.items() if k != 'market'} != parent_fields:
                        return fallback
                    queue = action.get('market', [])
                    for index in range(max(len(queue), len(parent_queue))):
                        old = parent_queue[index] if index < len(parent_queue) else []
                        new = queue[index] if index < len(queue) else []
                        if ((old and not is_sale(old)) or (new and not is_sale(new))) and old != new:
                            return fallback
                    plans.append({'id': identity, 'action': action})
                if plans[0]['action'] != fallback:
                    return fallback
                current_verdicts = {}
                def current_feasible(action):
                    stamp = json.dumps(action, sort_keys=True, separators=(',', ':'))
                    if stamp not in current_verdicts:
                        current_verdicts[stamp] = feasible(deepcopy(action))
                    return current_verdicts[stamp]
                selected = self.choose(key, plans, document,
                                       feasible=lambda plan: current_feasible(plan['action']))
                if selected is None:
                    return fallback
                # Preserve the draw only while the complete committed action
                # remains in the current parent-bound set of terminal plans.
                committed = selected['plan']
                if not any(p['id'] == committed['id'] and p['action'] == committed['action']
                           for p in plans):
                    self.active = None
                    self._fallback(key, 'terminal_commitment_changed')
                    return fallback
                if current_feasible(selected['plan']['action']) is not True:
                    self.active = None
                    self._fallback(key, 'terminal_continuation_unavailable')
                    return fallback
                return deepcopy(selected['plan']['action'])
            except Exception:
                return fallback

    return ScorePlanSelector()


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError('Cannot load supplied source')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--terminal-file', type=Path, required=True)
    parser.add_argument('--solver-file', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--max-pivots', type=int, default=128)
    parser.add_argument('--max-bits', type=int, default=512)
    args = parser.parse_args(argv)
    try:
        terminal = _load(args.terminal_file, 'score_terminal_dependency')
        solver = _load(args.solver_file, 'score_full_support_dependency')
        answer = solve_absolute(json.loads(args.input.read_text()), terminal.build_table,
                                solver.solve_full_table, solver.verify_certificate,
                                max_pivots=args.max_pivots, max_bits=args.max_bits)
        text = json.dumps(answer, indent=2, allow_nan=False) + '\n'
        if args.output:
            args.output.write_text(text, encoding='utf-8')
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
        print(json.dumps({'error': type(exc).__name__, 'message': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
