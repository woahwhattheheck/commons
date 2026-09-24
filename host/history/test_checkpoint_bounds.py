"""Publisher-sized GitHub history checkpoints keep every queued URL."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import github_cloud


def document(count, nxt=None):
    details = []
    keys = []
    for index in range(count):
        url = 'https://api.github.com/repos/woahwhattheheck/commons-ship-enforcer/issues/%d/comments' % index
        url += '/' + ('a' * 48)
        keys.append(url)
        details.append({'url': url, 'kind': 'issue', 'next': nxt or url})
    return {
        'schema': 'github-history-checkpoint-v1', 'account': 'woahwhattheheck', 'roads': {},
        'details': details, 'detail_keys': keys, 'repositories': [], 'repository_keys': [], 'gaps': []}


class CheckpointBoundsTest(unittest.TestCase):
    def test_expanded_checkpoint_compacts_under_ceiling_and_roundtrips(self):
        raw = github_cloud.dumps(document(1500))
        self.assertGreater(len(raw), 250_000)
        planned = github_cloud.plan_checkpoint_files(raw)
        self.assertEqual([name for name, _ in planned], ['checkpoint.json'])
        compact = planned[0][1]
        self.assertLessEqual(len(compact), github_cloud.MAX_CHECKPOINT_BYTES)
        self.assertLess(len(compact), len(raw) / 2)
        self.assertNotIn(b'detail_keys', compact)
        expanded, prior = github_cloud.expand_checkpoint(compact, lambda name: self.fail(name))
        self.assertEqual(prior, {})
        restored = json.loads(expanded)
        self.assertEqual(restored['detail_keys'], [row['url'] for row in restored['details']])
        self.assertEqual(restored['detail_keys'], document(1500)['detail_keys'])
        self.assertTrue(all(row['next'] == row['url'] and row['kind'] == 'issue' for row in restored['details']))
        again = github_cloud.plan_checkpoint_files(expanded)
        self.assertEqual(again, planned)

    def test_over_ceiling_compact_form_shards_without_dropping_urls(self):
        raw = github_cloud.dumps(document(7000))
        planned = github_cloud.plan_checkpoint_files(raw)
        names = [name for name, blob in planned]
        self.assertGreater(len(names), 2)
        self.assertEqual(names[-1], 'checkpoint.json')
        for name, blob in planned:
            self.assertLessEqual(len(blob), github_cloud.MAX_CHECKPOINT_BYTES)
            self.assertTrue(name.endswith('.json'))
        shards = dict(planned[:-1])
        expanded, prior = github_cloud.expand_checkpoint(planned[-1][1], lambda name: (shards[name], 'sha'))
        self.assertEqual(set(prior), set(shards))
        restored = json.loads(expanded)
        self.assertEqual(restored['detail_keys'], document(7000)['detail_keys'])
        self.assertNotIn('detail_shards', restored)

    def test_distinct_next_is_not_rewritten(self):
        raw = github_cloud.dumps(document(2, nxt='https://api.github.com/repos/woahwhattheheck/commons/issues/1'))
        planned = github_cloud.plan_checkpoint_files(raw)
        self.assertEqual(planned, [('checkpoint.json', raw)])

    def test_uncompactable_over_ceiling_is_refused(self):
        body = document(1)
        body['details'][0]['next'] = body['details'][0]['url'] + '/other'
        body['note'] = 'x' * (github_cloud.MAX_CHECKPOINT_BYTES + 1)
        raw = github_cloud.dumps(body)
        with self.assertRaises(RuntimeError) as caught:
            github_cloud.plan_checkpoint_files(raw)
        self.assertEqual(str(caught.exception), 'checkpoint_over_publisher_ceiling')


if __name__ == '__main__':
    unittest.main()
