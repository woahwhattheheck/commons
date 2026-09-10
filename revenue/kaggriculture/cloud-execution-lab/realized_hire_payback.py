# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import copy
from typing import Any, Mapping, Sequence
import mechanics as m
from realized_hire_payback_common import SCHEMA_VERSION, _Reject, _json_clone, _strict_int, _validate_state, _verify_single_hire_delta
from realized_hire_payback_market import _validate_market
from realized_hire_payback_replay import _action_op, _consume_sell_queue, _route_row
from realized_hire_payback_loop import replay_hired_lifetime
from realized_hire_payback_finish import finish_hire_payback

def certify_realized_hire_payback(*, farm: Mapping[str, Any], private: Mapping[str, Any], market: Mapping[str, Any], unlocked_shops: Sequence[str], route: Sequence[Mapping[str, Any]], baseline_market: Sequence[Any], candidate_market: Sequence[Any], inserted_index: int, hire_cost: int, current_step: int, configuration: Mapping[str, Any] | None, decision_steps: Sequence[int]=()) -> dict:
    report: dict[str, Any] = {'schema_version': SCHEMA_VERSION, 'admit': False, 'reason': 'not_evaluated', 'promotion_authorized': False, 'hosted_leaderboard_claim': False, 'scope': 'same-hired-lifetime represented-route replay; official unit/decay primitives; SELL-only market; per-step non-displacement; floor-price public-state-neutral coverage'}
    try:
        if not isinstance(route, Sequence) or isinstance(route, (str, bytes, bytearray)):
            raise _Reject('invalid_route')
        cfg = dict(configuration or {})
        now = _strict_int(current_step, 'current_step', minimum=0)
        cost = _strict_int(hire_cost, 'hire_cost', minimum=1)
        slot = _strict_int(inserted_index, 'inserted_index', minimum=0)
        turns_per_day = _strict_int(cfg.get('turnsPerDay', 24), 'turnsPerDay', minimum=1)
        episode_steps = _strict_int(cfg.get('episodeSteps', 720), 'episodeSteps', minimum=2)
        market_limit = _strict_int(cfg.get('maxMarketOrdersPerTurn', 10), 'maxMarketOrdersPerTurn', minimum=1)
        shed_capacity = _strict_int(cfg.get('shedCapacity', 100), 'shedCapacity', minimum=0)
        if now > episode_steps - 2:
            raise _Reject('outside_action_horizon')
        control_farm, control_private, board_size = _validate_state(farm, private, cfg)
        market_inventory, market_params, shops = _validate_market(market, unlocked_shops)
        checkpoints = sorted({_strict_int(step, 'decision_step', minimum=0) for step in decision_steps})
        candidate_farm = copy.deepcopy(control_farm)
        candidate_private = copy.deepcopy(control_private)
        active_hands = len(control_farm['hands'])
        new_actor_index = active_hands + 1
        new_hand_slot = active_hands
        hires_today = _strict_int(control_farm.get('hires_today', 0), 'farm.hires_today', minimum=0)
        hire_mult = _strict_int(cfg.get('farmHandCostMult', 1), 'farmHandCostMult', minimum=1)
        expected_cost = _strict_int(m._hire_cost(hires_today, hire_mult), 'expected_hire_cost', minimum=1)
        if cost != expected_cost:
            raise _Reject('hire_cost_mismatch', f'certificate={cost}; official={expected_cost}')
        baseline_queue = _json_clone(list(baseline_market), 'baseline_market')
        candidate_queue = _json_clone(list(candidate_market), 'candidate_market')
        if len(baseline_queue) > market_limit or len(candidate_queue) > market_limit:
            raise _Reject('over_limit_current_market')
        _verify_single_hire_delta(baseline_queue, candidate_queue, slot)
        baseline_current_sales = _consume_sell_queue(control_private, baseline_queue)
        candidate_current_sales = _consume_sell_queue(candidate_private, candidate_queue, allow_hire_index=slot)
        if baseline_current_sales != candidate_current_sales or control_private != candidate_private:
            raise _Reject('current_market_not_state_neutral_except_hire')
        m._decay_plants(control_farm, now)
        m._decay_plants(candidate_farm, now)
        if (now + 1) % turns_per_day == 0:
            raise _Reject('hire_expires_before_first_action')
        day_end = (now // turns_per_day + 1) * turns_per_day - 1
        last_action_step = min(episode_steps - 2, len(route) - 1)
        horizon_end = min(day_end, last_action_step)
        if now + 1 > horizon_end:
            raise _Reject('no_represented_hired_lifetime')
        crossing = [step for step in checkpoints if now < step <= horizon_end]
        if crossing:
            raise _Reject('route_decision_checkpoint_in_horizon', repr(crossing))
        next_row, next_hands, _ = _route_row(route, now + 1, market_limit)
        del next_row
        if new_hand_slot >= len(next_hands):
            raise _Reject('newly_unlocked_slot_missing')
        first_action = next_hands[new_hand_slot]
        first_op = _action_op(first_action)
        if first_op == 'PASS':
            raise _Reject('newly_unlocked_slot_is_pass')
        candidate_farm['hands'].append(m._spawn_hand(candidate_farm, board_size))
        candidate_private['inventories'].append({})
        candidate_farm['hires_today'] = hires_today + 1
        ctx = {'farm': farm, 'private': private, 'market': market, 'route': route, 'cfg': cfg, 'now': now, 'cost': cost, 'turns_per_day': turns_per_day, 'market_limit': market_limit, 'shed_capacity': shed_capacity, 'control_farm': control_farm, 'control_private': control_private, 'candidate_farm': candidate_farm, 'candidate_private': candidate_private, 'board_size': board_size, 'market_inventory': market_inventory, 'market_params': market_params, 'shops': shops, 'checkpoints': checkpoints, 'active_hands': active_hands, 'new_actor_index': new_actor_index, 'new_hand_slot': new_hand_slot, 'horizon_end': horizon_end, 'first_action': first_action}
        data = replay_hired_lifetime(ctx, report)
        if data is None:
            return report
        return finish_hire_payback(ctx, data, report)
    except _Reject as exc:
        report['reason'] = exc.reason
        if exc.detail:
            report['detail'] = exc.detail[:300]
        return report
    except Exception as exc:
        report.update(reason='certificate_internal_error', detail=f'{type(exc).__name__}: {exc}'[:300])
        return report
