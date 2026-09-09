# SPDX-License-Identifier: Apache-2.0
"""Isolated Titan runtime binding for the KESTREL early-capital candidate."""
from titan_runtime import TitanAgent
from kestrel_early_capital import order_early_capital


class KestrelTitanAgent(TitanAgent):
    """Canonical Titan with only the final early-capital call overridden."""

    def _early_capital_selected(self, obs, cfg, selected):
        if (not getattr(self.features, 'early_capital', False)
                or self.features.consumer != 'frozen'
                or self.features.terminal_route):
            return selected
        import mechanics as mechanics_mod
        from scheduler import parent

        # Use the exact completed unit snapshot when FrozenSelected captured it.
        # The candidate helper can reconstruct the same state with the vendored
        # unit primitive when a queue has no capture-triggering operating stock.
        post_unit = self._selected_snapshot(obs, selected)
        result, report = order_early_capital(
            mechanics_mod,
            obs,
            cfg,
            selected,
            self.controller.R[self.controller.cur],
            parent.DECISIONS,
            post_unit=post_unit,
        )
        report['runtime_binding'] = (
            'selected_post_units' if post_unit is not None
            else 'official_unit_replay'
        )
        self.diagnostics['early_capital'] = report
        return result
