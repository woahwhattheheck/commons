"""UIOWA-048 actual-engine checks, including optimized child CLI execution."""
import copy
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'revenue/uiowa_rfq_18649_doc_usability'
SPEC = importlib.util.spec_from_file_location('uiowa048_helio_assess', KIT / 'assess.py')
a = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(a)


def encoded(rows, header):
    text = io.StringIO(newline='')
    writer = csv.DictWriter(text, fieldnames=header, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return text.getvalue().encode('utf-8')


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.docs = a.parse_csv((KIT/'examples/rehearsal_inventory.csv').read_bytes(), a.INVENTORY, 'inventory')
        self.tasks = a.parse_csv((KIT/'examples/rehearsal_tasks.csv').read_bytes(), a.TASKS, 'tasks')

    def run_report(self, **kwargs):
        return a.assess(self.docs, self.tasks, as_of='2026-09-19', **kwargs)

    def codes(self, entity=None):
        return {r['code'] for r in self.run_report()['follow_ups'] if entity is None or r['entity_id']==entity}

    def test_complete_rehearsal_states(self):
        r=self.run_report()
        self.assertEqual(r['summary']['document_count'],4)
        self.assertEqual(r['summary']['task_count'],9)
        self.assertEqual({t['task_id']:t['assessment'] for t in r['tasks']}, {
            'T01':'RECORDED_COMPLETED','T02':'RECORDED_BLOCKED','T03':'NOT_OBSERVED',
            'T04':'REPORTED_COMPLETED','T05':'RECORDED_ASSISTED','T06':'ARTIFACT_REVIEW_ONLY',
            'T07':'AFTER_AS_OF','T08':'DATE_UNKNOWN','T09':'NOT_OBSERVED'})

    def test_four_doc_kinds_exercised(self):
        self.assertEqual({d['doc_kind'] for d in self.docs},a.KINDS)

    def test_original_inventory_prefix_retained(self):
        raw=(KIT/'examples/synthetic_inventory.csv').read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        self.assertEqual(blob,'16fdc2f5647ba49e7adf6ac1fb42927f6630b4bb')
        self.assertTrue((KIT/'examples/rehearsal_inventory.csv').read_bytes().startswith(raw))

    def test_no_score_or_correctness_inference(self):
        r=self.run_report()
        self.assertNotIn('score',r)
        self.assertTrue(all(d['content_correctness']=='NOT_DETERMINED' for d in r['documents']))
        self.assertEqual(r['documents'][1]['review_recency'],'REVIEW_DUE')
        self.assertIn('REVIEW_AGE_PROMPT',self.codes('D02'))

    def test_age_threshold_is_explicit_and_not_task_outcome(self):
        left=self.run_report(review_age_days=0)
        right=self.run_report(review_age_days=36500)
        self.assertNotEqual(left['documents'][0]['review_recency'],right['documents'][0]['review_recency'])
        self.assertEqual(left['tasks'],right['tasks'])

    def test_unknown_review_age_not_zero(self):
        d=self.run_report()['documents'][3]
        self.assertIsNone(d['review_age_days'])
        self.assertEqual(d['review_recency'],'UNKNOWN')

    def test_future_review_is_not_current(self):
        self.docs[0]['last_reviewed']='2026-09-20'
        self.assertEqual(self.run_report()['documents'][0]['review_recency'],'AFTER_AS_OF')
        self.assertIn('REVIEW_AFTER_AS_OF',self.codes('D01'))

    def test_future_observation_not_completed(self):
        self.assertEqual(self.run_report()['tasks'][6]['assessment'],'AFTER_AS_OF')

    def test_reported_and_observed_accounts_retained(self):
        d=self.run_report()['disagreements']
        self.assertEqual(len(d),1)
        self.assertEqual({x['task_id'] for x in d[0]['accounts']},{'T02','T04'})
        self.assertIn('DIVERGENT_TASK_ACCOUNTS',self.codes())

    def test_no_implicit_join_on_task_name(self):
        self.tasks[1]['comparison_key']=''; self.tasks[3]['comparison_key']=''
        self.assertEqual(self.run_report()['disagreements'],[])

    def test_distinct_groups_do_not_join_comparison_keys(self):
        self.tasks[3]['group']='ESS'
        self.assertEqual(self.run_report()['disagreements'],[])

    def test_future_accounts_do_not_create_disagreement(self):
        self.tasks[3]['observed_on']='2026-09-20'
        self.assertEqual(self.run_report()['disagreements'],[])

    def test_cross_group_reference_is_question_not_rejection(self):
        self.assertIn('CROSS_GROUP_REFERENCE',self.codes('T08'))
        self.assertEqual(self.run_report()['tasks'][7]['linked_documents'][0]['doc_id'],'D04')

    def test_missing_document_does_not_infer_absent_practice(self):
        self.assertEqual(self.run_report()['tasks'][2]['assessment'],'NOT_OBSERVED')
        self.assertIn('DOCUMENT_NOT_LOCATED',self.codes('D03'))

    def test_unknown_and_empty_link_inventories_differ(self):
        self.assertIn('DOCUMENT_LINKS_UNKNOWN',self.codes('T09'))
        self.assertNotIn('EXPECTED_SUPPORT_NOT_LINKED',self.codes('T09'))
        self.tasks[8]['doc_ids']='[]'; self.tasks[8]['required_doc_kinds']='["onboarding_guide"]'
        self.assertIn('NO_DOCUMENT_LINKS',self.codes('T09'))
        self.assertIn('EXPECTED_SUPPORT_NOT_LINKED',self.codes('T09'))

    def test_unresolved_id_never_fuzzy_joins(self):
        self.tasks[0]['doc_ids']='["d01"]'
        self.assertEqual(self.run_report()['tasks'][0]['unresolved_document_ids'],['d01'])

    def test_whitespace_and_punctuation_ids_preserved(self):
        self.docs[0]['doc_id']=' D|01_[a] '
        self.tasks[0]['doc_ids']=json.dumps([' D|01_[a] '])
        self.assertEqual(self.run_report()['tasks'][0]['linked_documents'][0]['doc_id'],' D|01_[a] ')

    def test_extra_fields_and_multiline_notes_preserved(self):
        self.docs[0]['extra']='=HYPERLINK("x")\nUnicode Ω'
        self.tasks[0]['notes']='line one\r\nline two'
        r=self.run_report()
        self.assertEqual(r['inventory_records'][0]['extra'],self.docs[0]['extra'])
        self.assertEqual(r['task_records'][0]['notes'],self.tasks[0]['notes'])

    def test_reordering_inputs_does_not_change_output(self):
        expected=a.json_bytes(self.run_report())
        self.docs.reverse(); self.tasks.reverse()
        self.assertEqual(a.json_bytes(self.run_report()),expected)

    def test_inputs_not_mutated(self):
        before=copy.deepcopy((self.docs,self.tasks))
        self.run_report()
        self.assertEqual((self.docs,self.tasks),before)

    def test_empty_template_is_not_coverage(self):
        r=a.assess([],[],as_of='2026-09-19')
        self.assertEqual(r['summary']['task_count'],0)
        self.assertIn('does not establish complete coverage',a.markdown(r))

    def test_no_observation_cannot_promote_result(self):
        self.tasks[2]['result']='completed'
        self.assertEqual(self.run_report()['tasks'][2]['assessment'],'NOT_OBSERVED')
        self.assertIn('OUTCOME_WITHOUT_OBSERVATION',self.codes('T03'))

    def test_superseded_document_stays_unresolved(self):
        self.docs[0]['state']='superseded'
        self.assertIn('DOCUMENT_SUPPORT_UNRESOLVED',self.codes('T01'))

    def test_missing_source_reference_diagnostic(self):
        self.docs[0]['reference']=''
        self.assertIn('SOURCE_REFERENCE_MISSING',self.codes('D01'))

    def test_invalid_parameters(self):
        for value in (True,False,-1,36501,1.0,'180',None):
            with self.subTest(value=value), self.assertRaises(a.InputError):
                self.run_report(review_age_days=value)
        with self.assertRaises(a.InputError): self.run_report(context='verified_university')

    def test_invalid_date_forms(self):
        for value in ('20260919','2026-W38-6','2026-02-30','2026-9-1',''):
            with self.subTest(value=value), self.assertRaises(a.InputError):
                a.assess(self.docs,self.tasks,as_of=value)

    def test_csv_structure_and_decode_failures(self):
        header=','.join(a.INVENTORY)
        for raw in (b'\xff',b'',(header+',doc_id\n').encode(),
                    (header+',\n').encode(),(header+'\nD01,ESS\n').encode(),
                    (header+'\n"unterminated').encode()):
            with self.subTest(raw=raw),self.assertRaises(a.InputError):
                a.parse_csv(raw,a.INVENTORY,'inventory')

    def test_bom_supported(self):
        data=(KIT/'examples/rehearsal_inventory.csv').read_bytes()
        self.assertEqual(a.parse_csv(b'\xef\xbb\xbf'+data,a.INVENTORY,'inventory'),self.docs)

    def test_wrong_python_types_and_duplicate_ids(self):
        bad=copy.deepcopy(self.docs); bad[0]['reference']=None
        with self.assertRaises(a.InputError): a.assess(bad,self.tasks,as_of='2026-09-19')
        with self.assertRaises(a.InputError): a.assess(self.docs+[self.docs[0]],self.tasks,as_of='2026-09-19')
        with self.assertRaises(a.InputError): a.assess(self.docs,self.tasks+[self.tasks[0]],as_of='2026-09-19')

    def test_bounded_transport_and_cells(self):
        with self.assertRaises(a.InputError): a.parse_csv(b'x'*(a.MAX_BYTES+1),a.INVENTORY,'inventory')
        self.docs[0]['notes']='x'*(a.MAX_CELL+1)
        with self.assertRaises(a.InputError): self.run_report()
        self.docs[0]['notes']='\0'
        with self.assertRaises(a.InputError): self.run_report()

    def test_json_list_errors(self):
        for value in ('D01','[1]','["D01","D01"]','null','{}','[NaN]','[""]'):
            self.tasks[0]['doc_ids']=value
            with self.subTest(value=value),self.assertRaises(a.InputError): self.run_report()

    def test_markdown_is_passive_and_structurally_escaped(self):
        self.docs[0]['reference']='[run](javascript:bad)<script>\n|`'
        md=a.markdown(self.run_report())
        self.assertNotIn('<script>',md)
        self.assertIn('\\[run\\]',md)
        self.assertIn('\\|',md)
        self.assertIn('&lt;script&gt;',md)

    def test_exhaustive_evidence_result_date_oracle_and_csv_parity(self):
        count=0
        for evidence,result,when in itertools.product(sorted(a.EVIDENCE),sorted(a.RESULTS),
                                                      ('','2026-09-17','2026-09-20')):
            row=copy.deepcopy(self.tasks[0]); row.update(evidence_type=evidence,result=result,observed_on=when)
            if evidence=='not_observed': expected='NOT_OBSERVED'
            elif not when: expected='DATE_UNKNOWN'
            elif when>'2026-09-19': expected='AFTER_AS_OF'
            elif evidence=='artifact_review': expected='ARTIFACT_REVIEW_ONLY'
            elif result=='unknown': expected='OUTCOME_UNKNOWN'
            else: expected=('RECORDED_' if evidence=='observed_walkthrough' else 'REPORTED_')+result.upper()
            with self.subTest(evidence=evidence,result=result,when=when):
                direct=a.assess(self.docs,[row],as_of='2026-09-19')
                self.assertEqual(direct['tasks'][0]['assessment'],expected)
                loaded=a.parse_csv(encoded([row],list(row)),a.TASKS,'tasks')
                self.assertEqual(a.assess(self.docs,loaded,as_of='2026-09-19'),direct)
            count+=1
        self.assertEqual(count,48)


class CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.inventory=self.base/'inventory.csv'
        self.tasks=self.base/'tasks.csv'
        self.inventory.write_bytes((KIT/'examples/rehearsal_inventory.csv').read_bytes())
        self.tasks.write_bytes((KIT/'examples/rehearsal_tasks.csv').read_bytes())

    def invoke(self, output, as_of='2026-09-19'):
        command=[sys.executable]+(['-O'] if sys.flags.optimize else [])+[str(KIT/'assess.py'),
                 '--inventory',str(self.inventory),'--tasks',str(self.tasks),'--as-of',as_of,'--output',str(output)]
        return subprocess.run(command,capture_output=True,text=True,timeout=15)

    def test_reproducible_cli_and_exact_input_output_receipt(self):
        one=self.base/'one'; two=self.base/'two'
        for out in (one,two):
            p=self.invoke(out); self.assertEqual(p.returncode,0,p.stderr)
            receipt=json.loads((out/'receipt.json').read_text())
            for name,path in [('inventory.csv',self.inventory),('tasks.csv',self.tasks)]:
                self.assertEqual(receipt['inputs'][name]['sha256'],a.digest(path.read_bytes()))
            for name,metadata in receipt['outputs'].items():
                self.assertEqual(metadata['sha256'],a.digest((out/name).read_bytes()))
                self.assertEqual(metadata['bytes'],len((out/name).read_bytes()))
        self.assertEqual({p.name:p.read_bytes() for p in one.iterdir()},
                         {p.name:p.read_bytes() for p in two.iterdir()})

    def test_existing_output_directory_untouched(self):
        out=self.base/'exists'; out.mkdir(); (out/'sentinel').write_bytes(b'unchanged')
        p=self.invoke(out); self.assertEqual(p.returncode,2)
        self.assertEqual(list(out.iterdir()),[out/'sentinel'])
        self.assertEqual((out/'sentinel').read_bytes(),b'unchanged')

    def test_input_alias_outputs_refused_without_data_loss(self):
        original=self.inventory.read_bytes()
        hard=self.base/'hard'; os.link(self.inventory,hard)
        symlink=self.base/'symlink'; symlink.symlink_to(self.inventory)
        for out in (self.inventory,hard,symlink):
            with self.subTest(out=out):
                p=self.invoke(out); self.assertEqual(p.returncode,2,p.stderr)
                self.assertEqual(self.inventory.read_bytes(),original)

    def test_invalid_input_creates_no_output(self):
        self.tasks.write_bytes(b'\xff'); out=self.base/'nope'
        p=self.invoke(out); self.assertEqual(p.returncode,2)
        self.assertIn('ERROR:',p.stderr); self.assertNotIn('Traceback',p.stderr)
        self.assertFalse(out.exists())

    def test_invalid_cutoff_creates_no_output(self):
        out=self.base/'nope'; p=self.invoke(out,'2026-02-31')
        self.assertEqual(p.returncode,2); self.assertFalse(out.exists())

    def test_missing_parent_is_controlled_error(self):
        p=self.invoke(self.base/'missing'/'out')
        self.assertEqual(p.returncode,2); self.assertNotIn('Traceback',p.stderr)

    def test_captured_input_used_not_reread(self):
        report=a.assess([],[],as_of='2026-09-19')
        capture={'inventory.csv':b'original inventory','tasks.csv':b'original tasks'}
        out=self.base/'snapshot'
        a.write_bundle(out,report,capture)
        receipt=json.loads((out/'receipt.json').read_text())
        self.assertEqual(receipt['inputs']['inventory.csv']['sha256'],a.digest(b'original inventory'))

    def test_write_failure_has_no_success_receipt(self):
        report=a.assess([],[],as_of='2026-09-19'); out=self.base/'partial'
        with mock.patch.object(Path,'open',side_effect=OSError('simulated full device')):
            with self.assertRaises(OSError): a.write_bundle(out,report,{})
        self.assertFalse((out/'receipt.json').exists())


if __name__=='__main__': unittest.main()
