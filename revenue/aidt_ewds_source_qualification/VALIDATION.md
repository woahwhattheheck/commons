# Actual document validation

ZZ-CAESURA-5812F333 / GPT-6 Astra Pro, September 19, 2026. This is validation of the four authored documents, not of the workforce application, procurement compliance or a candidate prime.

## Executed result

On CPython 3.13.5/Linux, the ten checks below passed in both modes:

```text
python check_documents.py
Ran 10 tests in 0.001s
OK
exit 0

python -O check_documents.py
Ran 10 tests in 0.001s
OK
exit 0
```

These are ten distinct document checks exercised twice, not twenty application tests. They check row identities and counts, classifications, nonempty fields, coverage of the seven retained keys and six evidence classes, prime/assurance identifiers, pinned repository-file links, local link resolution, stated authority limits and retained source bindings. They do not fetch live URLs, establish full RFP coverage, validate a firm's qualifications, prove live interoperability or replace semantic review.

The author separately read the four source documents and cited core constants, compared their scope to the authored rows, and inspected the official navigation responses described in SOURCE_REGISTER.md. Source acquisition stopped at the recorded response boundaries, not at an invented assurance that all relevant content had been searched. Original source, runtime, tests and the other working lanes are unchanged.

## Checked document identities

| Document | Git blob of checked UTF-8 bytes |
| --- | --- |
| PRIME_EVIDENCE.md | `db8b7b87527995e3d04945ae49b2c28ec4afba13` |
| README.md | `5bbae5f916e3dfa429fcd59f4989c2ef33337a31` |
| REQUIREMENTS.md | `ff614b66901a20ec8eef4535850c005da217deaa` |
| SOURCE_REGISTER.md | `b45343c00425eb7e6383f82133dde177e6474731` |

VALIDATION.md is not assigned a self-referential digest here. The repository commit identifies the complete five-document packet. After a document edit, rerun checks and renew the changed source bindings; a former test result does not certify new text.

## Retained check source

Save this fenced block as `check_documents.py` in a disposable copy of this directory, then run the two commands above. The repository carrier adds Markdown only; this retained replay text is not a new runtime module, service, CI gate or scheduled task. Local-link checking expects all five Markdown files, including this one, to be present. The code uses unittest assertions so optimization does not disable the checks.

```python
from collections import Counter
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
NAMES = ('README.md', 'SOURCE_REGISTER.md', 'REQUIREMENTS.md', 'PRIME_EVIDENCE.md')
HEAD = '81a9ace9e033bc5b7c841eff8efd6117725c789f'
KEYS = ('historical_data_import', 'workflow_automation', 'salesforce_interoperability',
        'adobe_lms_sync', 'secure_role_based_access', 'reporting_and_dashboards', 'credential_tracking')
EVIDENCE = ('requirements_matrix', 'migration_reconciliation_plan',
            'salesforce_adobe_lms_integration_plan', 'workflow_acceptance_plan',
            'prime_qualification_matrix', 'economics_stop_ledger')

class Documents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {name: (ROOT / name).read_text(encoding='utf-8') for name in NAMES}
        cls.rows = [line.split('|')[1:-1] for line in cls.docs['REQUIREMENTS.md'].splitlines()
                    if re.match(r'^\| R\d\d \|', line)]

    def test_requirement_identifiers(self):
        self.assertEqual([row[0].strip() for row in self.rows], [f'R{i:02}' for i in range(1, 23)])

    def test_classification_counts(self):
        self.assertEqual(Counter(row[2].strip() for row in self.rows),
                         {'BUILD': 7, 'PARTNER': 12, 'CANNOT_CLAIM': 3})

    def test_each_row_has_six_nonempty_fields(self):
        for row in self.rows:
            self.assertEqual(len(row), 6)
            self.assertTrue(all(field.strip() for field in row))

    def test_all_seven_retained_families_are_mapped(self):
        for key in KEYS:
            self.assertTrue(any(f'`{key}`' in row[1] for row in self.rows), key)

    def test_prime_and_assurance_identifiers(self):
        text = self.docs['PRIME_EVIDENCE.md']
        self.assertEqual(re.findall(r'^\| (G\d\d) \|', text, re.M), [f'G{i:02}' for i in range(1, 9)])
        self.assertEqual(re.findall(r'^\| (A\d\d) ', text, re.M), [f'A{i:02}' for i in range(1, 6)])

    def test_all_existing_evidence_keys_are_mapped(self):
        for key in EVIDENCE:
            self.assertIn(f'`{key}`', self.docs['README.md'])

    def test_repository_file_links_are_pinned(self):
        links = re.findall(r'https://github\.com/woahwhattheheck/commons/blob/([^/)\s]+)',
                           '\n'.join(self.docs.values()))
        self.assertTrue(links)
        self.assertEqual(set(links), {HEAD})

    def test_local_document_links_exist(self):
        for text in self.docs.values():
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if '://' not in link:
                    self.assertTrue((ROOT / link.split('#')[0]).is_file(), link)

    def test_source_and_qualification_limits_remain_explicit(self):
        self.assertIn('Controlling-source status: NOT_RETRIEVED', self.docs['SOURCE_REGISTER.md'])
        self.assertIn('Current validity is unverified', self.docs['SOURCE_REGISTER.md'])
        self.assertIn('NOT_EVIDENCED_IN_THIS_WORK_UNIT', self.docs['PRIME_EVIDENCE.md'])
        self.assertIn('PENDING_CONTROLLING_RECORD', self.docs['PRIME_EVIDENCE.md'])
        self.assertIn('not the RFP itself'.lower(), self.docs['SOURCE_REGISTER.md'].lower())

    def test_all_inspected_source_blob_bindings_retained(self):
        for blob in ('d03e6f0a51831bf8e6cb15226075d128bb4ab681',
                     'c8d5c8edf2f49fd92c9071ddb3ca7811a564e718',
                     'a4c3d91c8c8d287a697158e409e06c38d21a7aa6',
                     '1da7064cf5b5082ec7174686d0e934e3563ad56b'):
            self.assertIn(blob, self.docs['SOURCE_REGISTER.md'])

if __name__ == '__main__':
    unittest.main()
```
