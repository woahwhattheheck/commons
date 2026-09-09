# SPDX-License-Identifier: Apache-2.0
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

        def _early_capital_selected(self, obs, cfg, selected):
            # TitanAgent._finish_production calls this after every stock/crop
            # guard and before every receipt/history commit. Reuse that stable
            # boundary instead of copying the finalizer or mutating afterward.
            returned = super()._early_capital_selected(obs, cfg, selected)
            if self.diagnostics.get('status') != 'completed':
                return returned
            self._final_pressure_boundary = True
            try:
                return super()._market_pressure_selected(obs, cfg, returned)
            finally:
                self._final_pressure_boundary = False

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
