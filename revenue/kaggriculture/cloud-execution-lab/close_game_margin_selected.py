# SPDX-License-Identifier: Apache-2.0
"""Opt-in late-game cash-margin objective for the canonical frozen seller.

The candidate reuses FrozenSelected's exact feasible plan family. It changes
only the deterministic rank among plans already admitted by the incumbent
seller, and restores the canonical rank function after each callback.
"""
from __future__ import annotations

import mechanics as m
import frozen_selected as selected
from close_game_margin import build_margin_context, rank_option
from selected_sell_core import shared_market_path


class CloseGameMarginSelected(selected.FrozenSelected):
    """FrozenSelected with an opt-in public close-game margin ranking policy."""

    def __init__(self, mode="off", *, window=96, buffer=0):
        super().__init__()
        self.close_game_margin_mode = str(mode or "off").strip().lower()
        self.close_game_margin_window = window
        self.close_game_margin_buffer = buffer

    @staticmethod
    def _visible_rival_supply(obs, item):
        """Bound currently visible rival output without using hidden shed state."""
        rival = obs['farms'][1-int(obs['player'])]
        visible = 0
        for row in rival['tiles']:
            for tile in row:
                if not isinstance(tile, dict):
                    continue
                product = (tile.get('crop') if tile.get('kind') == 'PLANT'
                           else m.ANIMALS.get(tile.get('animal'), {}).get('product'))
                if product == item:
                    visible += max(0, int(tile.get('yield_units', 0)))
        return min(100, visible)

    def _public_liquidation_bound(self, obs, config, now, shops):
        """Exact immediate-sale receipt for visible rival standing output.

        This is a named public stress bound, not a claim about private rival
        stock. It intentionally ignores hidden inventory and therefore is used
        only to select among already-safe seller plans.
        """
        inventory = obs['market']['inventory']
        params = obs['market'].get('params')
        total = 0
        for item in selected.PRODUCTS:
            quantity = self._visible_rival_supply(obs, item)
            if quantity <= 0:
                continue
            model = shared_market_path(
                item, int(inventory[item]), params, shops, config, now, now)
            cash, _ending = model.single(int(inventory[item]), int(quantity))
            total += max(0, int(cash))
        return total

    def _margin_context(self, obs, config):
        mode = self.close_game_margin_mode
        if mode == 'off':
            return None
        try:
            now = int(obs['step'])
            last = int(config.get('episodeSteps', 720)) - 2
            player = int(obs['player'])
            own_cash = obs['farms'][player]['money']
            rival_cash = obs['farms'][1-player]['money']
            if (isinstance(own_cash, bool) or not isinstance(own_cash, int)
                    or isinstance(rival_cash, bool) or not isinstance(rival_cash, int)):
                return {'active': False, 'reason': 'non_plain_public_cash', 'mode': mode}
            shops = obs.get('town', {}).get('unlocked_shops', [])
            rival_bound = self._public_liquidation_bound(obs, config, now, shops)
            return build_margin_context(
                mode=mode, now=now, last=last,
                own_cash=own_cash, rival_cash=rival_cash,
                rival_liquidation_bound=rival_bound,
                window=self.close_game_margin_window,
                buffer=self.close_game_margin_buffer)
        except (KeyError, TypeError, ValueError, OverflowError):
            return {'active': False, 'reason': 'invalid_public_evidence', 'mode': mode}

    def transform(self, obs, config, base):
        context = self._margin_context(obs, config)
        if not context or not context.get('active'):
            out = super().transform(obs, config, base)
            if context is not None:
                self.diagnostics['close_game_margin'] = {
                    'context': dict(context), 'reports': []}
            return out

        incumbent_rank = selected.seller_choice_rank
        reports = []

        def margin_rank(info):
            eligible, base_rank = incumbent_rank(info)
            rank, report = rank_option(info, context, base_rank)
            reports.append(report)
            return eligible, rank

        # Kaggriculture callbacks are serialized, but still restore the exact
        # module-global function in a finally block so deadline exceptions cannot
        # leak this experimental objective into a later callback.
        selected.seller_choice_rank = margin_rank
        try:
            out = super().transform(obs, config, base)
        finally:
            selected.seller_choice_rank = incumbent_rank
        self.diagnostics['close_game_margin'] = {
            'context': dict(context), 'reports': reports}
        return out
