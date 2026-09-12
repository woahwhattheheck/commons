# SPDX-License-Identifier: Apache-2.0
"""Bind shipped history and terminal consumers to TITAN's selected-action path."""
from copy import copy,deepcopy
from pathlib import Path
import random
import sys
from titan_runtime import load

HERE=Path(__file__).resolve().parent/'reference/titan-history'


class TerminalHistoryJoin:
    def __init__(self, *, period=24, hypotheses=None, tie_break='baseline', terminal_enabled=True):
        def dependency(name):
            return load('_titan_history_'+name,HERE/(name+'.py'),cache=True)
        self.dependency=dependency
        self.m=dependency('terminal_mechanics')
        bridge=dependency('selected_action_history')
        fills=dependency('observed_fills');flow=dependency('flow')
        scenario=dependency('scenario_adapter')
        self.bridge=bridge.SelectedActionHistory(ledger=fills.ObservedFillLedger(),
            history=flow.FlowHistory(period=period), interval_type=flow.FlowInterval,
            infer=scenario.infer_rival_flow, mechanics=self.m)
        self.hypotheses=deepcopy(hypotheses)
        self.terminal_enabled=terminal_enabled
        self.tie_break=tie_break
        self.selector=None
        self.pending=None
        self.fill_result=None
        self.diagnostics={}
        self.deferred_observation=None
        self._observation_commit=None
        if terminal_enabled:self._initialize_terminal()

    def _initialize_terminal(self):
        # Receipt collection is useful in season. It does not authorize or load
        # the optional final-action optimizer and its solver dependencies.
        dependency=self.dependency
        self.joint=dependency('joint_terminal_history')
        self.inputs=dependency('terminal_inputs')
        score=dependency('score_endgame');utility=dependency('terminal_utility')
        full=dependency('full_support');weighted=dependency('weighted_selector')
        # The shipped selector has one absolute sibling import. Restore any
        # caller binding after loading; its function reference remains local.
        previous=sys.modules.get('solver')
        sys.modules['solver']=dependency('solver')
        try:
            selector=dependency('selector')
        finally:
            if previous is None:sys.modules.pop('solver',None)
            else:sys.modules['solver']=previous
        self.selector=score.make_score_selector(selector.WholePlanSelector,
            weighted.make_selector,utility.build_table,full.solve_full_table,
            full.verify_certificate,rng=random.Random(0),tie_break=self.tie_break)

    def defer_observation(self, obs):
        """Journal an interrupted public observation before making a stable copy."""
        # The first pointer store is intentionally tiny: if an outer signal lands
        # during deepcopy, the exact observation object is still retained for the
        # next guarded call rather than silently losing the adjacency witness.
        self.deferred_observation=obs
        self.deferred_observation=deepcopy(obs)

    def _observation_step(self, obs):
        if obs.get('step') is not None:return int(obs['step'])
        period=24
        if self.pending is not None:
            period=max(1,int((self.pending[1] or {}).get('turnsPerDay',24)))
        return int(obs['day'])*period+int(obs['hour'])

    def _observation_working_bridge(self):
        """Fork mutable bridge state while sharing injected code dependencies."""
        working=copy(self.bridge)
        for name,value in vars(self.bridge).items():
            if name in ('interval_type','infer','mechanics'):
                continue
            setattr(working,name,deepcopy(value))
        return working

    def _publish_observation_commit(self):
        """Finish an already-computed transition idempotently after cancellation."""
        commit=getattr(self,'_observation_commit',None)
        if commit is None:return None
        # Clearing the journal is deliberately last. A signal between any two
        # assignments leaves the same complete commit available to finish again.
        self.bridge=commit['bridge']
        self.pending=None
        self.diagnostics={'observed_fills':commit['observed_fills']}
        self.fill_result=commit['fill_result']
        self.deferred_observation=None
        observed_step=commit['observed_step']
        self._observation_commit=None
        return observed_step

    def _reconcile_observation(self, obs):
        before,cfg,final,post=self.pending
        working=self._observation_working_bridge()
        working.record(before,cfg,final,post_unit_shed=post['private']['shed'],
                       post_unit_inventories=post['private']['inventories'])
        observed=working.observe(obs)
        # Publish one complete journal pointer only after every expensive or
        # mutation-capable operation has succeeded on private state.
        self._observation_commit={
            'bridge':working,
            'observed_fills':observed,
            'fill_result':deepcopy(working.ledger.last_result),
            'observed_step':self._observation_step(obs),
        }
        return self._publish_observation_commit()

    def _drop_forward_gap(self, prior, observed):
        """Fail closed when no adjacent public observation can receipt pending."""
        self.pending=None
        self.deferred_observation=None
        self.diagnostics={'observed_fills':{
            'status':'skipped','reason':'forward_gap',
            'prior_step':prior,'observed_step':observed}}
        self.fill_result=None

    def observe(self, obs):
        """Bind the ACTUALLY returned prior action, then reconcile atomically."""
        now=self._observation_step(obs)

        # A deadline can land while a completed private transition is being
        # published. Finish that journal first; repeated publication is safe.
        published=self._publish_observation_commit()
        if published is not None:
            if now==published:return
            if now>published:
                # The fill belongs to the deferred observation, not today's
                # spatial receipt consumers. The FlowHistory update is retained.
                observed=self.diagnostics.get('observed_fills')
                self.diagnostics={'deferred_observation_replayed':published,
                                  'observed_fills':observed}
                self.fill_result=None
                return

        deferred=getattr(self,'deferred_observation',None)
        if deferred is not None:
            deferred_step=self._observation_step(deferred)
            if now<deferred_step:
                # New/reordered stream: let the normal strict-backstep contract
                # below discard the old pending receipt as well.
                self.deferred_observation=None
            elif self.pending is None:
                self.deferred_observation=None
                self.diagnostics={};self.fill_result=None
                return
            else:
                prior=int(self.pending[0]['step'])
                if deferred_step!=prior+1:
                    # A stored pointer is useful only when it is the exact
                    # adjacency witness. Never promote an arbitrary old gap into
                    # a replay merely because it survived a cancelled callback.
                    self._drop_forward_gap(prior,deferred_step)
                    return
                self._reconcile_observation(deferred)
                if now>deferred_step:
                    observed=self.diagnostics.get('observed_fills')
                    self.diagnostics={'deferred_observation_replayed':deferred_step,
                                      'observed_fills':observed}
                    self.fill_result=None
                return

        if self.pending is None:
            self.diagnostics={};self.fill_result=None
            return
        before,cfg,final,post=self.pending
        prior=int(before['step'])
        if now<prior:
            # A strict backstep is a new episode/reset boundary. Never carry a
            # pending action across it; a later step could otherwise cross-link
            # the prior episode into the new history. Exact retries stay pending.
            self.pending=None
            self.deferred_observation=None
            self.diagnostics={};self.fill_result=None
            return
        if now==prior:
            self.diagnostics={};self.fill_result=None
            return
        if now!=prior+1:
            # Only the immediately following public decision can receipt the
            # returned action. Missing turns make fill/flow attribution unknown.
            self._drop_forward_gap(prior,now)
            return

        # Journal the exact adjacency witness before any mutable history work.
        # Reconciliation itself then happens wholly on private bridge state.
        self.defer_observation(obs)
        self._reconcile_observation(self.deferred_observation)

    def remember(self, obs, cfg, final, post):
        # A canceled unit stage has no final snapshot. Do not record a requested
        # quantity as a fill or synthesize a second projection for it.
        self.pending=None if post is None else deepcopy((obs,cfg,final,post))

    def transform(self, obs, cfg, selected, post, *, deadline):
        if not self.terminal_enabled:return selected
        if int(obs['step'])!=int(cfg.get('episodeSteps',720))-2:return selected
        if self.selector is None:self._initialize_terminal()
        family=self.joint.build_joint_terminal_scenarios(self.bridge.history,self.m.PRODUCTS,
            int(obs['step']),capacity=int(cfg.get('shedCapacity',100)),
            max_orders=int(cfg.get('maxMarketOrdersPerTurn',10)),**self.hypotheses)
        self.diagnostics['family']=family
        if not family['ready'] or post is None:return selected
        packet=self.inputs.build_terminal_inputs(self.m,obs,cfg,selected,
            post_unit_observation=post,scenarios=family['scenarios'],deadline=deadline)
        self.diagnostics['terminal_inputs']=packet
        if not packet['complete']:return selected
        receipts=packet['document']['receipts']
        baseline={r['scenario']:r for r in receipts if r['plan']=='baseline'}
        def feasible(action):
            # Native receipts already execute every full queue against shared
            # precommit quotes. Seed/hire acquisitions must match the baseline
            # in EVERY included scenario. Other economic fills lack a receipt
            # witness here, so changed mixed queues retain their selected action.
            if action==selected:return True
            market=selected.get('market',[])
            if not isinstance(market,list):return False
            if any(isinstance(o,list) and o and
                   o[0] in ('BUY_PRODUCT','BUY_ANIMAL','BUY_LAND')
                   for o in market):return False
            identity=next((p['id'] for p in packet['plans'] if p['action']==action),None)
            rows=[r for r in receipts if r['plan']==identity]
            return bool(rows) and all(r['done'] and all(r[k]==baseline[r['scenario']][k]
                for k in ('own_seeds_after','own_hands_after')) for r in rows)
        output=self.selector.transform_terminal(obs,cfg,selected,
            document=packet['document'],feasible=feasible)
        self.diagnostics['selection']=deepcopy(self.selector.last_objective)
        self.diagnostics['changed']=output!=selected
        return output
