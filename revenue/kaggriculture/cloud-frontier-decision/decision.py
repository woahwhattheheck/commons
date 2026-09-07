# SPDX-License-Identifier: MIT
"""Marginal one-hand selection over caller-scheduled observable-state plans.

Pure calculation, not a scheduler or a game simulator. See README for the paired
counterfactual and inventory contract. No policy tape or hidden state is loaded.
"""
from math import isfinite


def hire_cost(hires_today, multiplier=1):
    if hires_today < 0 or multiplier < 0:
        raise ValueError('Negative hire input')
    a, b = 1, 1
    for _ in range(int(hires_today)):
        a, b = b, a + b
    return a * multiplier


def _number(value):
    value = float(value)
    if not isfinite(value):
        raise ValueError('Non-finite economic input')
    return value


def sale_receipts(lots, inventory_at, quote, last_sale):
    """Reprice a complete paired sale stream against exogenous inventory.

    inventory_at(product, step) excludes ALL sales in lots. Prior sales from this
    stream are added cumulatively; equal-step lots are processed in list order.
    quote(product, inventory) must use the observation's engine market params.
    Opponent/town trades belong in inventory_at, including chosen scenarios.
    Returns conditional receipts; it does not forecast a hidden opponent order.
    """
    supplied = {}
    total = 0
    for lot in sorted(lots, key=lambda x: x['step']):
        step, qty, item = lot['step'], lot['quantity'], lot['product']
        if int(step) != step or int(qty) != qty or qty < 0:
            raise ValueError('Sales need integer steps and nonnegative quantities')
        if step > last_sale:
            raise ValueError('Sale after final action')
        inv = _number(inventory_at(item, step)) + supplied.get(item, 0)
        for unit in range(qty):
            total += _number(quote(item, inv + unit))
        supplied[item] = supplied.get(item, 0) + qty
    return total


def select_hire(observation, configuration, plans, *, inventory_scenarios,
                quote, funds_before_hire=None, cash_reserve=0, free_order_slots=1):
    """Choose one supplied extra-hand plan with positive worst-scenario margin.

    Plan fields: id, observed_step, jointly_feasible, first_work_step,
    last_work_step, baseline_sales, with_hire_sales, additional_cost.
    additional_cost includes resources, displaced work and downstream upkeep,
    EXCLUDING this hire (computed here). Sales include affected existing-worker
    output, so extra supply's effect on that output is charged to the hire.

    Feasibility is supplied by FLORA's scheduler, not established by this
    calculation. No cash/price result is a guarantee of future execution.
    """
    now = int(observation['step'])
    farm = observation['farms'][observation['player']]
    turns = int(configuration.get('turnsPerDay', 24))
    last = int(configuration.get('episodeSteps', 720)) - 2
    if turns <= 0 or not inventory_scenarios:
        raise ValueError('Positive day length and explicit scenarios required')
    cost = hire_cost(int(farm['hires_today']), int(configuration.get('farmHandCostMult', 1)))
    funds = _number(farm['money'] if funds_before_hire is None else funds_before_hire)
    reserve = _number(cash_reserve)
    out = {'decision': 'KEEP', 'plan_id': None, 'market_order': None,
           'hire_cost': cost, 'conditional_margin': None, 'evaluations': []}
    if free_order_slots < 1 or funds - reserve < cost:
        out['reason'] = 'no_order_slot' if free_order_slots < 1 else 'cash_shortfall'
        return out
    # Hire occurs after unit actions and lasts only through this day's EOD.
    work_end = min(last, (now // turns + 1) * turns - 1)
    best = 0
    for plan in plans:
        result = {'plan_id': plan['id']}
        out['evaluations'].append(result)
        if plan['observed_step'] != now:
            result['reason'] = 'stale_plan'; continue
        if not plan['jointly_feasible']:
            result['reason'] = 'infeasible_plan'; continue
        if not now < plan['first_work_step'] <= plan['last_work_step'] <= work_end:
            result['reason'] = 'worker_lifetime'; continue
        lots = plan['baseline_sales'] + plan['with_hire_sales']
        if any(l['step'] < now or l['step'] > last for l in lots):
            result['reason'] = 'sale_horizon'; continue
        extra = _number(plan['additional_cost'])
        margins = {}
        for name, inventory_at in inventory_scenarios.items():
            base = sale_receipts(plan['baseline_sales'], inventory_at, quote, last)
            candidate = sale_receipts(plan['with_hire_sales'], inventory_at, quote, last)
            margins[name] = candidate - base - cost - extra
        floor = min(margins.values())
        result.update(reason='evaluated', margins=margins,
                      conditional_margin=[floor, max(margins.values())])
        if floor > best:
            best = floor
            out.update(decision='HIRE', plan_id=plan['id'], market_order=['HIRE'],
                       conditional_margin=result['conditional_margin'])
    out['reason'] = 'positive_incremental_margin' if best > 0 else 'no_positive_feasible_plan'
    return out
