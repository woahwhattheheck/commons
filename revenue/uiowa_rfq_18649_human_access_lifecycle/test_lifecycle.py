"""Retained behavioral, interchange and actual CLI tests for UIOWA-053."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

# Exact local file, without mutating sys.path or generic sys.modules aliases.
ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('uiowa053_lifecycle_under_test', ROOT / 'lifecycle.py')
life = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(life)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.packet = life.loads((ROOT / 'example.json').read_text(encoding='utf-8'))

    def row(self, target='SYN-J1'):
        return next(r for r in life.assess(self.packet)['rows'] if r['target_id'] == target)

    def event(self, kind, target='SYN-J1'):
        return next(e for e in self.packet['evidence'] if e['target_id'] == target and e['kind'] == kind)

    def without(self, *kinds, target='SYN-J1'):
        self.packet['evidence'] = [e for e in self.packet['evidence'] if e['target_id'] != target or e['kind'] not in kinds]

    def test_example_has_four_scenarios_and_nine_targets(self):
        result = life.assess(self.packet)
        self.assertEqual(len(result['rows']), 9)
        self.assertEqual({r['scenario'] for r in result['rows']}, set(life.SCENARIOS))
        self.assertEqual(sum(r['chain_complete'] for r in result['rows']), 5)

    def test_policy_only_is_unknown(self):
        row = self.row('SYN-L3')
        self.assertEqual(row['status'], 'UNKNOWN')
        self.assertFalse(row['chain_complete'])
        self.assertEqual(len(row['policy_ids']), 1)

    def test_contractor_departure_requires_every_declared_system(self):
        case = next(c for c in life.assess(self.packet)['cases'] if c['case_id'] == 'SYN-CONTRACTOR')
        self.assertEqual(case['complete_targets'], 1)
        self.assertEqual(case['unresolved_target_ids'], ['SYN-L2', 'SYN-L3'])

    def test_changed_responsibilities_retain_unremoved_old_role(self):
        row = self.row('SYN-M2')
        self.assertEqual(row['status'], 'CONTRADICTED')
        self.assertEqual(row['observed_state'], 'PRESENT')
        self.assertEqual(row['desired_state'], 'ABSENT')

    def test_emergency_verification_is_not_retrospective_review(self):
        row = self.row('SYN-E1')
        self.assertEqual(row['status'], 'VERIFIED')
        self.assertFalse(row['chain_complete'])
        self.assertIn('MISSING_EMERGENCY_REVIEWED', row['findings'])

    def test_joiner_has_complete_chain(self):
        self.assertEqual(self.row()['status'], 'VERIFIED')
        self.assertTrue(self.row()['chain_complete'])

    def test_observation_without_change_or_approval_is_not_complete(self):
        self.without('APPLIED', 'APPROVED')
        self.assertEqual(self.row()['status'], 'VERIFIED')
        self.assertFalse(self.row()['chain_complete'])

    def test_request_and_approval_do_not_imply_application(self):
        self.without('APPLIED', 'VERIFIED')
        self.assertEqual(self.row()['status'], 'APPROVED_ONLY')
        self.without('APPROVED')
        self.assertEqual(self.row()['status'], 'REQUESTED_ONLY')

    def test_old_verification_cannot_cover_later_change(self):
        self.event('APPLIED')['observed_at'] = '2026-09-18T14:00:00Z'
        self.assertEqual(self.row()['status'], 'APPLIED_UNVERIFIED')
        self.assertIn('VERIFICATION_PREDATES_CHANGE_OR_CHECKPOINT', self.row()['findings'])

    def test_pre_checkpoint_verification_does_not_close_chain(self):
        self.event('APPLIED')['observed_at'] = '2026-09-18T11:00:00Z'
        self.event('VERIFIED')['observed_at'] = '2026-09-18T11:01:00Z'
        self.assertEqual(self.row()['status'], 'APPLIED_UNVERIFIED')

    def test_future_evidence_is_excluded_and_retained(self):
        e = self.event('VERIFIED'); e['observed_at'] = '2026-09-19T12:10:00Z'
        row = self.row()
        self.assertEqual(row['status'], 'APPLIED_UNVERIFIED')
        self.assertEqual(row['future_evidence_ids'], [e['evidence_id']])
        self.assertNotIn(e['evidence_id'], row['evidence_ids'])

    def test_excluded_future_record_does_not_erase_current_evidence(self):
        event = copy.deepcopy(self.event('VERIFIED'))
        event.update(evidence_id='SYN-FUTURE', observed_at='2026-09-19T12:00:00Z',state='ABSENT')
        self.packet['evidence'].append(event)
        row = self.row()
        self.assertTrue(row['chain_complete'])
        self.assertEqual(row['observed_state'],'PRESENT')
        self.assertEqual(row['future_evidence_ids'],['SYN-FUTURE'])

    def test_future_target_is_not_due_not_a_completed_change(self):
        self.packet['targets'][0]['effective_at'] = '2026-09-20T00:00:00Z'
        self.assertEqual(self.row()['status'], 'NOT_DUE')
        self.assertFalse(self.row()['chain_complete'])

    def test_equal_instant_conflict_does_not_depend_on_id_order(self):
        e = copy.deepcopy(self.event('VERIFIED')); e.update(evidence_id='ZZ-CONFLICT',state='ABSENT',observed_at='2026-09-18T08:10:00-04:00')
        self.packet['evidence'].append(e)
        self.assertEqual(self.row()['status'], 'CONFLICTING')
        e['evidence_id']='AA-CONFLICT'
        self.assertEqual(self.row()['status'], 'CONFLICTING')

    def test_same_instant_apply_verify_conflict_is_preserved(self):
        self.event('VERIFIED').update(observed_at='2026-09-18T12:00:00Z',state='ABSENT')
        self.assertEqual(self.row()['status'], 'CONFLICTING')

    def test_approval_after_change_is_not_a_complete_chain(self):
        self.event('APPROVED')['observed_at'] = '2026-09-18T15:00:00Z'
        self.assertEqual(self.row()['status'], 'VERIFIED')
        self.assertIn('CHRONOLOGY_GAP',self.row()['findings'])
        self.assertFalse(self.row()['chain_complete'])

    def test_old_entitlement_review_cannot_cover_new_role_change(self):
        self.event('REVIEWED','SYN-M1')['observed_at'] = '2026-09-17T13:00:00Z'
        self.assertIn('REVIEWED_PREDATES_CHECKPOINT', self.row('SYN-M1')['findings'])
        self.assertFalse(self.row('SYN-M1')['chain_complete'])

    def test_evidence_change_affects_only_intended_target(self):
        before=life.assess(self.packet)
        e=copy.deepcopy(self.event('APPLIED','SYN-L2'))
        e.update(evidence_id='SYN-FOLLOWUP',kind='VERIFIED',observed_at='2026-09-18T14:00:00Z',source_ref='synthetic-follow-up:001')
        self.packet['evidence'].append(e)
        after=life.assess(self.packet)
        changes=[a['target_id'] for a,b in zip(after['rows'],before['rows']) if a!=b]
        self.assertEqual(changes,['SYN-L2'])
        self.assertTrue(self.row('SYN-L2')['chain_complete'])
        self.assertEqual(self.row('SYN-L3')['status'],'UNKNOWN')

    def test_no_input_mutation_and_order_independent_output(self):
        before=copy.deepcopy(self.packet); expected=life.assess(self.packet)
        self.assertEqual(self.packet,before)
        self.packet['targets'].reverse();self.packet['evidence'].reverse()
        self.assertEqual(life.assess(self.packet),expected)

    def test_json_and_csv_round_trip_exact_fields(self):
        texts=life.export_csv(self.packet)
        self.assertEqual(life.import_csv(*texts),self.packet)
        self.assertEqual(life.loads(life.canonical(self.packet)),self.packet)

    def test_empty_evidence_stays_unknown_after_csv_round_trip(self):
        self.packet['evidence']=[]
        restored=life.import_csv(*life.export_csv(self.packet))
        self.assertEqual(restored,self.packet)
        self.assertTrue(all(r['status']=='UNKNOWN' for r in life.assess(restored)['rows']))

    def test_formula_like_and_apostrophe_text_round_trip_as_literals(self):
        for value in ('=1+1','+cmd','-literal','@lookup',' =1+1','\u00a0=literal',"'literal","''text",'\tformula','\rline','\nline','plain, "quoted" | snow 雪'):
            with self.subTest(value=value):
                self.packet['evidence'][0]['note']=value
                exported=life.export_csv(self.packet)
                rows=list(csv.reader(io.StringIO(exported[1],newline='')))
                if value[0] in life.ESCAPE or value[0].isspace():self.assertTrue(rows[1][-1].startswith("'"))
                self.assertEqual(life.import_csv(*exported),self.packet)

    def test_unknown_field_duplicate_id_and_foreign_target_rejected(self):
        mutations=[lambda p:p.update(extra=True),lambda p:p['targets'].append(copy.deepcopy(p['targets'][0])),lambda p:p['evidence'].append(copy.deepcopy(p['evidence'][0])),lambda p:p['evidence'][0].update(target_id='OTHER')]
        for change in mutations:
            with self.subTest(change=change):
                p=copy.deepcopy(self.packet);change(p)
                with self.assertRaises(life.InputError):life.validate(p)

    def test_duplicate_logical_target_cannot_inflate_completion(self):
        extra = copy.deepcopy(self.packet['targets'][0])
        extra.update(target_id='DUPLICATE', effective_at='2026-09-18T08:00:00-04:00')
        self.packet['targets'].append(extra)
        with self.assertRaises(life.InputError):life.validate(self.packet)

    def test_plain_package_import_and_cli_module_entry(self):
        repo = ROOT.parents[1]
        with tempfile.TemporaryDirectory() as temp:
            command=[sys.executable,*(['-O'] if sys.flags.optimize else []),'-m','revenue.uiowa_rfq_18649_human_access_lifecycle.lifecycle','inspect',str(ROOT/'example.json'),'--out',str(Path(temp)/'out')]
            run=subprocess.run(command,cwd=repo,capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('declared_targets=9 complete_chains=5',run.stdout)

    def test_case_identity_cannot_change_across_systems(self):
        self.packet['targets'][1]['role']='Different role'
        with self.assertRaises(life.InputError):life.validate(self.packet)

    def test_bad_datetime_values_are_named_input_errors(self):
        for value in ('2026-09-18T12:00:00','2026-02-30T00:00:00Z','bad','9999-12-31T23:59:59-12:00'):
            with self.subTest(value=value):
                self.packet['as_of']=value
                with self.assertRaises(life.InputError):life.assess(self.packet)

    def test_strict_types_and_kind_state_rules(self):
        mutations=[lambda p:p.update(schema_version=True),lambda p:p['targets'][0].update(review_required='false'),lambda p:p['evidence'][0].update(state='ABSENT'),lambda p:p['targets'][0].update(desired_state='UNKNOWN'),lambda p:p['evidence'][0].update(kind='UNRECOGNIZED'),lambda p:p.update(provenance='\ud800')]
        for change in mutations:
            with self.subTest(change=change):
                p=copy.deepcopy(self.packet);change(p)
                with self.assertRaises(life.InputError):life.validate(p)

    def test_duplicate_json_keys_and_nonfinite_are_rejected(self):
        for raw in ('{"schema_version":1,"schema_version":1}','{"as_of":NaN}','{"a":Infinity}'):
            with self.subTest(raw=raw):
                with self.assertRaises(life.InputError):life.loads(raw)

    def test_bad_csv_headers_width_and_mixed_snapshots_rejected(self):
        targets,evidence=life.export_csv(self.packet)
        variants=[(targets.replace('target_id','other_id',1),evidence),(targets.replace('schema_version,','schema_version,schema_version,',1),evidence),(targets+'unexpected\n',evidence),(targets,evidence.replace('2026-09-18T18:00:00Z','2026-09-19T18:00:00Z',1))]
        for pair in variants:
            with self.subTest(pair=pair[0][:30]):
                with self.assertRaises(life.InputError):life.import_csv(*pair)

    def test_render_keeps_scope_and_missing_evidence_explicit(self):
        rendered=life.render(life.assess(self.packet))
        self.assertIn('SYNTHETIC / FICTIONAL',rendered)
        self.assertIn('CONTRADICTED',rendered)
        self.assertIn('MISSING_EMERGENCY_REVIEWED',rendered)
        self.assertIn('no live account checks',rendered)

    def test_real_cli_round_trip_and_source_unchanged(self):
        source=(ROOT/'example.json').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'review';restored=Path(temp)/'restored.json'
            command=[sys.executable,*(['-O'] if sys.flags.optimize else []),str(ROOT/'lifecycle.py')]
            run=subprocess.run(command+['inspect',str(ROOT/'example.json'),'--out',str(out)],capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('declared_targets=9 complete_chains=5',run.stdout)
            run=subprocess.run(command+['import',str(out/'targets.csv'),str(out/'evidence.csv'),'--out',str(restored)],capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(life.loads(restored.read_text(encoding='utf-8')),self.packet)
        self.assertEqual((ROOT/'example.json').read_bytes(),source)

    def test_real_cli_refuses_existing_output_without_deletion(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'review';out.mkdir();victim=out/'keep.txt';victim.write_bytes(b'unchanged')
            run=subprocess.run([sys.executable,str(ROOT/'lifecycle.py'),'inspect',str(ROOT/'example.json'),'--out',str(out)],capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,2)
            self.assertEqual(victim.read_bytes(),b'unchanged')
            self.assertEqual(list(out.iterdir()),[victim])
            self.assertNotIn('Traceback',run.stderr)


if __name__=='__main__':
    unittest.main()
