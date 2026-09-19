from __future__ import annotations
import json
import os
import shutil
from datetime import date
from pathlib import Path
from tools.public_surface_link_guard import codec, core
from tools.public_surface_link_guard.codec import GuardError, loads
from test_public_surface_link_guard import Base

class HostileTests(Base):

    def test_duplicate_json(self):
        with self.assertRaisesRegex(GuardError, 'duplicate JSON key'):
            loads('{"schema":"x","schema":"y"}')

    def test_float_nonfinite(self):
        for source in ('{"x":1.0}', '{"x":NaN}'):
            with self.subTest(source=source), self.assertRaises(GuardError):
                loads(source)

    def test_huge_integer_is_guard_error(self):
        with self.assertRaisesRegex(GuardError, 'safe range'):
            loads('{"x":' + '9' * 5000 + '}')

    def test_unknown_manifest_key(self):
        self.write('site/index.html', 'ok')
        manifest = self.m()
        manifest['send_authorized'] = True
        with self.assertRaisesRegex(GuardError, 'unknown keys'):
            self.scan(manifest)

    def test_internal_must_be_explicit_and_cannot_carry_public_base(self):
        self.write('site/index.html', 'ok')
        manifest = self.m()
        manifest['surfaces'][0] = {'path': 'site/index.html', 'class': 'INTERNAL', 'public_base_url': 'https://example.com/'}
        with self.assertRaisesRegex(GuardError, 'INTERNAL must not'):
            self.scan(manifest)

    def test_exception_transplant(self):
        self.write('site/index.html', 'ok')
        self.write('site/other.html', 'ok')
        manifest = self.m()
        manifest['exceptions'] = [{'path': 'site/other.html', 'destination': 'https://woahwhattheheck.github.io/commons/', 'expires_on': '2026-09-18', 'reason': 'wrong'}]
        with self.assertRaisesRegex(GuardError, 'not a declared public surface'):
            self.scan(manifest)

    def test_exception_cannot_target_internal(self):
        self.write('site/index.html', 'ok')
        self.write('internal/provenance.md', 'ok')
        manifest = self.m()
        manifest['surfaces'].append({'path': 'internal/provenance.md', 'class': 'INTERNAL'})
        manifest['exceptions'] = [{'path': 'internal/provenance.md', 'destination': 'https://github.com/woahwhattheheck/commons', 'expires_on': '2026-09-18', 'reason': 'wrong'}]
        with self.assertRaisesRegex(GuardError, 'not a declared public surface'):
            self.scan(manifest)

    def test_alias_target_must_be_blocked(self):
        self.write('site/index.html', 'ok')
        manifest = self.m()
        manifest['aliases'] = [{'alias': 'https://go.example/x', 'target': 'https://product.example/x'}]
        with self.assertRaisesRegex(GuardError, 'target must be blocked'):
            self.scan(manifest)

    def test_bad_custom_block_kind(self):
        self.write('site/index.html', 'ok')
        manifest = self.m()
        manifest['blocked_destinations'] = [{'id': 'x', 'kind': 'ANYTHING', 'destination': 'https://internal.example/x', 'match': 'EXACT'}]
        with self.assertRaisesRegex(GuardError, 'kind invalid'):
            self.scan(manifest)

    def test_symlink_leaf(self):
        self.write('real.html', 'https://woahwhattheheck.github.io/commons/')
        (self.root / 'site').mkdir(exist_ok=True)
        try:
            (self.root / 'site/index.html').symlink_to(self.root / 'real.html')
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(GuardError, 'cannot open file component|non-symlink'):
            self.scan(self.m())

    def test_symlink_parent(self):
        self.write('real/index.html', 'https://woahwhattheheck.github.io/commons/')
        try:
            (self.root / 'site').symlink_to(self.root / 'real', target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        with self.assertRaisesRegex(GuardError, 'cannot open directory component'):
            self.scan(self.m())

    def test_parent_remint_during_read_is_rejected(self):
        self.write('site/index.html', 'https://woahwhattheheck.github.io/commons/' + 'x' * 80000)
        original_read = codec.os.read
        old_root = self.root.with_name(self.root.name + '-old')
        triggered = False

        def hostile_read(fd, count):
            nonlocal triggered
            chunk = original_read(fd, count)
            if not triggered:
                triggered = True
                os.rename(self.root, old_root)
                self.root.mkdir()
                (self.root / 'site').mkdir()
                (self.root / 'site/index.html').write_text('https://product.example/', encoding='utf-8')
            return chunk
        try:
            with self.assertRaisesRegex(GuardError, 'visible path generation changed'):
                codec.read_text(self.root / 'site/index.html', 2 * 1024 * 1024, _read_fn=hostile_read)
        finally:
            if old_root.exists():
                shutil.rmtree(self.root, ignore_errors=True)
                os.rename(old_root, self.root)

    def test_process_current_scan_resists_semantic_global_rebind(self):
        self.write('site/index.html', 'https://github.com/woahwhattheheck/commons/tree/main/x')
        manifest = self.m()
        manifest['exceptions'] = [{'path': 'site/index.html', 'destination': 'https://github.com/woahwhattheheck/commons/tree/main/x', 'expires_on': '2000-01-01', 'reason': 'expired'}]
        manifest_path = self.root / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        original = core._scan_impl
        core._scan_impl = lambda **kwargs: {'state': 'PASS_INJECTED'}
        try:
            result = core.scan_paths(root=self.root, manifest_path=manifest_path)
        finally:
            core._scan_impl = original
        self.assertEqual(result['evaluation_mode'], 'PROCESS_CURRENT')
        self.assertEqual(result['state'], 'HOLD_PUBLIC_COMMONS_BACKLINK')
        self.assertEqual(result['violations'][0]['reason'], 'EXPIRED_EXCEPTION')

    def test_process_current_scan_resists_helper_global_rebinds(self):
        self.write('site/index.html', 'https://github.com/woahwhattheheck/commons/tree/main/x')
        manifest = self.m()
        manifest['exceptions'] = [{'path': 'site/index.html', 'destination': 'https://github.com/woahwhattheheck/commons/tree/main/x', 'expires_on': '2000-01-01', 'reason': 'expired'}]
        manifest_path = self.root / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        saved = (core._banned, core._candidate, core._PARSE_DATE, core._validate_impl, core._links, core._normalize_path)
        core._banned = lambda *args, **kwargs: None
        core._candidate = lambda *args, **kwargs: None
        core._PARSE_DATE = lambda *args, **kwargs: date(2999, 1, 1)
        core._validate_impl = lambda *args, **kwargs: {'surfaces': [], 'exceptions': [], 'aliases': [], 'blocked_destinations': []}
        core._links = lambda *args, **kwargs: []
        core._normalize_path = lambda *args, **kwargs: '/'
        try:
            result = core.scan_paths(root=self.root, manifest_path=manifest_path)
        finally:
            core._banned, core._candidate, core._PARSE_DATE, core._validate_impl, core._links, core._normalize_path = saved
        self.assertEqual(result['evaluation_mode'], 'PROCESS_CURRENT')
        self.assertEqual(result['state'], 'HOLD_PUBLIC_COMMONS_BACKLINK')
        self.assertEqual(result['violations'][0]['reason'], 'EXPIRED_EXCEPTION')

    def test_process_current_manifest_without_public_base_roundtrips(self):
        self.write('site/index.html', '//github.com/woahwhattheheck/commons/x')
        manifest = self.m(None)
        manifest_path = self.root / 'manifest-no-base.json'
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        result = core.scan_paths(root=self.root, manifest_path=manifest_path)
        self.assertEqual(result['evaluation_mode'], 'PROCESS_CURRENT')
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_raw_github_representation_cannot_bypass(self):
        self.write('site/index.html', 'https://raw.githubusercontent.com/woahwhattheheck/commons/main/README.md')
        result = self.scan(self.m(None))
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_api_github_representation_cannot_bypass(self):
        self.write('site/index.html', 'https://api.github.com/repos/woahwhattheheck/commons/contents/README.md')
        result = self.scan(self.m(None))
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_codeload_github_representation_cannot_bypass(self):
        self.write('site/index.html', 'https://codeload.github.com/woahwhattheheck/commons/zip/refs/heads/main')
        result = self.scan(self.m(None))
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_github_clone_representation_cannot_bypass(self):
        self.write('site/index.html', 'https://github.com/woahwhattheheck/commons.git')
        result = self.scan(self.m(None))
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_dot_segment_browser_path_cannot_bypass(self):
        self.write('site/index.html', 'https://github.com/woahwhattheheck/other/../commons/tree/main/x')
        result = self.scan(self.m(None))
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_GITHUB')

    def test_alias_query_suffix_cannot_bypass(self):
        self.write('site/index.html', 'https://go.example/context?utm=1#x')
        manifest = self.m()
        manifest['aliases'] = [{'alias': 'https://go.example/context', 'target': 'https://woahwhattheheck.github.io/commons/'}]
        result = self.scan(manifest)
        self.assertEqual(result['violations'][0]['reason'], 'COMMONS_PAGES')
        self.assertEqual(result['violations'][0]['via_alias'], 'https://go.example/context')

    def test_deterministic(self):
        self.write('site/index.html', 'https://woahwhattheheck.github.io/commons/x\nhttps://github.com/woahwhattheheck/commons')
        self.assertEqual(self.scan(self.m()), self.scan(self.m()))
if __name__ == '__main__':
    import unittest
    unittest.main()
