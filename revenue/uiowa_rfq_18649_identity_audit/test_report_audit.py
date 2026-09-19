"""Independent golden-output and resealed-corruption controls; no mapper import."""
from collections import Counter
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('uiowa103_conservation_audit', ROOT / 'report_audit.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def original():
    return json.loads((ROOT / 'fixtures/synthetic_packet.json').read_text(encoding='utf-8'))


def report():
    return json.loads((ROOT / 'fixtures/canonical_report.json').read_text(encoding='utf-8'))


def seal(value):
    value['snapshot_sha256'] = AUDIT.fingerprint({k: v for k, v in value.items() if k != 'snapshot_sha256'}, AUDIT.SCHEMA + '/report')
    return value


def set_at(value, path, replacement):
    parent = value
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = replacement


class ConservationTests(unittest.TestCase):
    def test_exact_published_producer_report(self):
        result = AUDIT.audit(original(), report())
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['diagnostics'], [])
        self.assertEqual(result['expected_counts'], {'input_records': 8, 'occurrences': 7, 'collisions': 1, 'links': 5, 'unresolved_links': 2})
        self.assertEqual(result, json.loads((ROOT / 'fixtures/audit_result.json').read_text(encoding='utf-8')))

    def test_pass_means_faithful_not_all_links_resolved(self):
        self.assertEqual(report()['summary']['unresolved_links'], 2)
        self.assertEqual(AUDIT.audit(original(), report())['status'], 'PASS')
        self.assertFalse(AUDIT.audit(original(), report())['assessment_authority'])

    def test_does_not_mutate_inputs(self):
        source, output = original(), report()
        before = deepcopy((source, output))
        AUDIT.audit(source, output)
        self.assertEqual((source, output), before)

    def test_input_order_not_conservation_failure(self):
        source = original()
        source['records'].reverse()
        source['links'].reverse()
        self.assertEqual(AUDIT.audit(source, report())['status'], 'PASS')

    def test_report_order_not_conservation_failure(self):
        output = report()
        output['records'].reverse()
        output['links'].reverse()
        self.assertEqual(AUDIT.audit(original(), seal(output))['status'], 'PASS')

    def test_duplicate_count_counts_first_occurrence(self):
        rows = report()['records']
        self.assertEqual(sum(row['duplicate_count'] for row in rows), 8)
        self.assertEqual(Counter(row['duplicate_count'] for row in rows), {1: 6, 2: 1})

    def test_missing_snapshot_diagnosed(self):
        output = report()
        output.pop('snapshot_sha256')
        result = AUDIT.audit(original(), output)
        self.assertIn('snapshot_digest', {row['code'] for row in result['diagnostics']})

    def test_reports_do_not_echo_changed_evidence_values(self):
        output = report()
        output['records'][0]['original']['private_future_field'] = 'UNIQUE_PRIVATE_SENTINEL'
        result = AUDIT.audit(original(), seal(output))
        self.assertNotIn('UNIQUE_PRIVATE_SENTINEL', json.dumps(result))
        self.assertEqual(result['status'], 'FAIL')

    def test_diagnostics_are_deterministic(self):
        output = report()
        output['records'].pop()
        output['links'].pop()
        first = AUDIT.audit(original(), seal(output))
        self.assertEqual(first, AUDIT.audit(original(), output))


# Each report mutation is RESEALED to prove checks do more than trust a hash.
MUTATIONS = [
    ('dropped_record', lambda r: r['records'].pop(), 'record_conservation'),
    ('duplicated_wrapper', lambda r: r['records'].append(deepcopy(r['records'][0])), 'duplicate_output_occurrence'),
    ('dropped_payload_extension', lambda r: r['records'][0]['original']['payload'].pop('null_value'), 'record_conservation'),
    ('null_to_empty', lambda r: set_at(r, ['records', 0, 'original', 'payload', 'null_value'], ''), 'record_conservation'),
    ('bool_to_integer', lambda r: set_at(r, ['records', 0, 'original', 'payload', 'flags', 0], 0), 'record_conservation'),
    ('integer_to_float', lambda r: set_at(r, ['records', 0, 'original', 'payload', 'flags', 1], 0.0), 'record_conservation'),
    ('synthetic_changed', lambda r: set_at(r, ['records', 0, 'original', 'synthetic'], False), 'record_conservation'),
    ('source_locator_changed', lambda r: r['records'][0]['original']['source_locators'].append('synthetic://invented'), 'record_conservation'),
    ('unknown_record_extension', lambda r: r['records'][0]['original'].pop('extension'), 'record_conservation'),
    ('duplicate_count_changed', lambda r: set_at(r, ['records', 0, 'duplicate_count'], 4), 'duplicate_count'),
    ('boolean_duplicate_count', lambda r: set_at(r, ['records', 0, 'duplicate_count'], True), 'duplicate_count_type'),
    ('unknown_occurrence_id', lambda r: set_at(r, ['records', 0, 'occurrence_id'], 'occ-invented'), 'occurrence_id'),
    ('unknown_entity_id', lambda r: set_at(r, ['records', 0, 'entity_id'], 'ent-invented'), 'entity_id'),
    ('missing_original', lambda r: r['records'][0].pop('original'), 'record_original_shape'),
    ('invalid_original_identity', lambda r: r['records'][0]['original'].pop('revision'), 'record_identity_shape'),
    ('dropped_link', lambda r: r['links'].pop(), 'link_conservation'),
    ('duplicated_link', lambda r: r['links'].append(deepcopy(r['links'][0])), 'duplicate_output_link'),
    ('renamed_link', lambda r: set_at(r, ['links', 0, 'link_id'], 'other'), 'link_inventory'),
    ('link_extension_changed', lambda r: set_at(r, ['links', 0, 'original', 'extension', 'follow_up'], []), 'link_conservation'),
    ('dropped_decision', lambda r: r['equivalences'].clear(), 'decision_conservation'),
    ('decision_extension_changed', lambda r: r['equivalences'][0].pop('extension'), 'decision_conservation'),
    ('dropped_envelope_extension', lambda r: r['extensions'].pop('envelope_extension'), 'envelope_extensions'),
    ('guessed_ambiguous_target', lambda r: set_at(r, ['links', 3, 'to', 'status'], 'resolved'), 'resolution_status'),
    ('falsely_resolved_link', lambda r: set_at(r, ['links', 3, 'status'], 'resolved'), 'link_status'),
    ('lost_candidate', lambda r: r['links'][3]['to']['candidate_ids'].pop(), 'candidate_inventory'),
    ('extra_candidate', lambda r: r['links'][0]['to']['candidate_ids'].append('occ-nonexistent'), 'candidate_inventory'),
    ('repeated_candidate', lambda r: r['links'][0]['to']['candidate_ids'].extend(r['links'][0]['to']['candidate_ids'][:]), 'candidate_inventory'),
    ('lost_resolved_target', lambda r: set_at(r, ['links', 0, 'to', 'resolved_id'], None), 'resolved_target'),
    ('selector_silently_changed', lambda r: set_at(r, ['links', 0, 'to', 'selector', 'revision'], 'v2'), 'selector_changed'),
    ('missing_resolution_object', lambda r: set_at(r, ['links', 0, 'from'], None), 'resolution_shape'),
    ('missing_group', lambda r: r['equivalence_groups'].pop(), 'group_inventory'),
    ('unknown_group_member', lambda r: r['equivalence_groups'][0]['members'].append('occ-unknown'), 'group_unknown_member'),
    ('repeated_group_member', lambda r: r['equivalence_groups'][0]['members'].extend(r['equivalence_groups'][0]['members'][:]), 'group_membership_count'),
    ('record_group_changed', lambda r: set_at(r, ['records', 0, 'equivalence_group'], 'eq-unknown'), 'record_group'),
    ('resolution_groups_lost', lambda r: set_at(r, ['links', 0, 'to', 'equivalence_groups'], []), 'resolution_group_inventory'),
    ('collisions_silently_dropped', lambda r: r['collisions'].clear(), 'collision_inventory'),
    ('unresolved_count_zero', lambda r: set_at(r, ['summary', 'unresolved_links'], 0), 'summary_count'),
    ('input_duplicate_count_hidden', lambda r: set_at(r, ['summary', 'input_records'], 7), 'summary_count'),
    ('summary_boolean', lambda r: set_at(r, ['summary', 'collisions'], True), 'summary_count'),
    ('authority_promoted', lambda r: set_at(r, ['assessment_authority'], True), 'authority_changed'),
    ('schema_changed', lambda r: set_at(r, ['schema'], 'other'), 'schema'),
    ('report_records_wrong_shape', lambda r: set_at(r, ['records'], {}), 'report_shape'),
    ('report_summary_wrong_shape', lambda r: set_at(r, ['summary'], []), 'summary_shape'),
]


def make_mutation_test(mutate, code):
    def test(self):
        output = report()
        mutate(output)
        result = AUDIT.audit(original(), seal(output))
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn(code, {row['code'] for row in result['diagnostics']})
        self.assertNotIn('snapshot_digest', {row['code'] for row in result['diagnostics']})
    return test


for name, mutate, code in MUTATIONS:
    setattr(ConservationTests, 'test_resealed_' + name, make_mutation_test(mutate, code))


class InputAndCLITests(unittest.TestCase):
    def invoke(self, source, output, *extra):
        return subprocess.run([sys.executable, str(ROOT / 'report_audit.py'), str(source), str(output), *map(str, extra)],
                              capture_output=True, text=True, timeout=8)

    def test_rejects_conflicting_source_duplicates(self):
        source = original()
        source['records'][-1]['payload']['note'] = 'conflict'
        with self.assertRaises(AUDIT.AuditInputError):
            AUDIT.audit(source, report())

    def test_rejects_malformed_source_records(self):
        for field, value in [('id', 7), ('synthetic', 'true'), ('payload', []), ('source_locators', [])]:
            with self.subTest(field=field):
                source = original()
                source['records'][0][field] = value
                with self.assertRaises(AUDIT.AuditInputError):
                    AUDIT.audit(source, report())

    def test_rejects_python_only_values(self):
        for value in [float('nan'), float('inf'), (1, 2), {1: 'not-a-string-key'}, '\ud800']:
            with self.subTest(value=repr(value)):
                source = original()
                source['extra'] = value
                with self.assertRaises(AUDIT.AuditInputError):
                    AUDIT.audit(source, report())

    def test_rejects_recursive_api_inputs(self):
        source = original()
        source['cycle'] = source
        with self.assertRaises(AUDIT.AuditInputError):
            AUDIT.audit(source, report())

    def test_rejects_duplicate_link_ids(self):
        source = original()
        source['links'].append(deepcopy(source['links'][0]))
        with self.assertRaises(AUDIT.AuditInputError):
            AUDIT.audit(source, report())

    def test_cli_pass_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'input.json', Path(tmp)/'report.json'
            source.write_text(json.dumps(original()), encoding='utf-8')
            output.write_text(json.dumps(report()), encoding='utf-8')
            done = self.invoke(source, output)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)['status'], 'PASS')
            bad = report(); bad['links'].pop()
            output.write_text(json.dumps(seal(bad)), encoding='utf-8')
            done = self.invoke(source, output)
            self.assertEqual(done.returncode, 1)
            self.assertEqual(json.loads(done.stdout)['status'], 'FAIL')

    def test_cli_invalid_inputs_clean_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'input.json', Path(tmp)/'report.json'
            output.write_text(json.dumps(report()), encoding='utf-8')
            for raw in [b'{"schema":1,"schema":2}', b'{"x":NaN}', b'\xff', ('['*1200+'0'+']'*1200).encode(), b'null']:
                with self.subTest(raw=raw[:30]):
                    source.write_bytes(raw)
                    done = self.invoke(source, output)
                    self.assertEqual(done.returncode, 2, done.stderr)
                    self.assertNotIn('Traceback', done.stderr)
                    self.assertEqual(done.stdout, '')

    def test_cli_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output, destination = (Path(tmp)/n for n in ['input.json', 'report.json', 'audit.json'])
            source.write_text(json.dumps(original()), encoding='utf-8')
            output.write_text(json.dumps(report()), encoding='utf-8')
            destination.write_bytes(b'EXISTING EVIDENCE')
            done = self.invoke(source, output, '--output', destination)
            self.assertEqual(done.returncode, 2)
            self.assertEqual(destination.read_bytes(), b'EXISTING EVIDENCE')

    def test_cli_hardlinked_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output, alias = (Path(tmp)/n for n in ['input.json', 'report.json', 'alias.json'])
            source.write_text(json.dumps(original()), encoding='utf-8')
            output.write_text(json.dumps(report()), encoding='utf-8')
            before = source.read_bytes()
            os.link(source, alias)
            done = self.invoke(source, output, '--output', alias)
            self.assertEqual(done.returncode, 2)
            self.assertEqual(source.read_bytes(), before)

    def test_cli_missing_report_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'input.json'; destination=Path(tmp)/'audit.json'
            source.write_text(json.dumps(original()), encoding='utf-8')
            done = self.invoke(source, Path(tmp)/'absent.json', '--output', destination)
            self.assertEqual(done.returncode, 2)
            self.assertFalse(destination.exists())

    def test_byte_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'json'; path.write_text('{"value": 12}', encoding='utf-8')
            with patch.object(AUDIT, 'MAX_BYTES', 5), self.assertRaises(AUDIT.AuditInputError):
                AUDIT.load(path)


if __name__ == '__main__':
    unittest.main()
