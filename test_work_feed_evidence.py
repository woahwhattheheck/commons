"""Focused contract tests; no live Slack/GitHub calls or claim mutations."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from integrations.command_center import work_feed_evidence as wf

AT = '2026-09-19T15:45:00Z'
OBS = '2026-09-19T15:44:59Z'
START = '2026-09-19T14:00:00Z'


def event(eid, kind='DEMAND', op='OP-A', source=None, channel='CDEMO', at='2026-09-19T15:40:00Z', holder='', claim='', lease=None):
    source = source or ('ledger' if kind in {'CLAIM','RENEW','RELEASE'} else 'github' if kind in {'OPEN','CLOSED'} else 'slack')
    return dict(source_id=source, event_id=eid, at=at, channel_id=channel,
        operation_id=op, kind=kind, tags=[] if source == 'ledger' or kind == 'MESSAGE' else ['python'],
        priority=50 if kind != 'MESSAGE' else 0, holder=holder, claim_id=claim,
        lease_until=lease, ref='https://example.invalid/evidence/'+eid)


def packet():
    channels = [dict(channel_id=cid, name=name, specialty_tags=['python'], capacity=3,
        paused=False, required_sources=dict(slack='slack', github='github', claims='ledger'))
        for cid,name in [('CDEMO','demo'),('CTECH','technical')]]
    sources = [dict(source_id=sid, provider=provider, scope=['CDEMO','CTECH'],
        observed_at=OBS, window_start=START, complete=True)
        for sid,provider in [('slack','slack'),('github','github'),('ledger','claims')]]
    return dict(schema=wf.SCHEMA, snapshot_id='synthetic-ad7b', max_source_age_seconds=300,
        channels=channels, sources=sources,
        events=[event('s1'), event('g1','OPEN','GH-12')],
        aliases=[dict(alias='GH-12',operation_id='OP-A',ref='https://example.invalid/alias/12')])


def report(p=None, at=AT):
    return wf.compile_historical(p or packet(), at)


class EvidenceCompositionTests(unittest.TestCase):
    def test_dedup_operations_across_slack_and_github(self):
        r=report(); self.assertEqual(len(r['operations']),1)
        self.assertEqual(r['operations'][0]['observed_ids'],['GH-12','OP-A'])
        self.assertEqual(len(r['dispatch']['assignments']),1)
        self.assertTrue(all(c['verified_targets']==1 for c in r['dispatch_snapshot']['channels']))
    def test_original_router_receipt_matches(self):
        from host.swarm_channel_dispatch import compile_dispatch
        r=report(); self.assertEqual(r['dispatch'],compile_dispatch(r['dispatch_snapshot']))
    def test_source_refs_survive(self):
        self.assertEqual(len(report()['operations'][0]['source_refs']),2)
    def test_permutation_invariance(self):
        p=packet(); r=report(p)
        for key in ('channels','sources','events','aliases'): p[key].reverse()
        for s in p['sources']: s['scope'].reverse()
        self.assertEqual(r,report(p))
    def test_exact_event_duplicates_collapse(self):
        p=packet(); p['events'].append(copy.deepcopy(p['events'][0])); r=report(p)
        self.assertEqual(r['duplicate_events_collapsed'],1)
        self.assertEqual(r['channel_diagnostics'][0]['messages_observed_15m'],1)
    def test_overlapping_slack_exports_do_not_double_traffic(self):
        p=packet(); s=copy.deepcopy(p['sources'][0]); s['source_id']='slack2'; p['sources'].append(s)
        e=copy.deepcopy(p['events'][0]); e['source_id']='slack2'; p['events'].append(e)
        self.assertEqual(report(p)['channel_diagnostics'][0]['messages_observed_15m'],1)
    def test_event_identity_remint_rejected(self):
        p=packet(); e=copy.deepcopy(p['events'][0]); e['priority']=51; p['events'].append(e)
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_provider_identity_conflict_across_exports(self):
        p=packet(); s=copy.deepcopy(p['sources'][0]); s['source_id']='slack2'; p['sources'].append(s)
        e=copy.deepcopy(p['events'][0]); e.update(source_id='slack2',kind='SHIP'); p['events'].append(e)
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_alias_chain(self):
        p=packet(); p['aliases'].append(dict(alias='ALIAS-2',operation_id='GH-12',ref='x'))
        p['events'].append(event('s2',op='ALIAS-2'))
        self.assertEqual(len(report(p)['operations']),1)
    def test_alias_cycle_rejected(self):
        p=packet(); p['aliases'].append(dict(alias='OP-A',operation_id='GH-12',ref='x'))
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_tag_conflict_holds(self):
        p=packet(); p['events'][1]['tags']=['javascript']; r=report(p)
        self.assertIn('TAG_CONFLICT',r['operations'][0]['reasons']); self.assertFalse(r['dispatch']['assignments'])
    def test_priority_conflict_holds(self):
        p=packet(); p['events'][1]['priority']=99
        self.assertIn('PRIORITY_CONFLICT',report(p)['operations'][0]['reasons'])
    def test_ship_versus_open_holds(self):
        p=packet(); p['events'][0]['kind']='SHIP'
        self.assertIn('WORK_STATE_CONFLICT',report(p)['operations'][0]['reasons'])
    def test_terminal_agreement(self):
        p=packet(); p['events'][0]['kind']='SHIP'; p['events'][1]['kind']='CLOSED'
        self.assertEqual(report(p)['operations'][0]['status'],'TERMINAL')
    def test_latest_state_per_source(self):
        p=packet(); p['events'] += [event('s2','SHIP',at='2026-09-19T15:41:00Z'), event('g2','CLOSED','GH-12',at='2026-09-19T15:41:00Z')]
        self.assertEqual(report(p)['operations'][0]['status'],'TERMINAL')
    def test_claim_and_release(self):
        p=packet(); p['events'].append(event('c1','CLAIM',holder='A',claim='lease-1',lease='2026-09-19T16:00:00Z'))
        self.assertEqual(report(p)['operations'][0]['status'],'CLAIMED')
        p['events'].append(event('c2','RELEASE',at='2026-09-19T15:41:00Z',holder='A',claim='lease-1'))
        self.assertEqual(report(p)['operations'][0]['status'],'AVAILABLE')
    def test_two_holders_release_only_matching_holder(self):
        p=packet(); p['events'] += [event('c1','CLAIM',holder='A',claim='lease-a',lease='2026-09-19T16:00:00Z'),event('c2','CLAIM',holder='B',claim='lease-b',lease='2026-09-19T16:00:00Z')]
        self.assertIn('MULTI_HOLDER',report(p)['operations'][0]['reasons'])
        p['events'].append(event('c3','RELEASE',at='2026-09-19T15:42:00Z',holder='A',claim='lease-a'))
        r=report(p); self.assertEqual(r['operations'][0]['holders'],['B']); self.assertEqual(r['operations'][0]['status'],'CLAIMED')
    def test_same_holder_two_claims_one_release_still_occupied(self):
        p=packet(); p['events'] += [event('c1','CLAIM',holder='A',claim='lease-a',lease='2026-09-19T16:00:00Z'),event('c2','CLAIM',holder='A',claim='lease-b',lease='2026-09-19T16:00:00Z'),event('c3','RELEASE',at='2026-09-19T15:42:00Z',holder='A',claim='lease-a')]
        r=report(p); self.assertEqual(r['channel_diagnostics'][0]['unreleased_claim_slots'],1); self.assertEqual(r['operations'][0]['status'],'CLAIMED')
    def test_stale_claim_is_not_available(self):
        p=packet(); p['events'].append(event('c1','CLAIM',holder='A',claim='lease-a',lease='2026-09-19T15:44:00Z'))
        r=report(p); self.assertIn('STALE_UNRELEASED_CLAIM',r['operations'][0]['reasons']); self.assertEqual(r['channel_diagnostics'][0]['unreleased_claim_slots'],1)
    def test_orphan_release_preserves_unknown_occupancy(self):
        p=packet(); p['events'].append(event('c1','RELEASE',holder='A',claim='lease-a'))
        r=report(p); self.assertIn('ORPHAN_RELEASE',r['operations'][0]['reasons']); self.assertEqual(r['channel_diagnostics'][0]['unreleased_claim_slots'],1)
    def test_two_orphan_releases_preserve_both_unknown_slots(self):
        p=packet(); p['events'] += [event('a','RELEASE',holder='A',claim='lease-a'),event('b','RELEASE',holder='B',claim='lease-b')]
        r=report(p); self.assertEqual(r['channel_diagnostics'][0]['unreleased_claim_slots'],2)
        self.assertEqual(r['operations'][0]['holders'],['A','B'])
    def test_valid_interleavings_and_prefixes(self):
        import itertools
        base=[('a','CLAIM','A','a'),('b','RELEASE','A','a'),('c','CLAIM','B','b'),('d','RELEASE','B','b')]
        cases=0
        for order in itertools.permutations(base):
            ids=[e[0] for e in order]
            if ids.index('a')>ids.index('b') or ids.index('c')>ids.index('d'): continue
            for count in range(5):
                p=packet(); live=set()
                for index,(eid,kind,holder,claim) in enumerate(order[:count]):
                    if kind=='CLAIM': live.add(holder)
                    else: live.remove(holder)
                    p['events'].append(event(eid,kind,at=f'2026-09-19T15:4{index}:00Z',holder=holder,claim=claim,lease='2026-09-19T16:00:00Z' if kind=='CLAIM' else None))
                p['events'].reverse(); r=report(p); cases+=1
                self.assertEqual(r['channel_diagnostics'][0]['unreleased_claim_slots'],len(live))
                self.assertEqual(r['operations'][0]['holders'],sorted(live))
                self.assertEqual(bool(r['dispatch']['assignments']),not live)
        self.assertEqual(cases,30)
    def test_expiry_boundary_and_renewal(self):
        p=packet(); p['events'].append(event('a','CLAIM',holder='A',claim='lease-a',lease=AT))
        self.assertIn('STALE_UNRELEASED_CLAIM',report(p)['operations'][0]['reasons'])
        p['events'].append(event('b','RENEW',at='2026-09-19T15:44:00Z',holder='A',claim='lease-a',lease='2026-09-19T16:00:00Z'))
        self.assertEqual(report(p)['operations'][0]['status'],'CLAIMED')
    def test_released_claim_renewal_is_held(self):
        p=packet(); p['events'] += [event('a','CLAIM',holder='A',claim='lease-a',lease='2026-09-19T16:00:00Z'),event('b','RELEASE',at='2026-09-19T15:41:00Z',holder='A',claim='lease-a'),event('c','RENEW',at='2026-09-19T15:42:00Z',holder='A',claim='lease-a',lease='2026-09-19T16:05:00Z')]
        self.assertIn('ORPHAN_OR_RELEASED_RENEWAL',report(p)['operations'][0]['reasons'])
    def test_normalized_configuration_is_detached(self):
        p=packet(); data,_,_=wf.normalize(p); data['channels'][0]['required_sources']['slack']='other'
        self.assertEqual(p['channels'][0]['required_sources']['slack'],'slack')
    def test_huge_integer_json_is_normalized(self):
        with self.assertRaises(wf.EvidenceError): wf.load_json('{"x":'+('9'*5000)+'}')
    def test_empty_snapshot_does_not_invent_work(self):
        p=packet(); p['events']=[]; p['aliases']=[]; r=report(p)
        self.assertEqual(r['operations'],[]); self.assertEqual(r['dispatch']['assignments'],[])
    def test_caller_aggregate_fields_are_rejected(self):
        for field in ('active_claims','messages_15m','verified_targets'):
            p=packet(); p['channels'][0][field]=0
            with self.subTest(field=field), self.assertRaises(wf.EvidenceError): report(p)
    def test_conflicting_simultaneous_release_never_frees_slot(self):
        p=packet(); p['events'] += [event('a','RELEASE',holder='A',claim='lease-a'),event('z','CLAIM',holder='A',claim='lease-a',lease='2026-09-19T16:00:00Z')]
        r=report(p); self.assertEqual(r['channel_diagnostics'][0]['unreleased_claim_slots'],1); self.assertEqual(r['operations'][0]['status'],'HOLD')
    def test_claim_id_cannot_cross_operations(self):
        p=packet(); p['events'] += [event('a','CLAIM',holder='A',claim='same',lease='2026-09-19T16:00:00Z'),event('b','CLAIM','OP-B',holder='A',claim='same',lease='2026-09-19T16:00:00Z')]
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_future_observation_rejected(self):
        p=packet(); p['sources'][0]['observed_at']='2026-09-19T15:46:00Z'
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_future_event_outside_source_rejected(self):
        p=packet(); p['events'][0]['at']='2026-09-19T15:46:00Z'
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_stale_sources_degrade_not_zero(self):
        r=report(at='2026-09-19T15:51:00Z'); self.assertFalse(r['dispatch']['assignments'])
        self.assertTrue(all(d['coverage']=='DEGRADED' for d in r['channel_diagnostics']))
    def test_missing_adapter_degrades_and_is_not_chosen(self):
        for provider in ('slack','github','claims'):
            with self.subTest(provider=provider):
                p=packet(); p['channels'][1]['required_sources'][provider]='missing'
                r=report(p); self.assertEqual(r['dispatch']['assignments'][0]['channel_id'],'CDEMO')
                self.assertEqual(r['channel_diagnostics'][1]['coverage'],'DEGRADED')
    def test_partial_source_blocks_originating_operation(self):
        p=packet(); p['sources'][0]['complete']=False; r=report(p)
        self.assertFalse(r['dispatch']['assignments']); self.assertIn('SOURCE_COVERAGE_DEGRADED',r['operations'][0]['reasons'])
    def test_source_scope_mismatch_degrades(self):
        p=packet(); p['sources'][2]['scope']=['CDEMO']; r=report(p)
        self.assertIn('SOURCE_SCOPE_MISMATCH:ledger',r['channel_diagnostics'][1]['reasons'])
    def test_traffic_window_boundary_and_current_drift(self):
        p=packet(); p['events'][0]['at']='2026-09-19T15:30:00Z'
        with patch.object(wf,'_now',return_value=AT): r=wf.compile_current(p)
        self.assertEqual(r['channel_diagnostics'][0]['messages_observed_15m'],1)
        with patch.object(wf,'_now',return_value='2026-09-19T15:45:01Z'):
            self.assertEqual(wf.verify_report(p,r,current=True)['verdict'],'TIME_SENSITIVE_STATE_CHANGED')
    def test_historical_never_current(self):
        with patch.object(wf,'_now',return_value=AT): self.assertFalse(wf.verify_report(packet(),report(),current=True)['ok'])
    def test_current_unchanged_then_expired(self):
        p=packet()
        with patch.object(wf,'_now',return_value=AT): r=wf.compile_current(p)
        with patch.object(wf,'_now',return_value='2026-09-19T15:45:01Z'): self.assertTrue(wf.verify_report(p,r,current=True)['ok'])
        with patch.object(wf,'_now',return_value='2026-09-19T15:51:01Z'): self.assertFalse(wf.verify_report(p,r,current=True)['ok'])
    def test_future_report_rejected_for_current(self):
        p=packet()
        with patch.object(wf,'_now',return_value=AT): r=wf.compile_current(p)
        with patch.object(wf,'_now',return_value='2026-09-19T15:44:59Z'): self.assertEqual(wf.verify_report(p,r,current=True)['verdict'],'NOT_CURRENT')
    def test_verifier_recompiles_even_after_resealing(self):
        p=packet(); r=report(p); r['operations'][0]['status']='TERMINAL'; r.pop('report_sha256'); r['report_sha256']=wf._digest(r)
        self.assertFalse(wf.verify_report(p,r)['ok'])
    def test_reused_snapshot_name_changed_config_invalidates_receipt(self):
        p=packet(); r=report(p); p['channels'][0]['capacity']=1
        self.assertFalse(wf.verify_report(p,r)['ok']); self.assertNotEqual(report(p)['source_sha256'],r['source_sha256'])
    def test_authority_remains_false(self):
        r=report(); self.assertFalse(any(r['authority'].values())); self.assertFalse(any(r['dispatch']['authority'].values()))
    def test_input_is_not_mutated(self):
        p=packet(); old=copy.deepcopy(p); report(p); self.assertEqual(p,old)
    def test_malformed_types_normalized(self):
        for field in ('channel_id','name','capacity','paused','required_sources'):
            with self.subTest(field=field):
                p=packet(); p['channels'][0][field]=[]
                with self.assertRaises(wf.EvidenceError): report(p)
    def test_boolean_capacity_and_priority_rejected(self):
        p=packet(); p['channels'][0]['capacity']=True
        with self.assertRaises(wf.EvidenceError): report(p)
        p=packet(); p['events'][0]['priority']=True
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_strict_json_duplicate_nonfinite_unicode_and_cycle(self):
        for value in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1.2}', '{"a":"\\ud800"}', '{"a":'+('9'*100)+'}'):
            with self.subTest(value=value), self.assertRaises(wf.EvidenceError): wf.load_json(value)
        p=packet(); p['events'].append(p)
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_nonledger_claim_rejected(self):
        p=packet(); p['events'][0]['holder']='FAKE'
        with self.assertRaises(wf.EvidenceError): report(p)
    def test_cli_round_trip_and_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'packet.json'; dst=Path(tmp)/'report.json'; src.write_text(json.dumps(packet()))
            prefix=[sys.executable]+(['-O'] if sys.flags.optimize else [])+['-m','integrations.command_center.work_feed_evidence']
            run=subprocess.run(prefix+['replay',str(src),'--at',AT],capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stderr); dst.write_text(run.stdout)
            verified=subprocess.run(prefix+['verify',str(src),str(dst)],capture_output=True,text=True,timeout=10)
            self.assertEqual(verified.returncode,0,verified.stderr)
            denied=subprocess.run(prefix+['current',str(src),'--at',AT],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(denied.returncode,0); self.assertEqual(denied.stdout,'')
    def test_markdown_discloses_limits(self):
        text=wf.render_markdown(report()); self.assertIn('HISTORICAL_REPLAY',text); self.assertIn('no source authentication',text); self.assertIn('https://example.invalid/evidence/s1',text)


if __name__=='__main__': unittest.main()
