"""Type/shape regression cases for the existing Tennessee response lab.

All inputs are disposable copies of the retained synthetic/internal packet.
The tests never authorize contact, submit a response, or mutate source evidence.
"""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from revenue.opportunities.tn_31701_03850_cashiering.response_lab import validator as v

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'revenue/opportunities/tn_31701_03850_cashiering/response_lab'


class ValidationTypes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'response_manifest.json'
        self.crosswalk = self.path.with_name('requirement_crosswalk.csv')
        self.doc = json.loads((LAB / 'response_manifest.json').read_text(encoding='utf-8'))
        self.raw = (LAB / 'requirement_crosswalk.csv').read_bytes()
        self.crosswalk.write_bytes(self.raw)

    def write(self, doc=None):
        self.path.write_text(json.dumps(self.doc if doc is None else doc), encoding='utf-8')
        return self.path

    def reject(self, key_path, value):
        doc = copy.deepcopy(self.doc)
        target = doc
        for key in key_path[:-1]:
            target = target[key]
        target[key_path[-1]] = value
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write(doc))

    def csv_rows(self):
        return list(csv.reader(io.StringIO(self.raw.decode('utf-8'), newline='')))

    def write_rows(self, rows):
        stream = io.StringIO(newline='')
        csv.writer(stream, lineterminator='\n').writerows(rows)
        raw = stream.getvalue().encode('utf-8')
        self.crosswalk.write_bytes(raw)
        self.doc['crosswalk']['sha256'] = hashlib.sha256(raw).hexdigest()
        return self.write()

    def test_original_packet_output_and_bytes_unchanged(self):
        before = {p.name: p.read_bytes() for p in LAB.iterdir() if p.is_file()}
        output = v.validate(self.write())
        self.assertEqual(output, {
            'requirements': 120, 'required': 112, 'optional': 8,
            'postures': {'DEMO_SUPPORTED': 12, 'GAP_QUESTION': 4,
                         'PRIME_PRODUCT_EVIDENCE': 51, 'SPECIALIST_WORKSHARE': 53},
            'authority': v.FALSE_AUTH,
        })
        self.assertTrue(all(value is False for value in output['authority'].values()))
        self.assertEqual(before, {p.name: p.read_bytes() for p in LAB.iterdir() if p.is_file()})

    def test_each_authority_flag_rejects_numeric_false(self):
        for field in v.FALSE_AUTH:
            for value in (0, 0.0):
                with self.subTest(field=field, value=repr(value)):
                    self.reject(('authority', field), value)

    def test_each_authority_flag_rejects_other_values(self):
        for field in v.FALSE_AUTH:
            for value in (True, None, '', [], {}):
                with self.subTest(field=field, value=repr(value)):
                    self.reject(('authority', field), value)

    def test_integer_fields_reject_equal_floats(self):
        for key_path, value in [
            (('response_page_limit',), 20.0),
            (('minimum_font_points',), 12.0),
            (('question_submissions_per_vendor',), 1.0),
            (('crosswalk', 'row_count'), 120.0),
            (('commercial', 'fixed_price_usd'), 25000.0),
        ]:
            with self.subTest(path=key_path):
                self.reject(key_path, value)

    def test_integer_fields_reject_booleans(self):
        for key_path in [('response_page_limit',), ('minimum_font_points',),
                         ('question_submissions_per_vendor',), ('crosswalk', 'row_count'),
                         ('commercial', 'fixed_price_usd')]:
            for value in (True, False):
                with self.subTest(path=key_path, value=value):
                    self.reject(key_path, value)

    def test_integer_fields_reject_strings_and_null(self):
        for key_path, value in [(('response_page_limit',), '20'),
                                (('minimum_font_points',), None),
                                (('question_submissions_per_vendor',), '1'),
                                (('crosswalk', 'row_count'), '120'),
                                (('commercial', 'fixed_price_usd'), '25000')]:
            with self.subTest(path=key_path):
                self.reject(key_path, value)

    def test_external_landing_page_flag_requires_boolean_false(self):
        for value in (0, 0.0, True, None, 'false', []):
            with self.subTest(value=repr(value)):
                self.reject(('embedded_external_landing_pages_allowed',), value)

    def test_text_metadata_requires_nonempty_strings(self):
        for key in ('title', 'buyer', 'issued', 'state_answers'):
            for value in (None, [], {}, 0, True, '', '  '):
                with self.subTest(key=key, value=repr(value)):
                    self.reject((key,), value)

    def test_nonstring_source_url_is_a_contract_error(self):
        for value in (None, 1, False, [], {}):
            with self.subTest(value=repr(value)):
                self.reject(('source_url',), value)

    def test_crosswalk_metadata_must_have_exact_keys(self):
        for value in (None, [], {}, {**self.doc['crosswalk'], 'extra': 1}):
            with self.subTest(value=repr(value)):
                self.reject(('crosswalk',), value)

    def test_commercial_metadata_must_have_exact_keys(self):
        for value in (None, [], {}, {**self.doc['commercial'], 'accepted': True}):
            with self.subTest(value=repr(value)):
                self.reject(('commercial',), value)

    def test_authority_metadata_must_have_exact_keys(self):
        for value in (None, [], {}, {**self.doc['authority'], 'extra': False}):
            with self.subTest(value=repr(value)):
                self.reject(('authority',), value)

    def test_duplicate_csv_header_is_rejected_even_with_matching_hash(self):
        rows = self.csv_rows()
        rows[0].append('summary')
        for row in rows[1:]:
            row.append(row[3])
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write_rows(rows))

    def test_csv_missing_header_is_rejected(self):
        rows = [row[:-1] for row in self.csv_rows()]
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write_rows(rows))

    def test_csv_unknown_header_is_rejected(self):
        rows = self.csv_rows()
        rows[0][3] = 'unknown'
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write_rows(rows))

    def test_csv_extra_cell_after_first_row_is_rejected(self):
        rows = self.csv_rows()
        rows[2].append('unmapped evidence')
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write_rows(rows))

    def test_csv_missing_cell_after_first_row_is_rejected(self):
        rows = self.csv_rows()
        rows[2] = rows[2][:-1]
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write_rows(rows))

    def test_csv_header_order_remains_supported(self):
        rows = self.csv_rows()
        order = [3, 0, 4, 2, 1]
        result = v.validate(self.write_rows([[row[i] for i in order] for row in rows]))
        self.assertEqual(result['requirements'], 120)

    def test_quoted_multiline_summary_is_preserved(self):
        rows = self.csv_rows()
        rows[1][3] = 'First evidence line\nSecond evidence line, with comma'
        self.write_rows(rows)
        self.assertEqual(v.load_rows(self.crosswalk)[0]['summary'], rows[1][3])
        self.assertEqual(v.validate(self.path)['requirements'], 120)

    def test_csv_blank_rows_and_crlf_remain_supported(self):
        raw = self.raw.replace(b'\n', b'\r\n') + b'\r\n'
        self.crosswalk.write_bytes(raw)
        self.doc['crosswalk']['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(v.validate(self.write())['requirements'], 120)

    def test_unclosed_csv_quote_is_a_contract_error(self):
        self.crosswalk.write_text('id,domain,required,summary,posture\n1,D,Y,"never closed', encoding='utf-8')
        with self.assertRaises(v.ResponseLabError):
            v.load_rows(self.crosswalk)

    def test_empty_and_header_only_csv_are_contract_errors(self):
        for raw in (b'', b'id,domain,required,summary,posture\n'):
            with self.subTest(raw=raw):
                self.crosswalk.write_bytes(raw)
                with self.assertRaises(v.ResponseLabError):
                    v.load_rows(self.crosswalk)

    def test_invalid_utf8_csv_is_a_contract_error(self):
        self.crosswalk.write_bytes(b'\xff')
        with self.assertRaises(v.ResponseLabError):
            v.load_rows(self.crosswalk)

    def test_missing_crosswalk_is_a_contract_error(self):
        self.crosswalk.unlink()
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write())

    def test_malformed_json_is_a_contract_error(self):
        self.path.write_text('{"schema":', encoding='utf-8')
        with self.assertRaises(v.ResponseLabError):
            v.load_json(self.path)

    def test_invalid_utf8_json_is_a_contract_error(self):
        self.path.write_bytes(b'\xff')
        with self.assertRaises(v.ResponseLabError):
            v.load_json(self.path)

    def test_missing_manifest_is_a_contract_error(self):
        with self.assertRaises(v.ResponseLabError):
            v.load_json(self.path)

    def test_nonfinite_json_and_duplicate_keys_remain_rejected(self):
        for raw in ('{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{"a":1,"a":2}'):
            with self.subTest(raw=raw):
                self.path.write_text(raw, encoding='utf-8')
                with self.assertRaises(v.ResponseLabError):
                    v.load_json(self.path)

    def test_validation_parses_the_same_crosswalk_read_it_hashes(self):
        self.write()
        original_open = Path.open
        opens = []

        def observed_open(path, *args, **kwargs):
            if path == self.crosswalk:
                opens.append(path)
            return original_open(path, *args, **kwargs)

        with mock.patch.object(Path, 'open', observed_open):
            self.assertEqual(v.validate(self.path)['requirements'], 120)
        self.assertEqual(len(opens), 1)

    def test_hash_mismatch_remains_rejected(self):
        self.crosswalk.write_bytes(self.raw + b'\n')
        with self.assertRaises(v.ResponseLabError):
            v.validate(self.write())

    def test_cli_good_packet_is_json_and_bad_packet_exits_nonzero(self):
        self.write()
        command = [sys.executable]
        if sys.flags.optimize:
            command.append('-O')
        command.append(str(LAB / 'validator.py'))
        good = subprocess.run(command + [str(self.path)], capture_output=True, text=True, timeout=10)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['requirements'], 120)
        self.doc['question_submissions_per_vendor'] = True
        bad = subprocess.run(command + [str(self.write())], capture_output=True, text=True, timeout=10)
        self.assertNotEqual(bad.returncode, 0)
        self.assertEqual(bad.stdout, '')


if __name__ == '__main__':
    unittest.main()
