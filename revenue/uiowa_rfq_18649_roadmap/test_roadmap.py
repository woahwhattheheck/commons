"""Executable regression and interchange checks; fixtures are entirely synthetic."""
import copy
import csv
import hashlib
import io
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import roadmap

HERE = Path(__file__).resolve().parent


def item(key='A', deps=None, days=None, phase='0-90'):
    return dict(id=key, title='Synthetic ' + key, group='ESS', phase=phase,
                owner_role='Fictional team role', depends_on=deps or [],
                duration_days=[10, 20] if days is None else days,
                finding_refs=['SYN-F-' + key], evidence_refs=['synthetic:' + key],
                practice_change='Proposed practice change', observable_outcome='Outcome to measure',
                assumptions=['Synthetic duration range; capacity unverified.'])


def document(*rows):
    return dict(schema_version=1, title='SYNTHETIC test', synthetic=True,
                assumptions=['Not a real engagement.'], recommendations=list(rows or [item()]))


def indexed(data):
    return {row['id']: row for row in roadmap.plan(data)['recommendations']}


def edit_csv(text, change):
    reader = csv.DictReader(io.StringIO(text, newline=''))
    fields, rows = reader.fieldnames, list(reader)
    change(rows)
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class PlannerTests(unittest.TestCase):
    def test_sample_expected_results(self):
        report = roadmap.plan(roadmap.strict_loads((HERE/'synthetic_recommendations.json').read_text()))
        self.assertEqual(report['summary'], dict(total=12, planned=10, unscheduled=2, phase_at_risk=1, phase_conflicts=1))
        rows = {row['id']: row for row in report['recommendations']}
        self.assertEqual((rows['R03']['start_min'], rows['R03']['finish_max']), (25, 80))
        self.assertEqual((rows['R06']['start_min'], rows['R06']['finish_max']), (90, 150))
        self.assertEqual((rows['R07']['start_min'], rows['R07']['finish_max']), (180, 210))
        self.assertEqual(rows['R08']['status'], 'MISSING_DURATION')
        self.assertIn('owner_role_unknown', rows['R08']['issues'])
        self.assertEqual(rows['R09']['status'], 'BLOCKED_BY_UNSCHEDULED_PREREQUISITE')
        self.assertEqual(rows['R11']['phase_state'], 'AT_RISK')
        self.assertEqual((rows['R12']['start_min'], rows['R12']['start_max']), (105, 145))
        self.assertEqual(rows['R12']['phase_state'], 'OUTSIDE_PHASE')

    def test_diamond_uses_max_not_sum(self):
        rows = indexed(document(item('A', days=[5,10]), item('B',['A'],[10,15]),
                                item('C',['A'],[20,30]), item('D',['B','C'],[2,5])))
        self.assertEqual((rows['D']['start_min'], rows['D']['start_max']), (25,40))
        self.assertEqual(rows['B']['layer'], rows['C']['layer'])
        self.assertEqual(rows['D']['finish_max'],45)

    def test_unknown_is_not_zero_and_propagates(self):
        unknown = item('A'); unknown['duration_days'] = None
        rows = indexed(document(unknown,item('B',['A']),item('C',['B']),item('D',days=[0,0])))
        self.assertEqual(rows['A']['status'],'MISSING_DURATION')
        self.assertIsNone(rows['C']['finish_min'])
        self.assertEqual(rows['D']['finish_max'],0)

    def test_missing_reference_is_retained(self):
        rows = indexed(document(item('A',['missing']), item('B',['A']),item('C')))
        self.assertEqual(rows['A']['status'],'MISSING_PREREQUISITE')
        self.assertIn('missing_prerequisite:missing',rows['A']['issues'])
        self.assertEqual(rows['B']['status'],'BLOCKED_BY_UNSCHEDULED_PREREQUISITE')
        self.assertEqual(rows['C']['status'],'PLANNED')

    def test_cycle_and_blocked_descendant_not_misclassified_as_all_cyclic(self):
        rows=indexed(document(item('A',['B']),item('B',['A']),item('C',['A']),item('D')))
        for key in 'ABC':
            self.assertEqual(rows[key]['status'],'CYCLE_OR_BLOCKED_BY_CYCLE')
            self.assertIsNone(rows[key]['start_min'])
        self.assertEqual(rows['D']['status'],'PLANNED')

    def test_self_cycle(self):
        self.assertEqual(indexed(document(item('A',['A'])))['A']['status'],'CYCLE_OR_BLOCKED_BY_CYCLE')

    def test_exact_phase_boundaries(self):
        for duration,phase in [(90,'0-90'),(180,'90-180')]:
            rows=indexed(document(item('A',days=[duration,duration]),item('B',['A'],[0,0],phase)))
            self.assertEqual(rows['B']['phase_state'],'OUTSIDE_PHASE')
        self.assertEqual(indexed(document(item('A',phase='90-180')))['A']['start_min'],90)
        self.assertEqual(indexed(document(item('A',phase='180+')))['A']['start_min'],180)

    def test_spanning_does_not_invent_start_conflict(self):
        row=indexed(document(item('A',days=[80,110])))['A']
        self.assertEqual(row['phase_state'],'ON_PHASE')
        self.assertIn('work_may_span_phase_boundary',row['issues'])

    def test_range_crossing_phase_is_at_risk(self):
        row=indexed(document(item('A',days=[80,100]),item('B',['A'])))['B']
        self.assertEqual(row['phase_state'],'AT_RISK')

    def test_missing_support_and_owner_not_silently_filled(self):
        a=item(); a.update(owner_role=None,evidence_refs=[],finding_refs=[],assumptions=[])
        row=indexed(document(a))['A']
        self.assertEqual(set(row['issues']),{'owner_role_unknown','evidence_refs_missing','finding_refs_missing','assumptions_missing'})
        self.assertIsNone(row['owner_role'])

    def test_duplicate_ids(self):
        with self.assertRaisesRegex(roadmap.PlanError,'duplicate recommendation'):
            roadmap.plan(document(item(),item()))

    def test_bad_durations(self):
        for value in ([True,2],[1,False],[1.0,2],[-1,2],[3,2],[2],[],{},'unknown'):
            with self.subTest(value=value),self.assertRaises(roadmap.PlanError):
                row=item(); row['duration_days']=value; roadmap.plan(document(row))

    def test_bad_fields(self):
        for key,value in [('id','bad id'),('group',[]),('phase','soon'),('depends_on',['B','B']),('owner_role',' '),('evidence_refs',[3]),('practice_change','')]:
            with self.subTest(key=key),self.assertRaises(roadmap.PlanError):
                row=item(); row[key]=value; roadmap.plan(document(row))

    def test_bad_document(self):
        for key,value in [('schema_version',True),('synthetic','true'),('recommendations',[]),('assumptions',[None]),('title',' ')]:
            with self.subTest(key=key),self.assertRaises(roadmap.PlanError):
                doc=document(); doc[key]=value; roadmap.plan(doc)

    def test_unknown_fields_rejected(self):
        doc=document(); doc['recommendations'][0]['calendar_invitation']='no'
        with self.assertRaises(roadmap.PlanError): roadmap.plan(doc)

    def test_strict_json(self):
        for text in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}','{broken'):
            with self.subTest(text=text),self.assertRaises(roadmap.PlanError): roadmap.strict_loads(text)

    def test_input_not_mutated(self):
        doc=document(item('B',['A']),item('A')); original=copy.deepcopy(doc)
        roadmap.plan(doc); self.assertEqual(doc,original)

    def test_permutation_preserves_plan(self):
        doc=document(item('C',['A','B']),item('B'),item('A'))
        before=roadmap.plan(doc); doc['recommendations'].reverse(); after=roadmap.plan(doc)
        self.assertEqual(before['recommendations'],after['recommendations'])
        self.assertEqual(before['dependency_layers'],after['dependency_layers'])
        self.assertNotEqual(before['input_sha256'],after['input_sha256'])

    def test_random_dag_properties(self):
        rng=random.Random(8547)
        for trial in range(25):
            source=[]
            for n in range(30):
                possible=[r['id'] for r in source]
                deps=rng.sample(possible,min(len(possible),rng.randrange(4)))
                lo=rng.randrange(10); hi=lo+rng.randrange(10)
                source.append(item(f'R{n}',deps,[lo,hi],rng.choice(list(roadmap.PHASES))))
            rows=indexed(document(*source))
            for row in rows.values():
                self.assertLessEqual(row['start_min'],row['start_max'])
                for dep in row['depends_on']:
                    self.assertGreaterEqual(row['start_min'],rows[dep]['finish_min'])
                    self.assertGreaterEqual(row['start_max'],rows[dep]['finish_max'])
                    self.assertGreater(row['layer'],rows[dep]['layer'])

    def test_deep_chain_no_recursion_limit(self):
        data=document(*[item(f'R{i}',[f'R{i-1}'] if i else [],[1,1]) for i in range(1500)])
        self.assertEqual(indexed(data)['R1499']['finish_max'],1500)


class InterchangeTests(unittest.TestCase):
    def test_full_csv_roundtrip(self):
        doc=roadmap.strict_loads((HERE/'synthetic_recommendations.json').read_text())
        self.assertEqual(roadmap.from_csv(roadmap.table_csv(roadmap.plan(doc))),doc)

    def test_unicode_multiline_locators_and_formulas_roundtrip(self):
        for value in ('=SUM(1,2)','+draft','-draft','@role',"'literal", "'+1",'\tvalue','\nnotes','  =formula','Résumé | Δ\nline two','source/'+('長'*4000)):
            with self.subTest(value=value[:20]):
                doc=document(); row=doc['recommendations'][0]
                row['title']=value; row['evidence_refs']=[value]
                text=roadmap.table_csv(roadmap.plan(doc))
                self.assertEqual(roadmap.from_csv(text),doc)
                raw=next(csv.DictReader(io.StringIO(text)))['title']
                self.assertFalse(raw.lstrip().startswith(('=','+','-','@')))

    def test_metadata_disagreement(self):
        text=roadmap.table_csv(roadmap.plan(document(item('A'),item('B'))))
        edited=edit_csv(text,lambda rows: rows[1].update(synthetic='false'))
        with self.assertRaisesRegex(roadmap.PlanError,'metadata differs'): roadmap.from_csv(edited)

    def test_forged_derived_columns_are_ignored_and_recomputed(self):
        a=item(); a['duration_days']=None
        text=roadmap.table_csv(roadmap.plan(document(a)))
        edited=edit_csv(text,lambda rows: rows[0].update(status='COMPLETE',start_min='0',finish_max='0',planning_state='APPROVED'))
        report=roadmap.plan(roadmap.from_csv(edited))
        self.assertEqual(report['planning_state'],'DRAFT_NON_AUTHORITATIVE')
        self.assertEqual(report['recommendations'][0]['status'],'MISSING_DURATION')
        self.assertIsNone(report['recommendations'][0]['finish_max'])

    def test_edited_inputs_change_plan(self):
        a=item('A'); a['duration_days']=None
        text=roadmap.table_csv(roadmap.plan(document(a,item('B',['A']))))
        edited=edit_csv(text,lambda rows: rows[0].update(duration_days='[5, 8]'))
        self.assertEqual(indexed(roadmap.from_csv(edited))['B']['start_max'],8)

    def test_headers_cells_and_empty_csv(self):
        text=roadmap.table_csv(roadmap.plan(document()))
        header,body=text.split('\n',1)
        for bad in (header+'\n',header+',id\n'+body,'wrong\nvalue\n',header+'\nx\n',header+'\n'+body.rstrip('\n')+',extra\n'):
            with self.subTest(bad=bad[:30]),self.assertRaises(roadmap.PlanError): roadmap.from_csv(bad)

    def test_html_escapes_input_and_has_semantic_headers(self):
        a=item(); a['title']='<script>alert(1)</script>'
        page=roadmap.render_html(roadmap.plan(document(a)))
        self.assertNotIn('<script>',page)
        self.assertIn('&lt;script&gt;',page)
        self.assertIn("scope='row'",page); self.assertIn('<caption>',page)
        self.assertIn("role='region'",page); self.assertIn("tabindex='0'",page)
        self.assertIn('DRAFT_NON_AUTHORITATIVE',page)
        self.assertIn('UNKNOWN',roadmap.render_html(roadmap.plan(document(dict(a,owner_role=None)))))

    def test_markdown_quotes_table_cells(self):
        a=item(); a['title']='A | B\nC <tag>'
        text=roadmap.markdown(roadmap.plan(document(a)))
        self.assertIn('A \\| B<br>C &lt;tag&gt;',text)

    def test_bundle_manifest_and_determinism(self):
        report=roadmap.plan(document())
        with tempfile.TemporaryDirectory() as tmp:
            first,second=Path(tmp)/'one',Path(tmp)/'two'
            a=roadmap.write_bundle(report,first); b=roadmap.write_bundle(report,second)
            self.assertEqual(a,b)
            for name,digest in a['outputs'].items():
                self.assertEqual(hashlib.sha256((first/name).read_bytes()).hexdigest(),digest)
                self.assertEqual((first/name).read_bytes(),(second/name).read_bytes())
            self.assertEqual((first/'manifest.json').read_bytes(),(second/'manifest.json').read_bytes())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'existing'; dest.mkdir(); marker=dest/'mine'; marker.write_text('retained')
            with self.assertRaises(FileExistsError): roadmap.write_bundle(roadmap.plan(document()),dest)
            self.assertEqual(marker.read_text(),'retained'); self.assertEqual(list(dest.iterdir()),[marker])

    def test_real_cli_json_then_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            first,second=Path(tmp)/'one',Path(tmp)/'two'
            command=[sys.executable,str(HERE/'roadmap.py')]
            run=subprocess.run(command+[str(HERE/'synthetic_recommendations.json'),str(first)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            rerun=subprocess.run(command+[str(first/'planning_table.csv'),str(second),'--require-plannable'],capture_output=True,text=True)
            self.assertEqual(rerun.returncode,3,rerun.stderr)
            self.assertEqual((first/'manifest.json').read_bytes(),(second/'manifest.json').read_bytes())

    def test_cli_bad_input_returns_two_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,dest=Path(tmp)/'bad.json',Path(tmp)/'output'; source.write_text('{broken')
            run=subprocess.run([sys.executable,str(HERE/'roadmap.py'),str(source),str(dest)],capture_output=True,text=True)
            self.assertEqual(run.returncode,2); self.assertFalse(dest.exists())

    def test_fictional_evidence_locators_resolve(self):
        doc=roadmap.strict_loads((HERE/'synthetic_recommendations.json').read_text())
        evidence=(HERE/'synthetic_evidence.md').read_text()
        for row in doc['recommendations']:
            self.assertIn('Finding reference: `'+row['finding_refs'][0]+'`',evidence)
            self.assertIn('## '+row['evidence_refs'][0].split('#')[1],evidence)


if __name__ == '__main__':
    unittest.main()
