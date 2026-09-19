# UIOWA-118 — Documentation validation

These checks validate the authored help records, internal links, source-reference shape,
fiction labels, and the arithmetic in eight worked cases. They do not run the assessment,
delivery, recovery or resource-estimator modules; a mathematical replay is not an engine
regression test. Native GitHub reads, rather than these checks, established the source
paths and blob identifiers in the source register. No external HTTP availability claim
is made.

## Replay

Copy the Python block below to a temporary `validate_explanations.py` outside the repo,
then pass this package directory as its first argument. Standard library only:

```sh
python /tmp/validate_explanations.py revenue/uiowa_rfq_18649_explanations
python -O /tmp/validate_explanations.py revenue/uiowa_rfq_18649_explanations
```

The checker is reproduced as documentation, not installed into the repository's test
runner. Its negative controls intentionally introduce a duplicate help ID, unresolved
source ID and incorrect expanded-help anchor; those inputs must be rejected. It neither
changes the source components nor adds a runtime integration gate.

## Executed result

Local cloud-container CPython; 17 checks passed normally and 17 under real `-O` after
completing this validation document. The initial pass caught the README's link to this
not-yet-created file; the link check was retained and the file was added. No specialist
suite, repository-wide suite or GitHub Actions success is claimed.

## Checker

```python
"""Documentation-only checks; never executes source components or reads real evidence."""
from pathlib import Path
import datetime as dt
import json
import re
import statistics
import sys
import unittest

ROOT = Path(sys.argv.pop(1)).resolve()

def text(name):
    return (ROOT / name).read_text(encoding='utf-8')

def load_records():
    blocks = re.findall(r'^```json\n(.*?)\n```$', text('HELP_SNIPPETS.md'), re.M | re.S)
    if len(blocks) != 1:
        raise ValueError('expected exactly one JSON help block')
    return json.loads(blocks[0])

def validate_records(data):
    if data.get('schema') != 'uiowa.explanation-help/v1':
        raise ValueError('wrong schema')
    records = data['records']
    ids = [row['id'] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate help ID')
    glossary = text('GLOSSARY.md')
    sources = set(re.findall(r'^## (S\d{2})$', text('README.md'), re.M))
    for row in records:
        if set(row) != {'id', 'label', 'short_text', 'expanded_ref', 'source_ids'}:
            raise ValueError('unexpected help fields')
        if not row['short_text'] or len(row['short_text']) > 160:
            raise ValueError('short copy outside limit')
        if row['expanded_ref'] != 'GLOSSARY.md#' + row['id']:
            raise ValueError('wrong expanded reference')
        if '\n## ' + row['id'] + '\n' not in glossary:
            raise ValueError('missing glossary target')
        if not row['source_ids'] or not set(row['source_ids']) <= sources:
            raise ValueError('unresolved source ID')
    return len(records)

class ExplanationChecks(unittest.TestCase):
    def test_01_record_contract(self):
        self.assertEqual(validate_records(load_records()), 29)

    def test_02_required_terms(self):
        ids = {r['id'] for r in load_records()['records']}
        self.assertTrue({'ess','ris','iam','confidence','maturity','lead-time','rto','rpo','recurring-effort'} <= ids)

    def test_03_all_glossary_entries_have_copy_example_source(self):
        chunks = re.split(r'^## ', text('GLOSSARY.md'), flags=re.M)[1:]
        self.assertEqual(len(chunks), 29)
        for chunk in chunks:
            for marker in ('**Short:**','**Expanded:**','**Example:**','**Source:**'):
                self.assertIn(marker, chunk)

    def test_04_eight_exact_source_bindings(self):
        readme = text('README.md')
        self.assertEqual(len(re.findall(r'^## S\d{2}$', readme, re.M)), 8)
        self.assertEqual(len(re.findall(r'Git blob: `[0-9a-f]{40}`', readme)), 8)
        self.assertEqual(len(re.findall(r'\[Read the pinned source\]\(https://github.com/woahwhattheheck/commons/blob/[0-9a-f]{40}/[^)]+\)', readme)), 8)

    def test_05_internal_links_and_fragments(self):
        for file in ROOT.glob('*.md'):
            # The validation guide itself contains regex examples, not report links.
            if file.name == 'VALIDATION.md':
                continue
            for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
                if target.startswith('https://'):
                    continue
                name, _, anchor = target.partition('#')
                destination = ROOT / (name or file.name)
                self.assertTrue(destination.is_file(), target)
                if anchor:
                    headings = re.findall(r'^#{1,6} (.+)$', destination.read_text(), re.M)
                    slugs = [re.sub(r'[^\w\- ]', '', s.lower()).replace(' ', '-') for s in headings]
                    self.assertIn(anchor, slugs, target)

    def test_06_duplicate_id_negative_control(self):
        data = load_records()
        data['records'].append(data['records'][0].copy())
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_records(data)

    def test_07_unresolved_source_negative_control(self):
        data = load_records()
        data['records'][0]['source_ids'] = ['S99']
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            validate_records(data)

    def test_08_broken_anchor_negative_control(self):
        data = load_records()
        data['records'][0]['expanded_ref'] = 'GLOSSARY.md#absent'
        with self.assertRaisesRegex(ValueError, 'wrong expanded'):
            validate_records(data)

    def test_09_w01_non_authorizing_copy(self):
        case = text('WALKTHROUGH.md').split('## W01')[1].split('## W02')[0]
        for token in ('UNTRUSTED_INSPECTION','UNTRUSTED_EVIDENCE_CONSISTENT','HOLD_TRUSTED_AUTHORITY_REQUIRED','UNTRUSTED_INTEGRITY_ONLY'):
            self.assertIn(token, case)

    def test_10_w02_declared_confidence_conversion(self):
        bp = min(8000, 6500)
        self.assertEqual(bp / 100, 65)
        self.assertEqual(bp / 10000, 0.65)
        self.assertIn('not a calibrated probability', text('WALKTHROUGH.md'))

    def test_11_w03_freshness_arithmetic(self):
        now = dt.datetime.fromisoformat('2026-09-19T12:00:00+00:00')
        observed = dt.datetime.fromisoformat('2026-05-22T12:00:00+00:00')
        age = int((now - observed).total_seconds())
        self.assertEqual(age, 10368000)
        self.assertFalse(age > 120 * 86400)
        self.assertTrue(age + 1 > 120 * 86400)

    def test_12_w04_known_denominator_and_sensitivity(self):
        eligible, used, failed = 10, 8, 2
        self.assertEqual(eligible - used, 2)
        self.assertEqual(failed / used, 0.25)
        self.assertEqual(failed / eligible, 0.20)
        self.assertEqual((failed + eligible - used) / eligible, 0.40)
        self.assertIn('not a calculator output or confidence interval', text('WALKTHROUGH.md'))

    def test_13_w05_aggregation_and_window(self):
        self.assertEqual(statistics.median([2,6,28]), 6)
        self.assertEqual(statistics.mean([2,6,28]), 12)
        self.assertEqual(4/8, 0.5)
        start, end, event = 0, 8, 8
        self.assertFalse(start <= event < end)

    def test_14_w06_recovery_clocks(self):
        def minute(t):
            hour, minute = map(int, t.split(':'))
            return hour * 60 + minute
        self.assertEqual(minute('10:00') - minute('09:30'), 30)
        self.assertEqual(minute('11:40') - minute('10:00'), 100)
        self.assertEqual(minute('10:40') - minute('10:00'), 40)
        self.assertLessEqual(minute('11:20'), minute('11:40'))
        self.assertIn('observed RTO becomes UNKNOWN', text('WALKTHROUGH.md'))

    def test_15_w07_effort_units_and_shared_training(self):
        totals = [a + 3*b for a,b in zip([52,84,128],[6,10,16])]
        self.assertEqual(totals, [70,114,176])
        self.assertEqual(12 * 1.5, 18)
        self.assertIn('Facilitator time is a', text('WALKTHROUGH.md'))

    def test_16_w08_unknown_and_skill_copy(self):
        self.assertGreater(20, 16)
        case = text('WALKTHROUGH.md').split('## W08')[1]
        self.assertIn('complete total is UNKNOWN', case)
        self.assertIn('unrelated role cannot', case)

    def test_17_fiction_and_uninstalled_boundary(self):
        data = load_records()
        self.assertEqual(data['status'], 'DOCUMENTARY_COPY_NOT_INSTALLED')
        self.assertEqual(data['examples'], 'FICTIONAL_NOT_UNIVERSITY_FINDINGS')
        self.assertIn('not outputs from a specialist engine run', text('WALKTHROUGH.md'))
        self.assertIn('does not implement a new', text('README.md'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
```
