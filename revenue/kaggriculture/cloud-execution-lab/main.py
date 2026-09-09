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
        The physical-equivalence cardinality guard runs after pressure so no
        later transform can reintroduce impossible HIRE or worker suffixes.
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
                returned = super()._market_pressure_selected(obs, cfg, returned)
            finally:
                self._final_pressure_boundary = False
            # The engine silently ignores unavailable workers and failed HIREs.
            # Reconcile only those exact no-ops after every policy transform,
            # without mutating the incumbent route or calling another policy.
            import mechanics
            from hire_cardinality import reconcile_hire_cardinality
            returned, report = reconcile_hire_cardinality(
                mechanics, obs, cfg, returned)
            self.diagnostics['hire_cardinality'] = report
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


def _entrypoint_fallback(instance, observation, configuration, deadline):
    """Return a completed current action, otherwise the visible-state fallback."""
    from copy import deepcopy
    selected = None if instance is None else getattr(instance, 'selected', None)
    if selected is not None:
        return deepcopy(selected)
    cfg = dict(configuration or {})
    obs = dict(observation)
    step = obs.get('step')
    if step is None:
        step = int(obs['day'])*int(cfg.get('turnsPerDay', 24))+int(obs['hour'])
    obs['step'] = int(step)
    last = int(cfg.get('episodeSteps', 720))-2
    return (deadline.terminal_liquidation_fallback(obs, cfg)
            if obs['step'] == last else deadline.legal_pass(obs))


def _record_entrypoint_deadline(instance, stage, started):
    """Retain both the inner receipt and the whole-call cancellation boundary."""
    if instance is None:
        return
    import time
    diagnostics = dict(getattr(instance, 'diagnostics', {}) or {})
    if diagnostics.get('fallback_stage') is not None:
        diagnostics['inner_fallback_stage'] = diagnostics['fallback_stage']
    if diagnostics.get('elapsed_seconds') is not None:
        diagnostics['inner_elapsed_seconds'] = diagnostics['elapsed_seconds']
    diagnostics.update(status='deadline_fallback', fallback_stage=stage,
                       entrypoint_guard=True,
                       elapsed_seconds=time.perf_counter()-started)
    instance.diagnostics = diagnostics


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
    step = int(step)
    replace = _INSTANCE is None or step == 0
    instance = None if replace else _INSTANCE
    feature_data = (json.loads((root/'TITAN-CONFIG.json').read_text())
                    if replace else None)
    from titan_runtime import deadline
    budget = (float(instance.features.budget_seconds) if instance is not None
              else float(feature_data.get('budget_seconds', 1.0)))
    reserve = (float(instance.features.reserve_seconds) if instance is not None
               else float(feature_data.get('reserve_seconds', 0.01)))
    if not 0 <= reserve < budget <= 1:
        raise ValueError('invalid action deadline')
    # TitanAgent clears this itself, but clear it before arming the outer timer
    # so an immediate whole-call cancellation cannot reuse the prior step.
    if instance is not None:
        instance.selected = None
    fallback = _entrypoint_fallback(None, observation, cfg, deadline)
    remaining = budget-(time.perf_counter()-entry_started)
    if remaining <= 0:
        # Construction is runtime work. Once the prelude has exhausted the
        # budget, starting a fresh lazy controller outside any timer would turn
        # this fallback branch into an unbounded call. Leave the instance absent;
        # the next visible observation can initialize it normally.
        if replace:
            _INSTANCE = None
            return fallback
        obs = dict(observation)
        obs['step'] = step
        if instance.features.consumer == 'frozen':
            instance.ready = False
        instance.selected = None
        instance.post = None
        instance._remember_seller_fallback(obs)
        instance.diagnostics = {
            'consumer': instance.features.consumer,
            'parent_calls': 0,
            'entrypoint_prelude_seconds': time.perf_counter()-entry_started,
            'status': 'deadline_fallback',
            'fallback_stage': 'entrypoint_prelude',
            'elapsed_seconds': time.perf_counter()-entry_started,
            'act_cpu_seconds': 0.0,
            'entrypoint_guard': True,
        }
        return fallback
    timer = deadline._DeadlineTimer(remaining)
    stage = 'entrypoint_construction' if replace else 'entrypoint_runtime'
    try:
        with timer:
            if replace:
                instance = _new_instance(root, feature_data)
                _INSTANCE = instance
            stage = 'entrypoint_runtime'
            output = instance.act(observation, cfg, entry_started=entry_started)
    except deadline.DeadlineExceeded as error:
        if error is not timer.expired:
            raise
        inner = getattr(instance, 'diagnostics', {}) if instance is not None else {}
        if (getattr(instance, 'selected', None) is not None
                and inner.get('status') in ('completed', 'deadline_fallback')):
            stage = 'entrypoint_finalization'
        fallback = _entrypoint_fallback(instance, observation, cfg, deadline)
        _record_entrypoint_deadline(instance, stage, entry_started)
        if instance is not None:
            instance.ready = False
        # Finalization may have been interrupted mid-mutation. Never expose that
        # object to the next observation; reconstruction starts from public state.
        _INSTANCE = None
        return fallback
    return output
