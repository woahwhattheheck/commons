# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint. Feature choices are deterministic package data."""
_INSTANCE = None

def _nonnegative_int(value):
    """Parse an internal action quantity without admitting bool or malformed rows."""
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def _sell_prefix_totals(action, limit):
    """Return valid positive SELL units in the exact raw engine prefix."""
    try:
        bound = max(0, int(limit))
    except (TypeError, ValueError, OverflowError):
        bound = 0
    market = action.get('market', []) if isinstance(action, dict) else []
    if not isinstance(market, (list, tuple)):
        return {}
    totals = {}
    for order in market[:bound]:
        if (not isinstance(order, (list, tuple)) or len(order) < 3
                or order[0] != 'SELL' or not isinstance(order[1], str)):
            continue
        quantity = _nonnegative_int(order[2])
        if quantity:
            totals[order[1]] = totals.get(order[1], 0)+quantity
    return totals


def _planned_due(rows, step):
    total = 0
    for row in rows if isinstance(rows, (list, tuple)) else ():
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        try:
            when = int(row[0])
        except (TypeError, ValueError, OverflowError):
            continue
        if when <= step:
            total += _nonnegative_int(row[1])
    return total


def _reconcile_returned_sell_carry(before, after, authored, returned, step, limit):
    """Carry pre-existing due SELL units removed by late returned-action guards.

    FrozenSelected settles its planning ledger against ``authored`` before the
    canonical finalizer protects feed/crop stock and reapplies pressure. The
    engine, however, observes only ``returned[:maxMarketOrdersPerTurn]``. Bind
    the next-turn carry to that exact raw prefix without creating obligations
    for baseline or opportunistic SELL quantities.
    """
    from copy import deepcopy
    checkpoint = deepcopy(after)
    report = {
        'changed': False,
        'step': int(step),
        'prefix_limit': _nonnegative_int(limit),
        'authored_sell': _sell_prefix_totals(authored, limit),
        'returned_sell': _sell_prefix_totals(returned, limit),
        'items': {},
    }
    if not isinstance(before, dict) or not isinstance(checkpoint, dict):
        report['reason'] = 'missing_seller_checkpoint'
        return checkpoint, report
    planned_before = before.get('planned', {})
    planned_after = checkpoint.setdefault('planned', {})
    pending_after = checkpoint.setdefault('pending', {})
    if not isinstance(planned_before, dict) or not isinstance(planned_after, dict):
        report['reason'] = 'invalid_seller_checkpoint'
        return checkpoint, report
    authored_sell = report['authored_sell']
    returned_sell = report['returned_sell']
    now = int(step)
    for item, rows in planned_before.items():
        if not isinstance(item, str):
            continue
        due = _planned_due(rows, now)
        removed = max(0, authored_sell.get(item, 0)-returned_sell.get(item, 0))
        carry = min(due, removed)
        if not carry:
            continue
        after_rows = planned_after.get(item, [])
        existing_due = _planned_due(after_rows, now)
        added = max(0, carry-existing_due)
        report['items'][item] = {
            'due_before': due,
            'removed_after_guards': removed,
            'already_carried': min(carry, existing_due),
            'carried_to_next_turn': added,
        }
        if not added:
            continue
        by_step = {}
        for row in after_rows if isinstance(after_rows, (list, tuple)) else ():
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            try:
                when = int(row[0])
            except (TypeError, ValueError, OverflowError):
                continue
            quantity = _nonnegative_int(row[1])
            if quantity:
                by_step[when] = by_step.get(when, 0)+quantity
        by_step[now+1] = by_step.get(now+1, 0)+added
        planned_after[item] = sorted(by_step.items())
        pending_after[item] = _nonnegative_int(pending_after.get(item, 0))+added
        report['changed'] = True
    if not report['items']:
        report['reason'] = 'no_removed_due_sell'
    return checkpoint, report



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
        def act(self, observation, configuration=None, *, entry_started=None):
            # Capture only intent that predates this action. New plans selected
            # during this action cannot become synthetic carry obligations.
            from copy import deepcopy
            if self.features.consumer != 'frozen':
                self._seller_state_before_action = None
            elif self.ready:
                self._seller_state_before_action = self._seller_state(self.consumer)
            else:
                self._seller_state_before_action = deepcopy(self._completed_seller_state)
            try:
                return super().act(observation, configuration,
                                   entry_started=entry_started)
            finally:
                self._seller_state_before_action = None

        def _finish_production(self, obs, returned, cfg=None):
            from copy import deepcopy
            authored = deepcopy(returned)
            result = super()._finish_production(obs, returned, cfg)
            if self.diagnostics.get('status') != 'completed':
                return result
            checkpoint, report = _reconcile_returned_sell_carry(
                getattr(self, '_seller_state_before_action', None),
                self._completed_seller_state, authored, result, int(obs['step']),
                (cfg or {}).get('maxMarketOrdersPerTurn', 10))
            self.diagnostics['returned_sell_carry'] = report
            if report['changed']:
                # TitanAgent committed before calling the finalizer. Keep its
                # live object and recovery checkpoint on the same corrected
                # planning ledger for both normal and reconstructed next turns.
                self.consumer.planned = {
                    item:list(rows) for item,rows in checkpoint['planned'].items()
                }
                self.consumer.pending = dict(checkpoint['pending'])
                self._completed_seller_state = checkpoint
            return result

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
