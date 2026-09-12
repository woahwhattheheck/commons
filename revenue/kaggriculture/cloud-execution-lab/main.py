# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint. Feature choices are deterministic package data."""
_INSTANCE = None
_SPATIAL_RECOVERY = None
_SPATIAL_RECOVERY_FIELDS = ('_committed', 'sale_obligation', 'receipt_events', 'crop_intent')


def _install_funding_eod_boundary(module):
    """Fail closed before a represented funding replay crosses official EOD."""
    from functools import wraps

    current = None if module is None else getattr(module, '_funding_trace', None)
    if not callable(current):
        raise RuntimeError('loaded frozen seller has no funding trace')
    if getattr(current, '_titan_funding_eod_boundary', False):
        return current

    @wraps(current)
    def guarded(obs, config, farm, private, route, now, end, current_market,
                stress_units=0):
        turns = config.get('turnsPerDay')
        if type(turns) is not int or turns != 24:
            raise ValueError('funding replay requires plain-int turnsPerDay == 24')
        if now // turns != end // turns:
            raise ValueError('funding replay cannot cross end-of-day lifecycle')
        return current(obs, config, farm, private, route, now, end,
                       current_market, stress_units=stress_units)

    guarded._titan_funding_eod_boundary = True
    guarded._titan_funding_eod_original = current
    module._funding_trace = guarded
    return guarded


def _new_instance(root, feature_data):
    """Construct the configured runtime and its opt-in economic admission."""
    from titan_runtime import TitanAgent, Features, load
    feature_data = dict(feature_data)
    town_enabled = bool(feature_data.pop('town_procurement', False))
    features = Features(**feature_data)
    if town_enabled and (features.consumer != 'frozen' or features.terminal_route):
        raise ValueError('town_procurement is the tested nonterminal frozen composition')

    class FinalPressureAgent(TitanAgent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.town_procurement_enabled = town_enabled
            self._finalizer_checkpoint = None
            self._staged_spatial_recovery = None

        def _export_spatial_recovery(self):
            """Copy only state certified before the next entrypoint call starts.

            SpatialTempo has transient proposal fields which can be half-mutated
            by a late outer deadline. Those are intentionally absent here. The
            four retained fields are committed/observed cross-turn state whose
            owning actions or receipts were already returned before this call.
            """
            from copy import deepcopy
            spatial = getattr(self, 'spatial', None)
            if spatial is None:
                return None
            return {name: deepcopy(getattr(spatial, name, None))
                    for name in _SPATIAL_RECOVERY_FIELDS}

        def _stage_spatial_recovery(self, snapshot):
            """Stage a bounded checkpoint for the next lazy spatial initialize."""
            from copy import deepcopy
            if snapshot is None:
                self._staged_spatial_recovery = None
                return True
            if (not isinstance(snapshot, dict)
                    or set(snapshot) != set(_SPATIAL_RECOVERY_FIELDS)):
                self._staged_spatial_recovery = None
                return False
            self._staged_spatial_recovery = deepcopy(snapshot)
            return True

        def _restore_spatial_recovery(self):
            """Restore certified state without restoring interrupted proposals."""
            from copy import deepcopy
            snapshot = self._staged_spatial_recovery
            self._staged_spatial_recovery = None
            spatial = getattr(self, 'spatial', None)
            if snapshot is None or spatial is None:
                return
            for name in _SPATIAL_RECOVERY_FIELDS:
                setattr(spatial, name, deepcopy(snapshot[name]))

        def _initialize(self):
            # Keep TitanAgent's normal lazy construction and controller install.
            # Install the lifecycle guard only after the exact relocated seller
            # module is loaded, but before any represented funding trace runs.
            super()._initialize()
            import sys
            selected_module = sys.modules.get(self.consumer.__class__.__module__)
            _install_funding_eod_boundary(selected_module)
            # Restore the bounded journal only after a fresh SpatialTempo exists,
            # but before production consumes the new public observation.
            self._restore_spatial_recovery()

        def _checkpoint_finalizer(self, obs, selected, stage):
            """Publish only a fully returned current-turn action stage.

            The outer entrypoint timer can interrupt later finalizers. Keeping
            this private action-only checkpoint lets that guard return the last
            completed bytes without trusting any partially mutated runtime state;
            the instance is still discarded after whole-call cancellation.
            """
            from copy import deepcopy
            self._finalizer_checkpoint = {
                'step': int(obs['step']),
                'player': int(obs['player']),
                'stage': str(stage),
                'action': deepcopy(selected),
            }

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

        def _feed_stock_selected(self, obs, cfg, selected):
            # Enter the first late market finalizer with a current-turn action
            # already checkpointed. If this helper is cancelled, the outer guard
            # can keep all earlier completed crop/stock work instead of dropping
            # back to the raw producer selection.
            self._checkpoint_finalizer(obs, selected, 'pre_feed_stock')
            returned = super()._feed_stock_selected(obs, cfg, selected)
            self._checkpoint_finalizer(obs, returned, 'feed_stock')
            return returned

        def _early_capital_selected(self, obs, cfg, selected):
            # TitanAgent._finish_production calls this after every stock/crop
            # guard and before every receipt/history commit. Reuse that stable
            # boundary instead of copying the finalizer or mutating afterward.
            self._checkpoint_finalizer(obs, selected, 'pre_early_capital')
            returned = super()._early_capital_selected(obs, cfg, selected)
            self._checkpoint_finalizer(obs, returned, 'early_capital')
            completed = self.diagnostics.get('status') == 'completed'
            if completed:
                self._final_pressure_boundary = True
                try:
                    returned = super()._market_pressure_selected(obs, cfg, returned)
                finally:
                    self._final_pressure_boundary = False
                self._checkpoint_finalizer(obs, returned, 'market_pressure')
            if self.town_procurement_enabled:
                from town_procurement import apply
                returned, report = apply(obs, returned, cfg, completed=completed)
                self.diagnostics['town_procurement'] = report
                self._checkpoint_finalizer(obs, returned, 'town_procurement')
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
    """Return the latest completed current action, else visible-state fallback."""
    from copy import deepcopy
    cfg = dict(configuration or {})
    obs = dict(observation)
    step = obs.get('step')
    if step is None:
        step = int(obs['day'])*int(cfg.get('turnsPerDay', 24))+int(obs['hour'])
    obs['step'] = int(step)

    action = None
    checkpoint = None if instance is None else getattr(instance, '_finalizer_checkpoint', None)
    if (isinstance(checkpoint, dict)
            and checkpoint.get('step') == obs['step']
            and checkpoint.get('player') == int(obs['player'])
            and checkpoint.get('action') is not None):
        action = deepcopy(checkpoint['action'])
    if action is None:
        selected = None if instance is None else getattr(instance, 'selected', None)
        if selected is not None:
            action = deepcopy(selected)
    if action is not None:
        if bool(getattr(instance, 'town_procurement_enabled', False)):
            from town_procurement import suppress_confirmed
            action, _ = suppress_confirmed(obs, action, cfg)
        return action

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
    checkpoint = getattr(instance, '_finalizer_checkpoint', None)
    if isinstance(checkpoint, dict) and checkpoint.get('stage') is not None:
        diagnostics['entrypoint_checkpoint_stage'] = checkpoint['stage']
    diagnostics.update(status='deadline_fallback', fallback_stage=stage,
                       entrypoint_guard=True,
                       elapsed_seconds=time.perf_counter()-started)
    instance.diagnostics = diagnostics


def _spatial_recovery_journal(snapshot, step):
    """Bind a pre-call spatial snapshot to the public step that was returned."""
    if snapshot is None:
        return None
    from copy import deepcopy
    return {'last_step': int(step), 'state': deepcopy(snapshot)}


def agent(observation, configuration=None):
    global _INSTANCE, _SPATIAL_RECOVERY
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

    journal = _SPATIAL_RECOVERY if isinstance(_SPATIAL_RECOVERY, dict) else None
    journal_step = None if journal is None else journal.get('last_step')
    # Step zero is both a match boundary and a legal same-step retry. Reuse an
    # instance (or a recovery journal) that already returned step zero; only a
    # later-step -> 0 transition proves that retained state belongs to old play.
    previous_step = (getattr(_INSTANCE, '_entrypoint_last_step', None)
                     if _INSTANCE is not None else journal_step)
    match_reset = step == 0 and previous_step not in (None, 0)
    if match_reset:
        _SPATIAL_RECOVERY = None
        journal = None
    replace = (_INSTANCE is None or match_reset)
    instance = None if replace else _INSTANCE

    # Snapshot only state certified before this call mutates the live instance.
    # If a prior outer timeout already discarded the instance, carry its saved
    # journal through another construction/prelude cancellation unchanged.
    spatial_recovery = None
    if not match_reset:
        if instance is not None:
            exporter = getattr(instance, '_export_spatial_recovery', None)
            if callable(exporter):
                spatial_recovery = exporter()
        elif (isinstance(journal, dict)
              and set(journal) == {'last_step', 'state'}):
            from copy import deepcopy
            spatial_recovery = deepcopy(journal['state'])

    feature_data = (json.loads((root/'TITAN-CONFIG.json').read_text())
                    if replace else None)
    town_enabled = (bool(feature_data.get('town_procurement', False)) if replace
                    else bool(getattr(instance, 'town_procurement_enabled', False)))
    if town_enabled:
        receipt_obs = dict(observation)
        receipt_obs['step'] = step
        import town_procurement
        town_procurement.observe(receipt_obs)
    from titan_runtime import deadline
    budget = (float(instance.features.budget_seconds) if instance is not None
              else float(feature_data.get('budget_seconds', 1.0)))
    reserve = (float(instance.features.reserve_seconds) if instance is not None
               else float(feature_data.get('reserve_seconds', 0.01)))
    if not 0 <= reserve < budget <= 1:
        raise ValueError('invalid action deadline')
    # TitanAgent clears this itself, but clear both current-action publications
    # before arming the outer timer so an immediate cancellation cannot reuse a
    # prior step (or an earlier retry of this same public step).
    if instance is not None:
        instance.selected = None
        if hasattr(instance, '_finalizer_checkpoint'):
            instance._finalizer_checkpoint = None
    fallback = _entrypoint_fallback(None, observation, cfg, deadline)
    remaining = budget-(time.perf_counter()-entry_started)
    if remaining <= 0:
        # Construction is runtime work. Once the prelude has exhausted the
        # budget, starting a fresh lazy controller outside any timer would turn
        # this fallback branch into an unbounded call. Leave the instance absent;
        # the next visible observation can initialize it normally.
        if replace:
            _SPATIAL_RECOVERY = _spatial_recovery_journal(spatial_recovery, step)
            _INSTANCE = None
            return fallback
        obs = dict(observation)
        obs['step'] = step
        if instance.features.consumer == 'frozen':
            instance.ready = False
        instance.selected = None
        instance.post = None
        instance._remember_seller_fallback(obs)
        instance._entrypoint_last_step = step
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
                stager = getattr(instance, '_stage_spatial_recovery', None)
                if callable(stager):
                    stager(spatial_recovery)
                _INSTANCE = instance
            stage = 'entrypoint_runtime'
            output = instance.act(observation, cfg, entry_started=entry_started)
            # Publish only after a complete inner return. A foreign exception or
            # outer cancellation keeps the prior marker or discards the instance.
            instance._entrypoint_last_step = step
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
        # object to the next observation; reconstruct from public state plus the
        # pre-call committed spatial journal, never current-call proposals.
        _SPATIAL_RECOVERY = _spatial_recovery_journal(spatial_recovery, step)
        _INSTANCE = None
        return fallback
    _SPATIAL_RECOVERY = None
    return output
