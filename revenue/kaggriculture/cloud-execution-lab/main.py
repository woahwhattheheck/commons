# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint. Feature choices are deterministic package data."""
_INSTANCE = None


def _new_instance(root, feature_data):
    """Construct the configured runtime and its opt-in economic admission."""
    from titan_runtime import TitanAgent, Features, load
    features = Features(**feature_data)
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
    return TitanAgent(features, fourth_quadrant_admission=admission)


def _entrypoint_fallback(instance, observation, configuration, deadline):
    """Return only a completed producer action or a visible-state legal fallback."""
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
    """Leave an inspectable receipt on the discarded instance."""
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
    if replace:
        # A cancelled step-zero construction must not leave the prior game's
        # instance available to a later nonzero call.
        _INSTANCE = None
    from titan_runtime import deadline
    owner = instance
    budget = (float(owner.features.budget_seconds) if owner is not None
              else float(feature_data.get('budget_seconds', 1.0)))
    reserve = (float(owner.features.reserve_seconds) if owner is not None
               else float(feature_data.get('reserve_seconds', 0.01)))
    if reserve < 0 or budget <= reserve:
        raise ValueError('budget_seconds must exceed non-negative reserve_seconds')
    # Never reuse the prior step's selected action as a current fallback.
    if instance is not None:
        instance.selected = None
    fallback = _entrypoint_fallback(None, observation, cfg, deadline)
    remaining = budget-reserve-(time.perf_counter()-entry_started)
    if remaining <= 0:
        _record_entrypoint_deadline(instance, 'entrypoint_prelude', entry_started)
        _INSTANCE = None
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
        _INSTANCE = None
        return fallback
    # Main-thread signal delivery cannot interrupt every native call. Refuse a
    # result that crossed the same internal boundary even if the timer callback
    # could not run until after that call returned.
    if time.perf_counter()-entry_started >= budget-reserve:
        fallback = _entrypoint_fallback(instance, observation, cfg, deadline)
        _record_entrypoint_deadline(instance, 'entrypoint_postcheck', entry_started)
        _INSTANCE = None
        return fallback
    return output
