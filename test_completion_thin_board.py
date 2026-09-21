"""Real thin-renderer regression; does not replace full board integration tests."""
from __future__ import annotations
import ast
import importlib.util
import copy
import tempfile
from pathlib import Path
import unittest

import chunk_board
import completion_projection

ROOT = Path(__file__).resolve().parent
PROBE = ROOT / 'reviews/completion_thin_board_thalweg_20260919/probe_thin_board.py'
spec = importlib.util.spec_from_file_location('thin_board_review_fixture', PROBE)
if spec is None or spec.loader is None:
    raise RuntimeError('review fixture unavailable')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class CurrentThinBoardTests(unittest.TestCase):
    def run_case(self, name):
        result = fixture.case(chunk_board, completion_projection, name, current_writer=True)
        self.assertTrue(result['projection_agrees'], result)
        self.assertTrue(result['history_and_input_unchanged'])
        self.assertTrue(result['real_git_ancestry'])
        return result

    def test_verified_completion_is_absent_from_actual_html_and_chunks(self):
        result = self.run_case('verified_completion')
        self.assertEqual([fixture.OPEN], result['actual_chunk_ids'])
        self.assertFalse(result['completed_body_in_html'])

    def test_reopen_ignores_stale_completed_flag(self):
        result = self.run_case('reopened_stale_history_flag')
        self.assertIn(fixture.DONE, result['actual_chunk_ids'])
        self.assertTrue(result['completed_body_in_html'])

    def test_source_drift_restores_live_work(self):
        self.assertIn(fixture.DONE, self.run_case('source_drift')['actual_chunk_ids'])

    def test_nonancestor_marker_does_not_suppress_work(self):
        self.assertIn(fixture.DONE, self.run_case('nonancestor_marker')['actual_chunk_ids'])

    def test_other_route_is_preserved(self):
        self.assertIn(fixture.DONE, self.run_case('other_route')['actual_chunk_ids'])

    def test_named_sender_is_preserved(self):
        self.assertIn(fixture.DONE, self.run_case('named_sender')['actual_chunk_ids'])

    def test_moderation_remains_separate_and_hidden(self):
        result = self.run_case('moderated_completed')
        self.assertEqual([fixture.OPEN], result['actual_chunk_ids'])
        self.assertFalse(result['completed_body_in_html'])

    def test_empty_and_idless_rows_keep_the_existing_renderer_contract(self):
        records = [None, {}, {"body": "not an identified card"}]
        before = copy.deepcopy(records)
        with tempfile.TemporaryDirectory(prefix='thalweg-empty-') as directory:
            result = chunk_board.write_current_thin_board(records, directory, fixture.CHROME, lambda sha: False)
            self.assertEqual(0, result['n'])
            self.assertIn('No posts yet.', Path(directory, 'board.html').read_text())
        self.assertEqual(before, records)

    def test_standalone_entry_uses_current_projection_but_archive_keeps_history(self):
        # Structural entrypoint check is additional evidence, not a claim that
        # the full board_ingest dependency closure executed in this suite.
        tree = ast.parse(Path(chunk_board.__file__).read_bytes())
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)]
        projection = [node for node in calls if isinstance(node.func, ast.Name)
                      and node.func.id == 'write_current_thin_board']
        self.assertEqual(1, len(projection))
        self.assertEqual(['feed', 'root', 'chrome'], [node.id for node in projection[0].args[:3]])
        verifier = projection[0].args[3]
        self.assertIsInstance(verifier, ast.Attribute)
        self.assertEqual('_completion_merge_is_ancestor', verifier.attr)
        direct = [node for node in calls if isinstance(node.func, ast.Name) and node.func.id == 'write_thin_board']
        self.assertEqual([], direct)
        archives = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == 'rebuild_archive']
        self.assertEqual(1, len(archives))
        rows = archives[0].args[1]
        self.assertIsInstance(rows, ast.Call)
        self.assertEqual('rows_from_feed', rows.func.id)
        self.assertEqual('feed', rows.args[0].id)


if __name__ == '__main__':
    unittest.main()
