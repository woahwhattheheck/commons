# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
"""Canonical TITAN entrypoint. Feature choices are deterministic package data."""
_INSTANCE = None


def _new_instance(root, feature_data):
    """Construct the configured runtime and its opt-in economic admission."""
    from titan_runtime import TitanAgent, Features, load
    features = Features(**feature_data)

    class FinalPressureAgent(TitanAgent):
        """Keep public-curve pressure at the returned-action boundary.

        Pressure was originally the final SELL transform. Later stock, crop,
        feed and capital repairs are now allowed to finish first, then pressure
        may reorder only the resulting supported SELL blocks. Deadline fallback
        keeps its existing path and does not start a new optional transform.
        """
        def _market_pressure_selected(self, obs, cfg, selected):
            if not getattr(self, '_final_pressure_boundary', False):
                return selected
            return super()._market_pressure_selected(obs, cfg, selected)

        def _finish_production(self, obs, returned, cfg=None):
            # Mirror TitanAgent's finalization boundary so the pressure result is
            # what every receipt/history owner observes, rather than mutating the
            # action after those ledgers have committed it.
            if self.spatial is not None:
                self.spatial.observe_crop_receipts(
                    obs, None if self.history is None else self.history.fill_result,
                    self.controller.cur)
            if self.spatial is not None:
                returned = self.spatial.guard_returned(
                    obs, returned,
                    repair_fallback=self.diagnostics.get('status') == 'deadline_fallback')
            post = self._selected_snapshot(obs, returned) if self.history is not None else None
            if self.spatial is not None:
                returned = self.spatial.guard_crop_returned(obs, returned, post)
            returned = self._feed_stock_selected(obs, cfg or {}, returned)
            returned = self._early_capital_selected(obs, cfg or {}, returned)
            if self.diagnostics.get('status') == 'completed':
                self._final_pressure_boundary = True
                try:
                    returned = super()._market_pressure_selected(
                        obs, cfg or {}, returned)
                finally:
                    self._final_pressure_boundary = False
            if self.quadrant is not None:
                self.quadrant.finish(obs, returned)
                self.diagnostics['fourth_quadrant_events'] = list(self.quadrant.events)
                if self._quadrant_admission is not None:
                    self.diagnostics['fourth_quadrant_admission'] = deepcopy(
                        self._quadrant_admission.last_report)
            if self.spatial is not None:
                self.spatial.finish(obs, returned, post)
                self.spatial.finish_crop(
                    obs, returned, post, self.controller.cur,
                    seller_completed=self.diagnostics.get('status') == 'completed')
                self.diagnostics['route_events'] = list(self.spatial.events)
                self.diagnostics['idle_fertilizer_receipts'] = list(
                    self.spatial.receipt_events)
                self.diagnostics['idle_fertilizer_obligation'] = deepcopy(
                    self.spatial.sale_obligation)
                if self.features.crop_release:
                    self.diagnostics['crop_release'] = deepcopy(self.spatial.crop_intent)
                    self.diagnostics['crop_release_action'] = deepcopy(
                        self.spatial.crop_report)
            if self.history is not None:
                needed = (
                    self.features.terminal_history or
                    (self.spatial is not None and
                     (self.spatial.sale_obligation is not None or
                      self.spatial.crop_intent is not None))
                )
                self.history.remember(
                    obs, cfg or {}, returned, post if needed else None)
                self.diagnostics['history'] = self.history.diagnostics
            return returned

    admission = None
    if features.fourth_quadrant:
        source = root/'funded_payback.py'
        if not source.is_file():
            # Source-tree execution retains ECON's own attributed location;
            # the canonical archive maps those exact bytes beside main.py.
            source = root/'../cloud-economic-stress/funded_payback/funded_payback.py'
        module = load('_titan_funded_payback', source, cache=True)
        adapter = load('_titan_funded_payback_runtime',
                       root/'funded_payback_runtime.py', cache=True)
        admission = adapter.make_admission(module.FundedPaybackAdmission)(
            seconds=features.budget_seconds, max_proposals=24)
    return FinalPressureAgent(features, fourth_quadrant_admission=admission)


def agent(observation, configuration=None):
    global _INSTANCE
    import time
    entry_started = time.perf_counter()
    from pathlib import Path
    import json
    import sys
    cfg = dict(configuration or {})
    path = globals().get('__file__') or cfg.get('__raw_path__')
    if not path:
        raise ValueError('Entrypoint path required')
    root = Path(path).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    step = observation.get('step')
    if step is None:
        step = int(observation['day'])*int(cfg.get('turnsPerDay', 24))+int(observation['hour'])
    if _INSTANCE is None or int(step) == 0:
        _INSTANCE = _new_instance(root, json.loads((root/'TITAN-CONFIG.json').read_text()))
    return _INSTANCE.act(observation, cfg, entry_started=entry_started)
