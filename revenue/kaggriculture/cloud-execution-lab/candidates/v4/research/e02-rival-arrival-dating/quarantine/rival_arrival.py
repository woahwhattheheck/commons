# SPDX-License-Identifier: Apache-2.0
"""Public-only rival harvest arrival hypotheses for the canonical TITAN seller.

The legacy seller reduced every visible rival yield drop to an immediate scalar
stress quantity. E02 keeps that scalar as a diagnostic stress case, but when the
public board actually supports a harvest hypothesis it derives a legal arrival
interval from public actor positions and day reset. Ambiguous decay/DIG/escape
transitions remain {0, q} hypotheses; no hidden rival inventory is reconstructed.
"""
from __future__ import annotations

import copy
from collections import defaultdict

import mechanics as m
import scheduler as scheduling
import selected_sell_core as selected_core
from seller_snapshot import seller_public_observation as _base_seller_public_observation

TURNS_PER_DAY = 24
LOOKBACK = 8
MAX_RIVAL_SUPPLY = 100

_ORIGINAL_SCHEDULER_OPTIMIZE = scheduling.optimize_lot
_ORIGINAL_SELECTED_OPTIMIZE = selected_core.optimize_lot
_INSTALLED = False


def seller_public_observation(observation, *, copy_tiles=True):
    """Extend QUICKSTEP's compact public snapshot with public rival positions."""
    snapshot = _base_seller_public_observation(observation, copy_tiles=copy_tiles)
    if observation is None:
        return None
    player = int(observation['player'])
    rival = 1 - player
    source = observation['farms'][rival]
    target = snapshot['farms'][rival]
    if copy_tiles:
        target['farmer'] = copy.deepcopy(source.get('farmer'))
        target['hands'] = copy.deepcopy(source.get('hands', []))
    else:
        target['farmer'] = source.get('farmer')
        target['hands'] = source.get('hands', [])
    return snapshot


class RivalSupply(int):
    """Legacy scalar stress magnitude plus public dated harvest hypotheses."""
    def __new__(cls, quantity, hypotheses=(), *, visible=0, recent=0):
        obj = int.__new__(cls, max(0, int(quantity)))
        obj.hypotheses = tuple(dict(h) for h in hypotheses)
        obj.visible = max(0, int(visible))
        obj.recent = max(0, int(recent))
        return obj


def _product(tile):
    if not isinstance(tile, dict):
        return None
    if tile.get('kind') == 'PLANT':
        return tile.get('crop')
    animal = tile.get('animal')
    if animal in m.ANIMALS:
        return m.ANIMALS[animal]['product']
    return None


def _yield(tile):
    return max(0, int(tile.get('yield_units', 0))) if isinstance(tile, dict) else 0


def _positions(farm):
    if not isinstance(farm, dict):
        return []
    return [farm.get('farmer'), *list(farm.get('hands', []) or [])]


def _actor_indices(farm, x, y):
    target = [int(x), int(y)]
    return [idx for idx, pos in enumerate(_positions(farm))
            if isinstance(pos, (list, tuple)) and list(pos) == target]


def _same_plant(tile, crop):
    return isinstance(tile, dict) and tile.get('kind') == 'PLANT' and tile.get('crop') == crop


def _same_animal(tile, animal):
    return isinstance(tile, dict) and tile.get('animal') == animal


def _harvest_compatible(old_tile, new_tile, *, day_reset):
    """Whether HARVEST could produce this public transition.

    This is deliberately one-sided: False rules harvest out; True may still be
    ambiguous with public non-harvest causes and is classified separately.
    """
    if not isinstance(old_tile, dict) or _yield(old_tile) <= 0:
        return False
    if old_tile.get('kind') == 'PLANT':
        crop = old_tile.get('crop')
        if crop not in m.CROPS:
            return False
        ongoing = bool(m.CROPS[crop]['ongoing'])
        if not day_reset:
            if ongoing:
                return _same_plant(new_tile, crop) and _yield(new_tile) == 0
            return new_tile is None
        # At day reset, decay/refresh/weed spawning runs after the unit action.
        if ongoing:
            return (_same_plant(new_tile, crop)
                    or (isinstance(new_tile, dict) and new_tile.get('kind') == 'WEED'))
        return (new_tile is None
                or (isinstance(new_tile, dict) and new_tile.get('kind') == 'WEED'))
    animal = old_tile.get('animal')
    if animal in m.ANIMALS:
        if not day_reset:
            return _same_animal(new_tile, animal) and _yield(new_tile) == 0
        # End-of-day refresh can either retain/reproduce the animal or make it
        # escape to its bare structure after a possible harvest.
        return (_same_animal(new_tile, animal)
                or (isinstance(new_tile, dict)
                    and new_tile.get('kind') == m.ANIMALS[animal]['structure']
                    and 'animal' not in new_tile))
    return False


def _certain_harvest(old_tile, new_tile, *, day_reset):
    if day_reset:
        return False
    if old_tile.get('kind') == 'PLANT':
        crop = old_tile.get('crop')
        return bool(crop in m.CROPS and m.CROPS[crop]['ongoing']
                    and _same_plant(new_tile, crop) and _yield(new_tile) == 0)
    animal = old_tile.get('animal')
    return bool(animal in m.ANIMALS and _same_animal(new_tile, animal)
                and _yield(new_tile) == 0)


def _arrival_interval(now, old_farm, new_farm, actor_indices, board_size):
    """Earliest/latest sale step for a harvest that occurred before ``now``."""
    now = int(now)
    if now % TURNS_PER_DAY == 0:
        # The prior step's end-of-day auto-drop already moved carried goods to
        # the shed (subject to hidden capacity, represented by the zero branch).
        return now, now
    current_positions = _positions(new_farm)
    access = m._shed_access_tiles(board_size)
    distances = []
    for idx in actor_indices:
        if idx >= len(current_positions):
            continue
        pos = current_positions[idx]
        old_pos = _positions(old_farm)[idx]
        # One unit action cannot both HARVEST and move. Without a day reset the
        # same public actor therefore must still occupy the harvested tile.
        if not (isinstance(pos, (list, tuple)) and list(pos) == list(old_pos)):
            continue
        px, py = int(pos[0]), int(pos[1])
        distances.append(min(abs(px - sx) + abs(py - sy) for sx, sy in access))
    if not distances:
        return None
    next_reset = (now // TURNS_PER_DAY + 1) * TURNS_PER_DAY
    earliest = min(now + min(distances), next_reset)
    return int(earliest), int(next_reset)


def observe(self, obs):
    """Record only publicly feasible harvest hypotheses from yield transitions."""
    now = int(obs['step'])
    if self.previous:
        rival = 1 - int(obs['player'])
        old_farm = self.previous['farms'][rival]
        new_farm = obs['farms'][rival]
        old_tiles = old_farm.get('tiles', [])
        new_tiles = new_farm.get('tiles', [])
        board_size = len(new_tiles)
        day_reset = now % TURNS_PER_DAY == 0
        for y, row in enumerate(old_tiles):
            for x, old_tile in enumerate(row):
                product = _product(old_tile)
                if product is None or _yield(old_tile) <= 0:
                    continue
                new_tile = (new_tiles[y][x] if y < len(new_tiles) and x < len(new_tiles[y])
                            else None)
                if not _harvest_compatible(old_tile, new_tile, day_reset=day_reset):
                    continue
                actors = _actor_indices(old_farm, x, y)
                if not actors:
                    # Decay/removal with nobody publicly on the tile cannot be a
                    # harvest; do not turn it into hidden carried inventory.
                    continue
                interval = _arrival_interval(now, old_farm, new_farm, actors, board_size)
                if interval is None:
                    continue
                earliest, latest = interval
                quantity = _yield(old_tile)  # HARVEST takes the full held yield.
                certain = _certain_harvest(old_tile, new_tile, day_reset=day_reset)
                event = (now, quantity, earliest, latest, int(certain), x, y)
                bucket = self.observed_harvests.setdefault(product, [])
                if event not in bucket:
                    bucket.append(event)
    for product in list(self.observed_harvests):
        rows = [row for row in self.observed_harvests[product]
                if row and now - int(row[0]) <= LOOKBACK]
        if rows:
            self.observed_harvests[product] = rows
        else:
            self.observed_harvests.pop(product, None)


def _decode_event(row):
    if len(row) >= 7:
        step, quantity, earliest, latest, certain, x, y = row[:7]
        return {
            'observed_step': int(step), 'quantity': max(0, int(quantity)),
            'earliest': int(earliest), 'latest': int(latest),
            'certain': bool(certain), 'tile': [int(x), int(y)],
        }
    return None


def rival_supply(self, obs, item):
    """Return legacy scalar stress plus public arrival hypotheses for ``item``."""
    rival = obs['farms'][1 - int(obs['player'])]
    visible = 0
    for row in rival['tiles']:
        for tile in row:
            if _product(tile) == item:
                visible += _yield(tile)
    step = int(obs['step'])
    recent = 0
    hypotheses = []
    for row in self.observed_harvests.get(item, []):
        if not row or step - int(row[0]) > LOOKBACK:
            continue
        if len(row) >= 2:
            recent += max(0, int(row[1]))
        decoded = _decode_event(row)
        if decoded is not None:
            hypotheses.append(decoded)
    hypotheses.sort(key=lambda h: (h['earliest'], h['latest'], h['observed_step'], h['tile']))
    scalar = min(MAX_RIVAL_SUPPLY, max(visible, recent))
    return RivalSupply(scalar, hypotheses, visible=visible, recent=recent)


def _arrival_schedule(hypotheses, key, now, end):
    dated = defaultdict(int)
    for h in hypotheses:
        step = max(int(now), int(h[key]))
        if step <= int(end):
            dated[step] += max(0, int(h['quantity']))
    # Preserve the legacy 100-unit rival-supply ceiling as a total shed-capacity
    # bound, not 100 units independently at every dated wave.
    remaining = MAX_RIVAL_SUPPLY
    schedule = []
    for step, quantity in sorted(dated.items()):
        take = min(remaining, quantity)
        if take > 0:
            schedule.append((step, take))
            remaining -= take
        if remaining <= 0:
            break
    return tuple(schedule)


def _timed_optimize(*, item, quantity, inventory, params, shops, config, now, dates,
                    reference, rival_quantity, minimum_now=0, capacity_ok=None,
                    last=718, market_path_cls=None):
    """Legacy optimizer with decision scenarios replaced only when timing narrows."""
    supply = rival_quantity
    hypotheses = tuple(getattr(supply, 'hypotheses', ()))
    scalar = max(0, int(supply))
    if not hypotheses:
        raise ValueError('timed optimizer requires at least one dated hypothesis')
    end = dates[-1]
    MarketPath = market_path_cls or selected_core.MarketPath
    model = MarketPath(item, inventory, params, shops, config, now, end)

    earliest = _arrival_schedule(hypotheses, 'earliest', now, end)
    latest = _arrival_schedule(hypotheses, 'latest', now, end)
    scenarios = [('no_rival', 0, 'paired')]
    if earliest:
        scenarios.append(('public_harvest_earliest', earliest, 'paired'))
    if latest and latest != earliest:
        scenarios.append(('public_harvest_latest', latest, 'paired'))

    # Preserve the old quantity-only urgency family as explicit diagnostics. It
    # no longer vetoes a physically dated plan once public timing narrowed the
    # harvest hypothesis; when timing is absent we delegate to legacy exactly.
    stress = [('observed_paired', scalar, 'paired'),
              ('observed_later_order', scalar, 'after')]
    if end > now:
        stress.append(('observed_next_turn', ((now + 1, scalar),), 'paired'))
    if end > now + 2:
        stress.append(('observed_before_delayed_batch', ((end - 1, scalar),), 'paired'))

    baseline = [model.score(reference, quantity, rival, alignment, end == last)
                for _, rival, alignment in scenarios]
    stress_baseline = [model.score(reference, quantity, rival, alignment, end == last)
                       for _, rival, alignment in stress]
    reference_feasible = ((capacity_ok(reference) if capacity_ok else True)
                          and dict(reference).get(now, 0) >= minimum_now)
    best_plan = tuple(reference)
    best_key = ((0.0, 0.0, 0.0) if reference_feasible
                else (-float('inf'), -float('inf'), 0.0))
    best_scores = baseline
    best_stress = stress_baseline
    found_feasible = reference_feasible
    candidates = {tuple(reference)}
    future = dates[1:]
    for first in range(minimum_now, quantity + 1):
        remaining = quantity - first
        candidates.add(((now, first),))
        for date in future:
            candidates.add(((now, first), (date, remaining)))
        if len(future) >= 2:
            for share in (1, 2, 3):
                a = remaining * share // 4
                candidates.add(((now, first), (future[0], a), (future[-1], remaining - a)))

    for plan in sorted(candidates):
        if sum(q for _, q in plan) > quantity:
            continue
        if dict(plan).get(now, 0) < minimum_now:
            continue
        if reference_feasible:
            first_score = model.score(plan, quantity, 0, 'paired', end == last)
            if first_score[0] - baseline[0][0] <= 0:
                continue
            if capacity_ok and not capacity_ok(plan):
                continue
            scores = [first_score]
            competitive = True
            for (_, rival, alignment), base_score in zip(scenarios[1:], baseline[1:]):
                score = model.score(plan, quantity, rival, alignment, end == last)
                if score[0] - base_score[0] <= 0:
                    competitive = False
                    break
                scores.append(score)
            if not competitive:
                continue
        else:
            if capacity_ok and not capacity_ok(plan):
                continue
            scores = [model.score(plan, quantity, rival, alignment, end == last)
                      for _, rival, alignment in scenarios]
        deltas = [score[0] - base_score[0] for score, base_score in zip(scores, baseline)]
        key = (round(min(deltas), 8), round(sum(deltas), 8),
               float(dict(plan).get(now, 0)))
        if (key[0] > 0 or not reference_feasible) and key > best_key:
            best_key, best_plan, best_scores = key, plan, scores
            best_stress = [model.score(plan, quantity, rival, alignment, end == last)
                           for _, rival, alignment in stress]
            found_feasible = True

    interval_rows = [dict(h) for h in hypotheses]
    return best_plan, {
        'item': item, 'quantity': quantity, 'rival_scenario_quantity': scalar,
        'reference': list(reference), 'plan': list(best_plan),
        'minimum_now': minimum_now,
        'rival_arrival_hypotheses': interval_rows,
        'scenarios': {
            name: {'reference_relative_value': base_score[0],
                   'relative_value': score[0], 'own_receipts': score[1],
                   'rival_receipts': score[2], 'carry_units': score[3]}
            for (name, _, _), base_score, score in zip(scenarios, baseline, best_scores)
        },
        'stress_scenarios': {
            name: {'reference_relative_value': base_score[0],
                   'relative_value': score[0], 'own_receipts': score[1],
                   'rival_receipts': score[2], 'carry_units': score[3]}
            for (name, _, _), base_score, score in zip(stress, stress_baseline, best_stress)
        },
        'worst_relative_gain': best_key[0] if found_feasible else 0.0,
        'forced_feasibility': not reference_feasible and found_feasible,
        'feasible': found_feasible, 'plans_evaluated': len(candidates),
    }


def selected_optimize_lot(**kwargs):
    supply = kwargs.get('rival_quantity')
    if not getattr(supply, 'hypotheses', ()):  # Exact legacy path when timing is absent.
        return _ORIGINAL_SELECTED_OPTIMIZE(**kwargs)
    return _timed_optimize(**kwargs, market_path_cls=selected_core.MarketPath)


def scheduler_optimize_lot(**kwargs):
    supply = kwargs.get('rival_quantity')
    if not getattr(supply, 'hypotheses', ()):  # Exact legacy path when timing is absent.
        return _ORIGINAL_SCHEDULER_OPTIMIZE(**kwargs)
    return _timed_optimize(**kwargs, market_path_cls=scheduling.MarketPath)


def install():
    """Install E02 on the existing seller/optimizer; idempotent, no new actor."""
    global _INSTALLED
    if _INSTALLED:
        return
    scheduling.SellScheduler.observe = observe
    scheduling.SellScheduler.rival_supply = rival_supply
    scheduling.optimize_lot = scheduler_optimize_lot
    selected_core.optimize_lot = selected_optimize_lot

    # TITAN's deadline checkpoint uses the same compact projection. Evolve that
    # existing hook so fallback/recovery retains the public rival positions E02
    # consumes, without adding any private state to the checkpoint.
    import titan_runtime
    import frozen_selected
    frozen_selected.seller_public_observation = seller_public_observation
    titan_runtime.TitanAgent._seller_public_observation = staticmethod(seller_public_observation)
    _INSTALLED = True
