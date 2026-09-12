# SPDX-License-Identifier: Apache-2.0
"""Bounded livestock-feed suppression with a physical next-day rescue certificate.

The Kaggriculture engine lets an animal survive exactly one unfed daily refresh;
base production still occurs on that first miss, while care bonus production
requires feeding.  This module exploits only that deterministic boundary.  It
never executes a future game state and never treats requested purchases as
receipts.

The proposal is deliberately narrow:
* only a FEED returned on the final slot of a standard 24-turn day can change;
* the animal must have zero prior misses and no current/pending care value;
* the completed post-unit snapshot must prove the incumbent FEED really worked;
* the existing operating-stock feed-window certificate must prove a funded,
  reachable feed for the same animal during the next day; and
* that rescue must already be funded without crediting the wheat saved here.

It is a candidate component.  Merely importing it does not alter TITAN policy.
"""
from copy import deepcopy

from operating_stock import _current_room_bound, _feed_window, _order_quantity, _whole


def _units(selected):
    return [selected.get('farmer') or ['PASS'], *(selected.get('hands') or [])]


def _positions(farm):
    return [tuple(farm['farmer']), *[tuple(p) for p in farm.get('hands', [])]]


def _tile(farm, position):
    x, y = position
    tiles = farm['tiles']
    if not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])):
        raise ValueError('worker_position_outside_farm')
    return tiles[y][x]


def _animal_key(farm, position):
    tile = _tile(farm, position)
    if not isinstance(tile, dict) or 'animal' not in tile:
        return None
    return (position, tile['animal'])


def _current_wheat_after_sales(private, orders, maximum):
    stock = _whole(private['shed'].get('WHEAT', 0))
    offered = sum(_order_quantity(order) for order in orders[:maximum]
                  if order and order[:2] == ['SELL', 'WHEAT'])
    # Requested buys are intentionally absent.  A sale can consume at most the
    # observed stock, so this is the guaranteed shed wheat after this market row.
    return max(0, stock - offered)


def propose_alternate_day_feed(mechanics, observation, configuration, selected,
                               post_farm, post_private, route, checkpoints=()):
    """Replace certified day-close FEED actions with PASS for one day.

    ``post_farm``/``post_private`` must be the caller's completed deterministic
    unit-stage snapshot for ``selected``.  The helper uses that snapshot only as
    a certificate for the incumbent action and for physical stock accounting;
    it returns a copied action and does not mutate observations, route or state.
    """
    report = {
        'changed': False,
        'certified': False,
        'reason': 'no_feed_action',
        'saved_wheat_units': 0,
        'future_purchase_credit': 0,
        'saved_wheat_rescue_credit': 0,
    }
    try:
        cfg = dict(configuration or {})
        now = _whole(observation['step'])
        turns = int(cfg.get('turnsPerDay', 24))
        episode = int(cfg.get('episodeSteps', 720))
        capacity = int(cfg.get('shedCapacity', 100))
        maximum = int(cfg.get('maxMarketOrdersPerTurn', 10))
        player = int(observation['player'])
        farm = observation['farms'][player]
        if (turns != 24 or episode != 720 or capacity != 100 or maximum != 10
                or len(farm['tiles']) != 10 or len(route) < 696 or now >= 695):
            raise ValueError('outside_supported_alternate_feed_window')
        if now % turns != turns - 1:
            raise ValueError('alternate_feed_is_day_close_only')

        actions = _units(selected)
        positions = _positions(farm)
        if len(actions) != len(positions):
            raise ValueError('selected_worker_shape_mismatch')
        post_positions = _positions(post_farm)
        if post_positions != positions:
            # A FEED is stationary; changing a row that also changed worker
            # identity/position means the completed snapshot is not our contract.
            raise ValueError('post_unit_position_mismatch')

        care_targets = {
            key for position, action in zip(positions, actions)
            if isinstance(action, list) and action and action[0] == 'CARE'
            for key in [_animal_key(farm, position)] if key is not None
        }
        feed_actors = {}
        for actor, (position, action) in enumerate(zip(positions, actions)):
            if not (isinstance(action, list) and action and action[0] == 'FEED'):
                continue
            key = _animal_key(farm, position)
            if key is not None:
                feed_actors.setdefault(key, []).append(actor)
        if not feed_actors:
            return selected, report

        target_reports = []
        candidates = {}
        for key, actors in sorted(feed_actors.items()):
            position, animal = key
            status = {'position': list(position), 'animal': animal,
                      'actors': list(actors), 'eligible': False}
            if len(actors) != 1:
                status['reason'] = 'shared_feed_target'
                target_reports.append(status)
                continue
            pre = _tile(farm, position)
            post = _tile(post_farm, position)
            if bool(pre.get('fed_today')):
                status['reason'] = 'animal_already_fed'
            elif _whole(pre.get('consecutive_unfed', 0)) != 0:
                status['reason'] = 'animal_already_missed_feed'
            elif bool(pre.get('cared_today')) or _whole(pre.get('pending_care_bonus', 0)):
                status['reason'] = 'care_value_requires_feed'
            elif key in care_targets:
                status['reason'] = 'same_turn_care_requires_feed'
            elif (not isinstance(post, dict) or post.get('animal') != animal
                  or not bool(post.get('fed_today'))):
                # Proves the incumbent FEED consumed wheat and set the engine
                # state.  Failed/no-op FEED actions are not counted as savings.
                status['reason'] = 'incumbent_feed_not_proven'
            else:
                status['eligible'] = True
                status['reason'] = 'awaiting_rescue_certificate'
                candidates[key] = actors[0]
            target_reports.append(status)
        report['targets'] = target_reports
        if not candidates:
            report['reason'] = 'no_safe_day_close_feed'
            return selected, report

        window = _feed_window(mechanics, observation, cfg, selected, post_farm,
                              post_private, route, checkpoints)
        if not window.get('crosses_reset'):
            raise ValueError('feed_window_does_not_cross_reset')
        future = {}
        for obligation in window.get('obligations', []):
            for feed in obligation.get('feeds', []):
                key = (tuple(feed['position']), feed['animal'])
                future.setdefault(key, []).append(dict(feed))
        approved = {key: actor for key, actor in candidates.items() if key in future}
        if not approved:
            report.update(reason='no_certified_next_day_rescue', window=window)
            return selected, report

        # The existing feed-window proof does not itself debit the current
        # market row.  Establish that all future pickup/feed obligations are
        # already backed by observed physical wheat after current sales.  The
        # wheat saved by this proposal is deliberately *not* credited here.
        orders = selected.get('market') or []
        room = _current_room_bound(mechanics, post_private, orders, True)
        shed_wheat = _current_wheat_after_sales(post_private, orders, maximum)
        carry_wheat = sum(_whole(inv.get('WHEAT', 0))
                          for inv in post_private['inventories'])
        guaranteed = shed_wheat + carry_wheat
        required = _whole(window.get('required_wheat', 0))
        if guaranteed < required:
            raise ValueError('next_day_rescue_feed_not_prepaid')

        # Each approved target is unique and its incumbent FEED is proven to
        # have succeeded, so suppressing it preserves exactly one extra wheat.
        # Make sure those extra carried units also fit at the EOD shed delivery.
        saved = len(approved)
        if room['after_delivery_upper'] + saved > capacity:
            raise ValueError('saved_wheat_would_overflow_at_reset')

        result = deepcopy(selected)
        skipped = []
        for key, actor in sorted(approved.items(), key=lambda item: item[1]):
            if actor == 0:
                result['farmer'] = ['PASS']
            else:
                result['hands'][actor - 1] = ['PASS']
            skipped.append({'actor': actor, 'position': list(key[0]),
                            'animal': key[1], 'next_day_feeds': future[key]})

        for status in target_reports:
            key = (tuple(status['position']), status['animal'])
            if key in approved:
                status['eligible'] = True
                status['reason'] = 'certified_one_day_skip'
            elif status['eligible']:
                status['eligible'] = False
                status['reason'] = 'no_certified_next_day_rescue'
        report.update(
            changed=True,
            certified=True,
            reason='skip_one_feed_day_with_prepaid_rescue',
            saved_wheat_units=saved,
            skipped=skipped,
            window=window,
            room=room,
            guaranteed_wheat_after_current_sales=guaranteed,
            required_next_day_wheat=required,
            future_purchase_credit=0,
            saved_wheat_rescue_credit=0,
        )
        return result, report
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, AttributeError) as error:
        report['reason'] = str(error)
        return selected, report
