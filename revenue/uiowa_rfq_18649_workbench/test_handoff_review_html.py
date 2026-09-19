"""Real-parent, offline-reader regression tests; no University data."""
from __future__ import annotations

import base64
import copy
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import handoff_review as hr
import handoff_review_html as view


class Parsed(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.elements=[]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag,dict(attrs)))

    def attrs(self, tag, **matching):
        return [attrs for name,attrs in self.elements if name==tag
                and all(attrs.get(k)==v for k,v in matching.items())]


def real_inputs():
    # Consume the existing generator and its actual parent fixtures, not a
    # separately invented report or another set of lookalike source records.
    with tempfile.TemporaryDirectory() as tmp:
        output=Path(tmp)/'rehearsal'
        hr.write_example(output)
        return hr.load_json(output/'report.json'), [
            ('analyst-a',hr.load_json(output/'analyst-a.json')),
            ('analyst-b',hr.load_json(output/'analyst-b.json')),
        ]



def decoded_result(text):
    href=Parsed(text).attrs('a',download='draft-reconciliation.json')[0]['href']
    return base64.b64decode(href.split(',',1)[1],validate=True)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.report,self.drafts=real_inputs()

    def render(self):
        return view.build_html(self.report,self.drafts,classification='SYNTHETIC_REHEARSAL')

    def test_real_compiler_path_retains_all_twelve_cells(self):
        doc=Parsed(self.render())
        cards=doc.attrs('article',**{'class':'cell'})
        self.assertEqual(len(cards),12)
        self.assertEqual([c['id'] for c in cards],[f'cell-{g}-{d}' for g,d in hr.CELLS])
        self.assertEqual(sum(c['data-pending']=='yes' for c in cards),11)

    def test_download_is_byte_exact_engine_result(self):
        self.assertEqual(decoded_result(self.render()),hr.canonical(hr.reconcile(self.report,self.drafts))+b'\n')

    def test_duplicate_twenty_labels_retains_pending_and_all_notes(self):
        draft=self.drafts[0][1]
        for cell in draft['cell_notes']:
            cell.update(disposition='TECHNICAL_DRAFT_NOTE',analyst_note='FICTIONAL: same note.')
        self.drafts=[(f'copy-{i:02}',copy.deepcopy(draft)) for i in range(20)]
        text=self.render()
        result=json.loads(decoded_result(text))
        self.assertEqual(len(result['review_queue']),12)
        self.assertEqual(result['distinct_handoff_content_count'],1)
        self.assertEqual(len(Parsed(text).attrs('section',**{'class':'note'})),240)
        self.assertIn('copy-19',text)

    def test_markup_unicode_and_line_breaks_are_literal(self):
        note='FICTIONAL: <em>not formatting</em> & résumé / 研究 / 🙂\nsecond line\tend'
        self.drafts[0][1]['cell_notes'][0]['analyst_note']=note
        text=self.render()
        self.assertEqual(Parsed(text).attrs('em'),[])
        self.assertIn('&lt;em&gt;not formatting&lt;/em&gt;',text)
        actual=json.loads(decoded_result(text))['assessment_cells'][0]['entries'][0]['analyst_note']
        self.assertEqual(actual,note)

    def test_full_length_notes_are_not_truncated(self):
        note='N'*3999+'Z'
        self.drafts[0][1]['cell_notes'][0]['analyst_note']=note
        self.assertIn(note,self.render())

    def test_input_bytes_and_values_not_mutated(self):
        saved=copy.deepcopy((self.report,self.drafts))
        self.render()
        self.assertEqual((self.report,self.drafts),saved)

    def test_order_of_supplied_drafts_does_not_change_html(self):
        text=self.render()
        self.drafts.reverse()
        self.assertEqual(text,self.render())

    def test_tampered_report_never_becomes_html(self):
        self.report['assessment_matrix'][0]['status']='READY'
        with self.assertRaises(hr.ReviewError):
            self.render()

    def test_wrong_draft_receipt_never_becomes_html(self):
        self.drafts[0][1]['report_receipt_sha256']='0'*64
        with self.assertRaises(hr.ReviewError):
            self.render()

    def test_missing_parent_is_not_stubbed_or_skipped(self):
        with patch.object(hr,'_parent_module',side_effect=hr.ReviewError('parent unavailable')):
            with self.assertRaisesRegex(hr.ReviewError,'parent unavailable'):
                self.render()

    def test_explicit_classification_is_required(self):
        with self.assertRaises(hr.ReviewError):
            view.build_html(self.report,self.drafts,classification='')
        text=view.build_html(self.report,self.drafts,classification='OPERATOR_DRAFT')
        self.assertIn('OPERATOR DRAFT',text)
        self.assertNotIn('SYNTHETIC REHEARSAL — fictional inputs',text)
        self.assertIn('Classification is operator-declared',text)

    def test_every_source_locator_and_record_is_retained(self):
        text=self.render()
        for row in self.report['evidence_authority']['sources']:
            self.assertIn(row['source_ref'],text)
            self.assertIn(row['source_content_sha256'],text)
            self.assertIn(row['observed_at'],text)
        self.assertIn('No source record supplied for this cell',text)

    def test_only_http_locators_are_clickable(self):
        for locator in ['synthetic://example/ref','file:///private/report','custom:opaque','not a link']:
            self.assertEqual(Parsed(view._locator(locator)).attrs('a'),[])
            self.assertIn(view._e(locator),view._locator(locator))
        self.assertEqual(Parsed(view._locator('https://example.org/a?q=1&z=2')).attrs('a')[0]['href'],
                         'https://example.org/a?q=1&z=2')

    def test_no_external_assets_and_fixed_script_hashes(self):
        parsed=Parsed(self.render())
        self.assertEqual(len(parsed.attrs('script')),1)
        self.assertFalse(any('src' in attrs for attrs in parsed.attrs('script')))
        self.assertEqual(parsed.attrs('link'),[])
        csp=parsed.attrs('meta',**{'http-equiv':'Content-Security-Policy'})[0]['content']
        self.assertIn("connect-src 'none'",csp)
        for source in (view.CSS,view.SCRIPT):
            value=base64.b64encode(hashlib.sha256(source.encode()).digest()).decode()
            self.assertIn('sha256-'+value,csp)
        self.assertFalse(any(key.startswith('on') for _,attrs in parsed.elements for key in attrs))

    def test_filters_have_explicit_stable_accessible_labels(self):
        labels=Parsed(self.render()).attrs('label')
        self.assertEqual({row['for'] for row in labels},{'group-filter','text-filter'})

    def test_all_links_have_existing_cell_targets(self):
        parsed=Parsed(self.render())
        ids=[attrs['id'] for _,attrs in parsed.elements if 'id' in attrs]
        self.assertEqual(len(ids),len(set(ids)))
        internal=[a['href'][1:] for a in parsed.attrs('a') if a.get('href','').startswith('#')]
        self.assertTrue(set(internal)<=set(ids))
        self.assertEqual(len(internal),13)

    def test_cli_roundtrip_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'report.json').write_bytes(hr.canonical(self.report))
            for label,draft in self.drafts:
                (root/f'{label}.json').write_bytes(hr.canonical(draft))
            script=Path(view.__file__)
            args=[sys.executable,str(script),str(root/'report.json'),'--classification','SYNTHETIC_REHEARSAL',
                  '--handoff','analyst-a',str(root/'analyst-a.json'),'--handoff','analyst-b',str(root/'analyst-b.json'),
                  '--output',str(root/'out.html')]
            result=subprocess.run(args,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            original=(root/'out.html').read_bytes()
            self.assertEqual(original,self.render().encode())
            again=subprocess.run(args,capture_output=True,text=True,timeout=10)
            self.assertEqual(again.returncode,2)
            self.assertEqual((root/'out.html').read_bytes(),original)
            self.assertNotIn(str(root),again.stderr)
            (root/'out.html').unlink()
            args.insert(1,'-O')
            optimized=subprocess.run(args,capture_output=True,text=True,timeout=10)
            self.assertEqual(optimized.returncode,0,optimized.stderr)
            self.assertEqual((root/'out.html').read_bytes(),original)

    def test_invalid_intake_creates_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'bad.json').write_text('{"schema":1,"schema":2}')
            output=root/'no.html'
            status=view.main([str(root/'bad.json'),'--handoff','a',str(root/'bad.json'),
                              '--classification','SYNTHETIC_REHEARSAL','--output',str(output)])
            self.assertEqual(status,2)
            self.assertFalse(output.exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
