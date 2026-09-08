"""Real parser, filesystem, subprocess, and concurrent publication checks."""
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import caption_intake as intake

VTT = b'WEBVTT\n\nfirst\n00:00.123 --> 00:02.456 align:start\n<v Alex>Keep <b>original</b> sources &amp; context.</v>\n\nsecond\n00:02.000 --> 00:04.005\n<v Jules>Overlaps stay on their original timeline.\n'
SRT = b'1\r\n00:00:00,123 --> 00:00:02,456\r\nKeep <i>original</i> sources.\r\n\r\n2\r\n00:00:02,000 --> 00:00:04,005\r\nAn overlapping response.\r\n'


def parse(source=VTT, fmt='vtt', **kwargs):
    return intake.parse_captions(source, fmt=fmt, title='Original fictional caption example', **kwargs)


class Parsing(unittest.TestCase):
    def test_vtt_voice_exact_timing_settings_and_overlap(self):
        out = parse()
        self.assertEqual(out['segments'][0], {'id': 'c00001', 'start_ms': 123, 'end_ms': 2456,
                         'speaker': 'Alex', 'text': 'Keep original sources & context.'})
        self.assertEqual(out['segments'][1]['start_ms'], 2000)
        self.assertEqual(out['segments'][1]['speaker'], 'Jules')
        self.assertEqual(out['provenance']['cues'][0]['settings'], 'align:start')
        self.assertEqual(out['provenance']['cues'][0]['source_id'], 'first')
        self.assertEqual(out['provenance']['cues'][0]['line'], 3)
        self.assertFalse(out['provenance']['media_verified'])

    def test_srt_preserves_crlf_hash_and_supplied_voice(self):
        out = parse(SRT, 'srt', default_speaker='Caller-provided narrator')
        self.assertEqual(out['segments'][0]['start_ms'], 123)
        self.assertEqual(out['segments'][0]['text'], 'Keep original sources.')
        self.assertEqual(out['segments'][0]['speaker'], 'Caller-provided narrator')
        self.assertEqual(out['provenance']['source_sha256'], hashlib.sha256(SRT).hexdigest())
        self.assertEqual(out['provenance']['source_bytes'], len(SRT))

    def test_utf8_bom_crlf_and_unicode_voice(self):
        source = '\ufeffWEBVTT\r\n\r\n00:01.000 --> 00:02.000\r\n<v 李 &amp; Zoë>保存 原文 — مرحبا\r\n'.encode()
        out = parse(source)
        self.assertEqual(out['segments'][0]['speaker'], '李 & Zoë')
        self.assertEqual(out['segments'][0]['text'], '保存 原文 — مرحبا')

    def test_srt_explicit_utf16_and_cp1252(self):
        source = '1\n00:00:01,000 --> 00:00:02,000\nCafé.'
        for encoding in ('utf-16', 'cp1252'):
            with self.subTest(encoding=encoding):
                self.assertEqual(parse(source.encode(encoding), 'srt', encoding=encoding)['segments'][0]['text'], 'Café.')
        with self.assertRaises(intake.IntakeError):
            parse(source.encode('cp1252'), 'srt')

    def test_metadata_retained_and_not_spoken(self):
        data = b'WEBVTT original fixture\n\nNOTE a production note\nnot speech\n\nSTYLE\n::cue { color: blue; }\n\nREGION\nid:stage\n\n00:00.000 --> 00:01.000 region:stage\nA line.\n\nNOTE after the cue\n'
        out = parse(data)
        self.assertEqual([m['kind'] for m in out['provenance']['metadata']], ['header', 'NOTE', 'STYLE', 'REGION', 'NOTE'])
        self.assertEqual(len(out['segments']), 1)
        self.assertEqual(out['segments'][0]['text'], 'A line.')

    def test_anonymous_equal_start_cues_receive_distinct_ids(self):
        source = b'WEBVTT\n\n00:01.000 --> 00:02.000\nOne\n\n00:01.000 --> 00:03.000\nTwo'
        out = parse(source)
        self.assertEqual([s['id'] for s in out['segments']], ['c00001', 'c00002'])
        self.assertEqual([s['source_id'] for s in out['provenance']['cues']], [None, None])

    def test_long_hours_use_integer_arithmetic(self):
        self.assertEqual(intake.timestamp_ms('100:59:59.999', 'vtt'), 363599999)
        self.assertEqual(intake.timestamp_ms('999999999:59:59.999', 'vtt'), 3599999999999999)

    def test_timestamp_grammar(self):
        for value in ('1:02.003', '00:60.001', '00:00.1', '00:00,000', '-00:00.000',
                      '00:00:60.000', '００:00.000', '0:00:00.000', '1000000000:00:00.000'):
            with self.subTest(value=value), self.assertRaises(intake.IntakeError):
                intake.timestamp_ms(value, 'vtt')
        with self.assertRaises(intake.IntakeError):
            intake.timestamp_ms('00:01,000', 'srt')

    def test_formatting_and_literal_entities(self):
        source = b'WEBVTT\n\n00:00.000 --> 00:01.000\n<c.green><b>One</b> <i>two</i></c> &lt;v Not-a-voice&gt;\nthree &gt; four'
        self.assertEqual(parse(source)['segments'][0]['text'], 'One two <v Not-a-voice>\nthree > four')
        self.assertEqual(parse(source)['segments'][0]['speaker'], 'Unspecified')

    def test_ambiguous_or_unsupported_markup_rejected(self):
        for payload in ('<v A>One</v><v B>Two</v>', 'Before<v A>After</v>', '<v A>One</v>After',
                        '<v A><v B>Two', '<v>Missing name', '<ruby>字<rt>reading</rt></ruby>',
                        '<00:00.500>karaoke', '<lang en>Language</lang>', '<b>Unclosed',
                        '<i>Mismatch</b>', '<br>Break', 'Literal < not escaped', '<unknown>Text</unknown>'):
            with self.subTest(payload=payload), self.assertRaisesRegex(intake.IntakeError, 'line 3, cue 1:'):
                parse(('WEBVTT\n\n00:00.000 --> 00:01.000\n' + payload).encode())

    def test_bad_header_missing_blank_and_mapping_rejected(self):
        for source in (b'\nWEBVTT\n\n00:00.000 --> 00:01.000\nA',
                       b'WEBVTTx\n\n00:00.000 --> 00:01.000\nA',
                       b'WEBVTT\n00:00.000 --> 00:01.000\nA',
                       b'WEBVTT\nX-TIMESTAMP-MAP=LOCAL:00:00.000,MPEGTS:900000\n\n00:00.000 --> 00:01.000\nA'):
            with self.subTest(source=source), self.assertRaises(intake.IntakeError):
                parse(source)

    def test_duplicate_source_ids_rejected(self):
        for source, fmt in ((VTT.replace(b'second\n', b'first\n'), 'vtt'), (SRT.replace(b'\r\n2\r\n', b'\r\n1\r\n'), 'srt')):
            with self.subTest(fmt=fmt), self.assertRaisesRegex(intake.IntakeError, 'duplicate'):
                parse(source, fmt)

    def test_reverse_or_empty_intervals_and_unordered_cues(self):
        for source in (VTT.replace(b'00:02.456', b'00:00.123'), VTT.replace(b'00:02.456', b'00:00.000'),
                       VTT.replace(b'00:02.000', b'00:00.001')):
            with self.subTest(source=source), self.assertRaises(intake.IntakeError):
                parse(source)

    def test_srt_counter_settings_empty_and_missing_timing(self):
        for source in (b'00:00:00,000 --> 00:00:01,000\nA', b'x\n00:00:00,000 --> 00:00:01,000\nA',
                       b'1\n00:00:00,000 --> 00:00:01,000 X1:3\nA', b'1\n00:00:00,000 --> 00:00:01,000\n', b'1'):
            with self.subTest(source=source), self.assertRaises(intake.IntakeError):
                parse(source, 'srt')

    def test_missing_cue_blank_line_not_silently_consumed(self):
        with self.assertRaisesRegex(intake.IntakeError, 'payload contains -->'):
            parse(VTT.replace(b'</v>\n\nsecond', b'</v>\nsecond'))

    def test_metadata_order_and_setting_token_validation(self):
        for source in (VTT + b'\nSTYLE\n::cue {}', VTT.replace(b'align:start', b'align')):
            with self.subTest(source=source), self.assertRaises(intake.IntakeError):
                parse(source)

    def test_size_encoding_control_and_label_limits(self):
        for source in (b'', b' ', b'WEBVTT\n', VTT + b'\x00'):
            with self.subTest(source=source), self.assertRaises(intake.IntakeError):
                parse(source)
        with mock.patch.object(intake, 'MAX_BYTES', 10), self.assertRaises(intake.IntakeError):
            parse()
        with mock.patch.object(intake, 'MAX_CUES', 1), self.assertRaises(intake.IntakeError):
            parse()
        for kwargs in ({'encoding': 'not-a-codec'}, {'encoding': 'cp1252'}, {'default_speaker': ''}, {'default_speaker': 'A\nB'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(intake.IntakeError):
                parse(**kwargs)
        for title in ('', 'x' * 301, 'line\nbreak'):
            with self.subTest(title=title), self.assertRaises(intake.IntakeError):
                intake.parse_captions(VTT, fmt='vtt', title=title)


class CanonicalAdapter(unittest.TestCase):
    def setUp(self):
        self.source = VTT.replace(b'00:02.000', b'00:02.456')
        self.parsed = parse(self.source)

    def test_seconds_envelope_and_false_verification(self):
        out = intake.canonical_episode(self.parsed, '4.005', synthetic_demo=True)
        self.assertEqual(out['duration'], 4.005)
        self.assertEqual(out['chapters'], [])
        self.assertTrue(out['synthetic_demo'])
        self.assertEqual(out['segments'][0]['start'], .123)
        self.assertEqual(out['segments'][0]['end'], 2.456)
        self.assertTrue(all(row['verified'] is False for row in out['segments']))
        self.assertNotIn('start_ms', out['segments'][0])
        self.assertEqual(self.parsed['segments'][0]['start_ms'], 123)

    def test_overlap_is_reported_without_shifting(self):
        original = parse()
        before = intake.json_bytes(original)
        with self.assertRaisesRegex(intake.IntakeError, 'overlap at c00002'):
            intake.canonical_episode(original, '10')
        self.assertEqual(intake.json_bytes(original), before)
        self.assertTrue(intake.create_bundle(VTT, original))

    def test_duration_comes_from_caller_and_is_bounded(self):
        self.assertEqual(intake.canonical_episode(self.parsed, '10')['duration'], 10)
        for duration in ('NaN', 'Infinity', '-Infinity', '0', '-1', '86400.001', 'word', '4.004999999999999999999'):
            with self.subTest(duration=duration), self.assertRaises(intake.IntakeError):
                intake.canonical_episode(self.parsed, duration)
        self.assertEqual(intake.canonical_episode(self.parsed, '86400')['duration'], 86400)

    def test_nonstring_duration_and_nonboolean_demo_rejected(self):
        for duration in (True, 10, 4.005, None, [], '1' * 65):
            with self.subTest(duration=duration), self.assertRaises(intake.IntakeError):
                intake.canonical_episode(self.parsed, duration)
        with self.assertRaises(intake.IntakeError):
            intake.canonical_episode(self.parsed, '10', synthetic_demo='yes')

    def test_optional_import_zip_preserves_integer_original_and_hashes(self):
        blob = intake.create_bundle(self.source, self.parsed, duration_seconds='10', synthetic_demo=True)
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            self.assertEqual(archive.read('source.vtt'), self.source)
            self.assertEqual(json.loads(archive.read('transcript.json'))['segments'][0]['start_ms'], 123)
            out = json.loads(archive.read('episode-import.json'))
            self.assertEqual(out['segments'][0]['start'], .123)
            manifest = json.loads(archive.read('manifest.json'))
            for name, info in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), info['sha256'])

    def test_cli_adapter_failure_does_not_publish_or_modify_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, dest = root / 'overlap.vtt', root / 'handoff.zip'
            source.write_bytes(VTT)
            run = subprocess.run([sys.executable, intake.__file__, str(source), '--title', 'Overlap',
                                  '--duration-seconds', '10', '--output', str(dest)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn('overlap', run.stderr)
            self.assertFalse(dest.exists())
            self.assertEqual(source.read_bytes(), VTT)

    def test_cli_adapter_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, dest = root / 'captions.vtt', root / 'handoff.zip'
            source.write_bytes(self.source)
            run = subprocess.run([sys.executable, intake.__file__, str(source), '--title', 'Fictional example',
                                  '--duration-seconds', '10', '--synthetic-demo', '--output', str(dest)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)['episode_import'])
            with zipfile.ZipFile(dest) as archive:
                self.assertTrue(json.loads(archive.read('episode-import.json'))['synthetic_demo'])


class Publication(unittest.TestCase):
    def test_deterministic_bundle_preserves_exact_source_and_hashes(self):
        parsed = parse()
        data = intake.create_bundle(VTT, parsed)
        self.assertEqual(data, intake.create_bundle(VTT, parsed))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(set(archive.namelist()), {'source.vtt', 'transcript.json', 'manifest.json'})
            self.assertEqual(archive.read('source.vtt'), VTT)
            self.assertEqual(json.loads(archive.read('transcript.json')), parsed)
            manifest = json.loads(archive.read('manifest.json'))
            for name, info in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), info['sha256'])
                self.assertEqual(len(archive.read(name)), info['bytes'])

    def test_source_mismatch_rejected(self):
        with self.assertRaisesRegex(intake.IntakeError, 'no longer match'):
            intake.create_bundle(VTT + b'\n', parse())

    def test_exclusive_publication_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'bundle.zip'
            intake.publish_bundle(dest, b'first')
            with self.assertRaises(intake.IntakeError):
                intake.publish_bundle(dest, b'second')
            self.assertEqual(dest.read_bytes(), b'first')
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ['bundle.zip'])

    def test_symlink_and_directory_targets_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'real'
            target.write_bytes(b'keep')
            symlink = root / 'link.zip'
            symlink.symlink_to(target)
            directory = root / 'directory.zip'
            directory.mkdir()
            for dest in (symlink, directory):
                with self.subTest(dest=dest), self.assertRaises(intake.IntakeError):
                    intake.publish_bundle(dest, b'replace')
            self.assertEqual(target.read_bytes(), b'keep')
            self.assertTrue(symlink.is_symlink())
            self.assertTrue(directory.is_dir())

    def test_concurrent_publish_has_one_complete_winner(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'winner.zip'
            payloads = [bytes([i]) * 10000 for i in range(8)]
            def attempt(payload):
                try:
                    intake.publish_bundle(dest, payload)
                    return payload
                except intake.IntakeError:
                    return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(attempt, payloads))
            winners = [result for result in results if result is not None]
            self.assertEqual(len(winners), 1)
            self.assertEqual(dest.read_bytes(), winners[0])
            self.assertEqual(len(list(Path(temp).iterdir())), 1)

    def test_failed_staging_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'bundle.zip'
            with mock.patch.object(intake.os, 'fsync', side_effect=OSError(5, 'injected I/O failure')):
                with self.assertRaises(intake.IntakeError):
                    intake.publish_bundle(dest, b'data')
            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_cli_actual_success_reimport_and_invalid_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, dest = root / 'original.vtt', root / 'handoff.zip'
            source.write_bytes(VTT)
            cmd = [sys.executable, str(Path(intake.__file__)), str(source), '--title', 'Example', '--output', str(dest)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)['cues'], 2)
            before = dest.read_bytes()
            again = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(dest.read_bytes(), before)
            self.assertEqual(source.read_bytes(), VTT)
            invalid = root / 'invalid.vtt'
            invalid.write_bytes(b'WEBVTT\n\nnot a cue')
            failed = subprocess.run([*cmd[:2], str(invalid), '--title', 'Bad', '--output', str(root / 'bad.zip')], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertFalse((root / 'bad.zip').exists())


if __name__ == '__main__':
    unittest.main()
