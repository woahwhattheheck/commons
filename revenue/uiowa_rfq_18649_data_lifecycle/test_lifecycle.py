"""Retained behavior and malformed-input tests; all records are fictional."""
import copy
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from . import lifecycle as m
except ImportError:
    import lifecycle as m

HERE = Path(__file__).resolve().parent


def packet():
    return json.loads((HERE / 'template.json').read_text())


def event(ident='ev1', stage='classification', outcome='SUPPORTED', basis='OBSERVED', at='2026-09-10T10:00:00Z', subject='copy-001'):
    return dict(id=ident, item_id=subject, stage=stage, basis=basis, outcome=outcome,
                at=at, reference='fictional-record:'+ident, recorded_by='Fictional steward', statement='Synthetic metadata only')


def check(report, stage, ident='copy-001'):
    row = next(row for row in report['items'] if row['item']['id'] == ident)
    return next(c for c in row['applicable_checks'] if c['stage'] == stage)


class Semantics(unittest.TestCase):
    def test_example(self):
        p = m.loads((HERE / 'example.json').read_text())
        r = m.assess(p)
        self.assertEqual(r['summary']['items'], 4)
        self.assertEqual(r['summary']['evidence_records'], 15)
        states = {x['item']['id']: x['state'] for x in r['items']}
        self.assertEqual(states['ess-source'], 'SUPPLIED_RECORDS_SUPPORT_DISPOSAL')
        self.assertEqual(states['iam-diagnostic'], 'DISPOSAL_REPORTED_UNVERIFIED')
        self.assertEqual(check(r, 'minimization', 'ris-export')['status'], 'CONTRADICTORY')
        self.assertTrue(any(f['code'] == 'SOURCE_DISPOSAL_DOES_NOT_COVER_COPY' for f in r['findings']))
        self.assertTrue(m.verify_report(p, r))

    def test_missing_records_are_unknown(self):
        r = m.assess(packet())
        self.assertEqual(r['summary']['check_counts']['UNKNOWN'], 3)
        self.assertEqual(r['summary']['check_counts']['OBSERVED_GAP'], 0)
        self.assertEqual(r['items'][0]['state'], 'ACTIVE_OR_UNKNOWN')
        self.assertIn('OWNER_NOT_RECORDED', [f['code'] for f in r['findings']])

    def test_policy_is_not_practice(self):
        p = packet(); p['evidence'] = [event(basis='DOCUMENTED')]
        self.assertEqual(check(m.assess(p), 'classification')['status'], 'DOCUMENTED_ONLY')

    def test_observation_and_documentation_kept_separate(self):
        p = packet(); p['evidence'] = [event('doc',basis='DOCUMENTED',at='2026-09-18T10:00:00Z'), event('obs',outcome='GAP')]
        c = check(m.assess(p), 'classification')
        self.assertEqual(c['status'], 'OBSERVED_GAP')
        self.assertEqual(c['documented_outcome'], 'SUPPORTED')
        self.assertEqual(c['evidence_ids'], ['doc','obs'])

    def test_latest_unknown_does_not_reuse_old_success(self):
        p = packet(); p['evidence'] = [event('old'),event('new',outcome='UNKNOWN',at='2026-09-18T00:00:00Z')]
        self.assertEqual(check(m.assess(p),'classification')['status'], 'UNKNOWN')

    def test_same_instant_conflict_and_later_resolution(self):
        p = packet(); p['evidence'] = [event('a'),event('b',outcome='GAP')]
        self.assertEqual(check(m.assess(p),'classification')['status'], 'CONTRADICTORY')
        p['evidence'].append(event('c',at='2026-09-18T00:00:00Z'))
        c=check(m.assess(p),'classification')
        self.assertEqual(c['status'],'OBSERVED_SUPPORTED')
        self.assertEqual(c['latest_observed_ids'],['c'])
        self.assertEqual(c['evidence_ids'],['a','b','c'])

    def test_same_outcomes_at_same_instant_not_conflict(self):
        p=packet();p['evidence']=[event('a'),event('b')]
        self.assertEqual(check(m.assess(p),'classification')['status'],'OBSERVED_SUPPORTED')

    def test_input_order_independent_and_no_mutation(self):
        p=m.loads((HERE/'example.json').read_text()); original=copy.deepcopy(p)
        r=m.assess(p)
        self.assertEqual(p,original)
        p['items'].reverse();p['evidence'].reverse()
        for item in p['items']:item['retained_categories'].reverse()
        self.assertEqual(m.assess(p),r)

    def test_disposal_needs_subject_bound_verification(self):
        p=packet();p['evidence']=[event(stage='disposal')]
        self.assertEqual(m.assess(p)['items'][0]['state'],'DISPOSAL_REPORTED_UNVERIFIED')
        p['evidence'].append(event('verify',stage='disposal_verification',at='2026-09-11T00:00:00Z'))
        self.assertEqual(m.assess(p)['items'][0]['state'],'SUPPLIED_RECORDS_SUPPORT_DISPOSAL')

    def test_verification_alone_and_before_disposal_not_complete(self):
        p=packet();p['evidence']=[event('verify',stage='disposal_verification')]
        self.assertEqual(m.assess(p)['items'][0]['state'],'ACTIVE_OR_UNKNOWN')
        p['evidence'].append(event('dispose',stage='disposal',at='2026-09-12T00:00:00Z'))
        r=m.assess(p)
        self.assertEqual(r['items'][0]['state'],'DISPOSAL_REPORTED_UNVERIFIED')
        self.assertIn('DISPOSAL_VERIFICATION_UNCORROBORATED',[f['code'] for f in r['findings']])

    def test_copy_does_not_inherit_source_observations(self):
        p=packet();child=copy.deepcopy(p['items'][0]);child.update(id='child',parent_id='copy-001')
        p['items'].append(child);p['evidence']=[event(stage='disposal'),event('verify',stage='disposal_verification')]
        r=m.assess(p)
        self.assertEqual(next(x for x in r['items'] if x['item']['id']=='child')['state'],'ACTIVE_OR_UNKNOWN')
        self.assertEqual(check(r,'transfer','child')['status'],'UNKNOWN')

    def test_expiry_boundary_and_future_date(self):
        p=packet();p['items'][0]['retention_due_at']=p['as_of']
        self.assertTrue(m.assess(p)['items'][0]['expiry_reached'])
        p['items'][0]['retention_due_at']='2026-09-20T00:00:00Z'
        self.assertFalse(m.assess(p)['items'][0]['expiry_reached'])

    def test_documented_disposal_never_closes_copy(self):
        p=packet();p['evidence']=[event('d','disposal',basis='DOCUMENTED'),event('v','disposal_verification',basis='DOCUMENTED')]
        self.assertEqual(m.assess(p)['items'][0]['state'],'ACTIVE_OR_UNKNOWN')

    def test_semantic_tamper_not_rescued_by_hash(self):
        p=packet();r=m.assess(p);r['items'][0]['state']='SUPPLIED_RECORDS_SUPPORT_DISPOSAL'
        r.pop('report_sha256');r['report_sha256']=m.digest(r)
        self.assertFalse(m.verify_report(p,r))

    def test_csv_and_markdown_passive_rendering(self):
        r=m.assess(packet());r['findings'][0]['detail']='  =HYPERLINK("example","x")'
        rows=list(csv.DictReader(io.StringIO(m.findings_csv(r))))
        self.assertTrue(rows[0]['detail'].startswith("'"))
        r['items'][0]['item']['purpose']='<script>x</script>|[link](example)'
        text=m.markdown(r)
        self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text)
        self.assertIn('\\|',text);self.assertIn('\\[link\\]',text)


class InputValidation(unittest.TestCase):
    def reject(self,p):
        with self.assertRaises(m.InputError):m.assess(p)

    def test_duplicate_keys_numbers_nonfinite_and_invalid_unicode(self):
        for raw in ['{"schema":1,"schema":2}', '{"x":1}', '{"x":1.2}', '{"x":NaN}', '"\ud800"']:
            with self.subTest(raw=repr(raw)), self.assertRaises(m.InputError):m.loads(raw)

    def test_closed_shape_and_exact_types(self):
        for mutate in [lambda p:p.update(extra='x'),lambda p:p['items'][0].update(actual_data='not permitted'),lambda p:p.update(items=True),lambda p:p['items'][0].update(owner=False),lambda p:p.update(as_of=1)]:
            p=packet();mutate(p);self.reject(p)

    def test_duplicate_item_evidence_and_categories(self):
        p=packet();p['items'].append(copy.deepcopy(p['items'][0]));self.reject(p)
        p=packet();p['evidence']=[event(),event()];self.reject(p)
        p=packet();p['items'][0]['retained_categories']=['a','a'];self.reject(p)

    def test_unknown_subject_parent_and_cycles(self):
        p=packet();p['evidence']=[event(subject='missing')];self.reject(p)
        p=packet();p['items'][0]['parent_id']='missing';self.reject(p)
        p=packet();p['items'][0]['parent_id']='copy-001';self.reject(p)

    def test_chronology_and_calendar(self):
        for at in ['2026-08-31T00:00:00Z','2026-09-20T00:00:00Z','2026-02-30T00:00:00Z','2026-09-10T10:00:00+00:00']:
            p=packet();p['evidence']=[event(at=at)];self.reject(p)
        p=packet();p['items'][0]['retention_due_at']='2026-08-31T00:00:00Z';self.reject(p)

    def test_child_cannot_predate_parent(self):
        p=packet();child=copy.deepcopy(p['items'][0]);child.update(id='child',parent_id='copy-001',created_at='2026-08-31T00:00:00Z')
        p['items'].append(child);self.reject(p)

    def test_transfer_record_names_child(self):
        p=packet();p['evidence']=[event(stage='transfer')];self.reject(p)

    def test_controls_bounds_and_no_disguised_container(self):
        p=packet();p['items'][0]['location']='hello\nworld';self.reject(p)
        p=packet();p['items'][0]['location']='x'*1001;self.reject(p)
        p=packet();p['items']=p['items']*201;self.reject(p)
        class Mapping(dict):pass
        self.reject(Mapping(packet()))
        with self.assertRaises(m.InputError):m.loads(' '* (m.MAX_BYTES+1))


class CommandLine(unittest.TestCase):
    def run_cli(self,source,output):
        return subprocess.run([sys.executable,str(HERE/'cli.py'),str(source),str(output)],capture_output=True,text=True,timeout=15)

    def test_cli_outputs_and_preserves_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report';source=HERE/'example.json'
            r=self.run_cli(source,out);self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(set(x.name for x in out.iterdir()),{'report.json','assessment.md','follow-ups.csv'})
            original=(out/'report.json').read_bytes()
            self.assertTrue(m.verify_report(m.loads(source.read_text()),json.loads(original)))
            r=self.run_cli(source,out);self.assertEqual(r.returncode,2)
            self.assertEqual((out/'report.json').read_bytes(),original)

    def test_bad_input_creates_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'bad.json';source.write_text('{"invalid":true}');out=Path(tmp)/'out'
            r=self.run_cli(source,out);self.assertEqual(r.returncode,2);self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
