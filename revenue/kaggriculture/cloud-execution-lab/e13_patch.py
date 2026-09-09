# SPDX-License-Identifier: Apache-2.0
"""One-shot E13 source patcher; deleted by the VM evidence commit."""
from pathlib import Path

TARGET = Path(__file__).with_name('frozen_selected.py')

HELPER = r'''def _funding_prefix_end(route, now, end):
    """Stop before the next requested future sale; future intent is not cash."""
    for t in range(now + 1, end + 1):
        orders = route[t].get('market', []) if t < len(route) else []
        if any(o and len(o) > 2 and o[0] == 'SELL' and max(0, int(o[2])) > 0
               for o in orders):
            return t - 1, t
    return end, None


def _funding_trace(obs, config, farm, private, route, now, end, current_market,
                   stress_units=0):
    """Execute the bounded own market tape and return actual acquisition fills.

    Only the current turn's materialized sales may fund the prefix.  Future unit
    actions are applied before their market turn so shed clipping remains real.
    `stress_units` is a named prior rival draw from every BUY_PRODUCT market.
    """
    f, p = copy.deepcopy(farm), copy.deepcopy(private)
    inventory = {k: int(v) for k, v in obs['market']['inventory'].items()}
    params = obs['market'].get('params')
    cap = int(config.get('shedCapacity', 100))
    max_orders = int(config.get('maxMarketOrdersPerTurn', 10))
    hires = int(f.get('hires_today', 0))
    buy_items = set()
    for t in range(now, end + 1):
        orders = current_market if t == now else (route[t].get('market', []) if t < len(route) else [])
        for o in orders[:max_orders]:
            if o and len(o) > 2 and o[0] == 'BUY_PRODUCT':
                buy_items.add(o[1])
    if stress_units:
        for item in buy_items:
            inventory[item] = inventory.get(item, 0) - int(stress_units)
    acquisitions = []
    for t in range(now, end + 1):
        if t > now:
            action = route[t] if t < len(route) else parent.PASS
            acts = [action.get('farmer', ['PASS']), *action.get('hands', [])]
            for i, a in enumerate(acts):
                m._apply_unit_action(f, p, i, a, len(f['tiles']), t // 24, 24, 10**6)
        if t > now and t % 24 == 0:
            hires = 0
        orders = current_market if t == now else (route[t].get('market', []) if t < len(route) else [])
        for index, order in enumerate(orders[:max_orders]):
            if not order:
                continue
            op = order[0]
            item = order[1] if len(order) > 1 else ''
            requested = max(0, int(order[2])) if len(order) > 2 else 1
            executed = 0
            if op == 'SELL' and len(order) > 2:
                for _ in range(requested):
                    if p['shed'].get(item, 0) <= 0:
                        break
                    price = m.market_price(item, inventory[item], params)
                    p['shed'][item] -= 1
                    f['money'] += price
                    if price > 1:
                        inventory[item] += 1
            elif op == 'HIRE':
                price = m._hire_cost(hires, int(config.get('farmHandCostMult', 1)))
                if f['money'] >= price:
                    f['money'] -= price
                    hires += 1
                    executed = 1
                    f['hands'].append(m._spawn_hand(f, len(f['tiles'])))
                    p['inventories'].append({})
                acquisitions.append(((t, index, op, ''), executed))
            elif op == 'BUY_LAND':
                land_index = len(f['unlocked_quadrants']) - 1
                price = m.LAND_PRICES[land_index] if land_index < len(m.LAND_PRICES) else 0
                if f['money'] >= price:
                    f['money'] -= price
                    executed = 1
                    if len(f['unlocked_quadrants']) <= len(m.LAND_ORDER):
                        f['unlocked_quadrants'].append(
                            m.LAND_ORDER[len(f['unlocked_quadrants']) - 1])
                acquisitions.append(((t, index, op, ''), executed))
            elif op == 'BUY_SEED' and len(order) > 2 and item in m.CROPS:
                price = int(m.CROPS[item]['seed'])
                for _ in range(requested):
                    if f['money'] < price:
                        break
                    f['money'] -= price
                    p['seeds'][item] = p['seeds'].get(item, 0) + 1
                    executed += 1
                acquisitions.append(((t, index, op, item), executed))
            elif op == 'BUY_ANIMAL' and len(order) > 2 and item in m.ANIMALS:
                price = int(m.ANIMALS[item]['cost'])
                for _ in range(requested):
                    if f['money'] < price or sum(p['shed'].values()) >= cap:
                        break
                    f['money'] -= price
                    p['shed'][item] = p['shed'].get(item, 0) + 1
                    executed += 1
                acquisitions.append(((t, index, op, item), executed))
            elif op == 'BUY_PRODUCT' and len(order) > 2 and item in m.PRODUCTS:
                for _ in range(requested):
                    if sum(p['shed'].values()) >= cap:
                        break
                    price = m.market_price(item, inventory[item] - 1, params)
                    if f['money'] < price:
                        break
                    f['money'] -= price
                    inventory[item] -= 1
                    p['shed'][item] = p['shed'].get(item, 0) + 1
                    executed += 1
                acquisitions.append(((t, index, op, item), executed))
    return {'cash': int(f['money']), 'acquisitions': acquisitions}


def funded_minimum_now(obs, config, base, farm, private, route, end,
                       current, targets, item, stress_units=32):
    """Smallest current sale that preserves the inherited executable prefix."""
    now = int(obs['step'])
    baseline = max(0, int(current.get(item, 0)))
    prefix_end, funding_turn = _funding_prefix_end(route, now, end)
    max_orders = int(config.get('maxMarketOrdersPerTurn', 10))
    certificate = {
        'item': item, 'baseline_now': baseline, 'prefix_end': prefix_end,
        'funding_turn': funding_turn, 'stress_units': int(stress_units),
        'fallback': False,
    }
    try:
        reference_market = materialize_sales(
            base['market'], current, private['shed'], targets, max_orders)
        reference = _funding_trace(
            obs, config, farm, private, route, now, prefix_end,
            reference_market, stress_units=0)
        required = {key: units for key, units in reference['acquisitions'] if units > 0}
        certificate['reference_acquisitions'] = sum(required.values())
        certificate['reference_terminal_cash'] = reference['cash']
        if not required:
            certificate['minimum_now'] = 0
            return 0, certificate
        for quantity in range(baseline + 1):
            totals = dict(current)
            totals[item] = quantity
            candidate_market = materialize_sales(
                base['market'], totals, private['shed'], targets, max_orders)
            traces = [
                _funding_trace(obs, config, farm, private, route, now, prefix_end,
                               candidate_market, stress_units=0),
                _funding_trace(obs, config, farm, private, route, now, prefix_end,
                               candidate_market, stress_units=stress_units),
            ]
            safe = True
            for trace in traces:
                filled = dict(trace['acquisitions'])
                if any(filled.get(key, 0) < units for key, units in required.items()):
                    safe = False
                    break
            if safe:
                certificate['minimum_now'] = quantity
                certificate['scenario_terminal_cash'] = [trace['cash'] for trace in traces]
                return quantity, certificate
    except Exception as exc:
        certificate['error'] = f'{type(exc).__name__}: {exc}'[:500]
    certificate['fallback'] = True
    certificate['minimum_now'] = baseline
    return baseline, certificate
'''


def main():
    text = TARGET.read_text()
    anchor = """def sale_quantities(orders):\n    result={}\n    for o in orders:\n        if o and len(o)>2 and o[0]=='SELL':\n            result[o[1]]=result.get(o[1],0)+max(0,int(o[2]))\n    return result\n\n\ndef joint_resource_bound"""
    if HELPER.strip() not in text:
        if anchor not in text:
            raise SystemExit('E13 helper insertion anchor changed')
        replacement = anchor[:-len('def joint_resource_bound')] + HELPER + "\n\ndef joint_resource_bound"
        text = text.replace(anchor, replacement, 1)
    old = """            if len(dates)<2:continue\n            minimum=current[item] if farm['money']<budget else 0\n            receipt_feasible=self.receipt_profile(obs,base,farm,private,end,item,config)\n            route=self.controller.R[self.controller.cur]\n"""
    new = """            if len(dates)<2:continue\n            route=self.controller.R[self.controller.cur]\n            minimum,funding=funded_minimum_now(obs,config,base,farm,private,route,end,\n                                                current,targets,item)\n            funding['nominal_future_spend']=budget\n            self.diagnostics.setdefault('funding_certificates',{})[item]=funding\n            receipt_feasible=self.receipt_profile(obs,base,farm,private,end,item,config)\n"""
    if new not in text:
        if old not in text:
            raise SystemExit('E13 minimum_now anchor changed')
        text = text.replace(old, new, 1)
    TARGET.write_text(text)
    print('E13_PATCH_APPLIED', TARGET)


if __name__ == '__main__':
    main()
