"""Caption handoffs against the real sibling Hive004 consumer, never a mock."""
from __future__ import annotations

import copy
import hashlib
import http.client
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile

import caption_intake as intake

HERE = Path(__file__).resolve().parent
CONSUMER_PATH = HERE.parent / 'podcast-content-workspace' / 'app.py'


def load_consumer():
    if not CONSUMER_PATH.is_file():
        raise RuntimeError('Canonical podcast-content-workspace/app.py is required for this integration suite')
    spec = importlib.util.spec_from_file_location('caption_consumer_runtime', CONSUMER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def captions(count=6, payload='A source sentence.', speaker='Narrator'):
    blocks = ['WEBVTT\n']
    for i in range(count):
        start, end = i * 1000, (i + 1) * 1000
        def stamp(ms):
            return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}'
        blocks.append(f'cue-{i}\n{stamp(start)} --> {stamp(end)}\n<v {speaker}>{payload}</v>\n')
    return ('\n'.join(blocks)).encode('utf-8')


class ConsumerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_consumer()
        data = CONSUMER_PATH.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        print(f'Consumer source: {CONSUMER_PATH}; git_blob={blob}; sha256={hashlib.sha256(data).hexdigest()}', flush=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.app.Store(self.root / 'actual.sqlite3')

    def document(self, source=None, title='Fictional caption integration', duration='65'):
        source = source if source is not None else (HERE / 'examples' / 'demo.vtt').read_bytes()
        parsed = intake.parse_captions(source, fmt='vtt', title=title)
        doc = intake.canonical_episode(parsed, duration, synthetic_demo=True)
        return source, parsed, doc

    def run_cli(self, *args):
        run = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_real_converter_cli_to_canonical_cli_and_sqlite(self):
        bundle = self.root / 'intake.zip'
        receipt = self.run_cli(HERE / 'caption_intake.py', HERE / 'examples' / 'demo.vtt',
                               '--title', 'Fictional caption integration', '--duration-seconds', '65',
                               '--synthetic-demo', '--output', bundle)
        with zipfile.ZipFile(bundle) as archive:
            original = archive.read('source.vtt')
            self.assertEqual(original, (HERE / 'examples' / 'demo.vtt').read_bytes())
            doc_bytes = archive.read('episode-import.json')
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(hashlib.sha256(doc_bytes).hexdigest(), manifest['files']['episode-import.json']['sha256'])
        self.assertEqual(receipt['source_sha256'], hashlib.sha256(original).hexdigest())
        doc_path = self.root / 'episode-import.json'
        doc_path.write_bytes(doc_bytes)
        created = self.run_cli(CONSUMER_PATH, '--db', self.store.path, '--import-document', doc_path)
        persisted = self.app.Store(self.store.path).get(created['id'])
        self.assertEqual(persisted['document'], json.loads(doc_bytes))
        self.assertEqual(persisted['revision'], 1)
        self.assertEqual(len(persisted['document']['segments']), 6)
        self.assertTrue(all(s['verified'] is False for s in persisted['document']['segments']))

    def test_real_http_import_generate_and_editable_export(self):
        source, parsed, doc = self.document()
        with zipfile.ZipFile(io.BytesIO(intake.create_bundle(source, parsed, duration_seconds='65', synthetic_demo=True))) as handoff:
            payload = handoff.read('episode-import.json')
        server = self.app.Server(('127.0.0.1', 0), self.store)
        worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        worker.start()
        def stop():
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
        self.addCleanup(stop)
        def request(method, path, body=None):
            client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            try:
                client.request(method, path, body=body, headers={'Content-Type': 'application/json'})
                response = client.getresponse()
                return response.status, response.read()
            finally:
                client.close()
        status, body = request('POST', '/api/episodes', payload)
        self.assertEqual(status, 201, body)
        episode = json.loads(body)
        self.assertEqual(episode['document'], doc)
        path = '/api/episodes/' + episode['id']
        status, body = request('POST', path + '/generate', intake.json_bytes({'revision': episode['revision']}))
        self.assertEqual(status, 200, body)
        generated = json.loads(body)
        self.assertEqual(len(set(generated['drafts']['posts'])), 5)
        status, exported = request('GET', path + '/export')
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(exported)) as archive:
            self.assertEqual(json.loads(archive.read('transcript.json')), doc)
            source_map = json.loads(archive.read('source-map.json'))
            ids = [sid for group in source_map['current_source_groups'].values() for sid in group]
            self.assertEqual(ids, [s['id'] for s in doc['segments']])
            for i in range(5):
                self.assertEqual(archive.read(f'posts/post-{i+1:02}.md').decode(), generated['drafts']['posts'][i])
            for key, name in [('show_notes', 'show-notes.md'), ('newsletter', 'newsletter.md')]:
                self.assertEqual(archive.read(name).decode(), generated['drafts'][key])
            self.assertFalse(source_map['drafts_stale'])
            self.assertTrue(source_map['synthetic_demo'])
        self.assertEqual(source, (HERE / 'examples' / 'demo.vtt').read_bytes())

    def test_unicode_and_escaped_literals_survive_consumer_export(self):
        source, parsed, doc = self.document(captions(payload='保存 &lt;literal&gt; &amp; café — مرحبا', speaker='李 &amp; Zoë'))
        episode = self.store.create(doc)
        self.store.make_drafts(episode['id'], episode['revision'])
        with zipfile.ZipFile(io.BytesIO(self.store.export(episode['id']))) as archive:
            exported = json.loads(archive.read('transcript.json'))
            for segment in exported['segments']:
                self.assertEqual(segment['text'], '保存 <literal> & café — مرحبا')
                self.assertEqual(segment['speaker'], '李 & Zoë')
                self.assertFalse(segment['verified'])
            self.assertIn('保存 &lt;literal&gt; &amp; café', archive.read('show-notes.md').decode())
        self.assertEqual(parsed['provenance']['source_sha256'], hashlib.sha256(source).hexdigest())

    def test_adapter_accepts_actual_schema_boundaries(self):
        cases = [
            (captions(), 'T' * 200, '65'),
            (captions(speaker='S' * 120), 'Speaker edge', '65'),
            (captions(payload='X' * 12000), 'Text edge', '65'),
            (captions(count=2000), 'Cue edge', '2000'),
        ]
        for source, title, duration in cases:
            with self.subTest(title=title[:20]):
                _, _, doc = self.document(source, title, duration)
                persisted = self.store.create(doc)
                self.assertEqual(persisted['document'], doc)

    def test_adapter_rejects_consumer_limits_without_narrowing_generic_intake(self):
        cases = [
            (captions(), 'T' * 201, '65', 'title'),
            (captions(speaker='S' * 121), 'Speaker edge', '65', 'speaker'),
            (captions(payload='X' * 12001), 'Text edge', '65', 'text'),
            (captions(count=2001), 'Cue edge', '2001', '2000'),
        ]
        for source, title, duration, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                parsed = intake.parse_captions(source, fmt='vtt', title=title)
                before = copy.deepcopy(parsed)
                with self.assertRaisesRegex(intake.IntakeError, diagnostic):
                    intake.canonical_episode(parsed, duration)
                self.assertEqual(parsed, before)
                with zipfile.ZipFile(io.BytesIO(intake.create_bundle(source, parsed))) as archive:
                    self.assertEqual(archive.read('source.vtt'), source)
                    self.assertEqual(json.loads(archive.read('transcript.json')), parsed)

    def test_large_valid_document_keeps_canonical_cli_route(self):
        # Raw captions fit the generic source bound, but JSON escaping exceeds HTTP's body bound.
        source = captions(count=900, payload='"' * 1900)
        self.assertLess(len(source), intake.MAX_BYTES)
        _, parsed, doc = self.document(source, duration='900')
        document_bytes = intake.json_bytes(doc)
        self.assertGreater(len(document_bytes), self.app.MAX_JSON)
        doc_path = self.root / 'large-import.json'
        doc_path.write_bytes(document_bytes)
        created = self.run_cli(CONSUMER_PATH, '--db', self.store.path, '--import-document', doc_path)
        self.assertEqual(self.store.get(created['id'])['document'], doc)
        self.assertEqual(parsed['provenance']['source_bytes'], len(source))

    def test_short_srt_imports_but_does_not_claim_five_post_workflow(self):
        source = (HERE / 'examples' / 'demo.srt').read_bytes()
        parsed = intake.parse_captions(source, fmt='srt', title='Fictional short captions')
        doc = intake.canonical_episode(parsed, '20', synthetic_demo=True)
        episode = self.store.create(doc)
        self.assertEqual(episode['document'], doc)
        with self.assertRaisesRegex(self.app.Invalid, 'at least five'):
            self.store.make_drafts(episode['id'], episode['revision'])
        self.assertIsNone(self.store.get(episode['id'])['drafts'])


if __name__ == '__main__':
    unittest.main()
