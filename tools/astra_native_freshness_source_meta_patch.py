#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
base = root / 'revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/native-package-freshness'
checker = base / 'check_native_freshness.py'
tests = base / 'test_check_native_freshness.py'
deletions = base / 'test_native_freshness_tracked_deletion.py'
readme = base / 'README.md'

text = checker.read_text(encoding='utf-8')
anchor = 'PUBLISHER = "build_integrated.py"\nSOURCE_MANIFEST = "SOURCE.json"\nMAX_ARCHIVE_BYTES = 32 * 1024 * 1024\n'
replacement = (
    'PUBLISHER = "build_integrated.py"\n'
    'SOURCE_MANIFEST = "SOURCE.json"\n'
    'RELEASE_METADATA = "runtime/integrated-selected/RELEASE.json"\n'
    'ENTRYPOINT = "main.py::agent"\n'
    'CONFIG_MEMBER = "TITAN-CONFIG.json"\n'
    'MAX_ARCHIVE_BYTES = 32 * 1024 * 1024\n'
)
if text.count(anchor) != 1:
    raise SystemExit('checker constants anchor drift')
text = text.replace(anchor, replacement, 1)

git_anchor = '    return proc.stdout.strip()\n\n\ndef _assert_no_tracked_deletions'
git_insert = '''    return proc.stdout.strip()\n\n\ndef _git_bytes(repo_root: Path, *args: str) -> bytes:\n    try:\n        proc = subprocess.run(\n            ["git", "-C", str(repo_root), *args],\n            check=True,\n            stdout=subprocess.PIPE,\n            stderr=subprocess.PIPE,\n        )\n    except (OSError, subprocess.CalledProcessError) as exc:\n        detail = getattr(exc, "stderr", b"")\n        if isinstance(detail, bytes):\n            detail = detail.decode("utf-8", errors="replace")\n        detail = detail or str(exc)\n        raise InvalidEvidence("git byte binding failed: " + detail.strip()) from exc\n    return proc.stdout\n\n\ndef _assert_no_tracked_deletions'''
if text.count(git_anchor) != 1:
    raise SystemExit('checker git anchor drift')
text = text.replace(git_anchor, git_insert, 1)

archive_anchor = '\ndef _read_archive_core(\n'
meta_helper = '''\ndef _canonical_source_metadata(\n    repo_root: Path,\n    live_rel: PurePosixPath,\n    expected_commit: str,\n    package: dict[str, bytes],\n) -> dict:\n    release_rel = live_rel / RELEASE_METADATA\n    release = _strict_json(\n        _git_bytes(repo_root, "show", f"{expected_commit}:{release_rel.as_posix()}"),\n        label=RELEASE_METADATA,\n    )\n    if type(release) is not dict:\n        raise InvalidEvidence("canonical RELEASE.json must contain an object")\n    config_raw = package.get(CONFIG_MEMBER)\n    if config_raw is None:\n        raise InvalidEvidence(f"archive missing canonical config member: {CONFIG_MEMBER}")\n    default = _strict_json(config_raw, label=CONFIG_MEMBER)\n    expected = dict(release)\n    expected.update(\n        {\n            "entrypoint": ENTRYPOINT,\n            "config": CONFIG_MEMBER,\n            "default": default,\n        }\n    )\n    expected.pop("runtime", None)\n    return expected\n\n\ndef _read_archive_core(\n'''
if text.count(archive_anchor) != 1:
    raise SystemExit('checker archive anchor drift')
text = text.replace(archive_anchor, meta_helper, 1)

old_ann = ') -> tuple[str, dict[str, bytes], dict[str, str]]:\n'
new_ann = ') -> tuple[str, dict[str, bytes], dict[str, str], dict]:\n'
if text.count(old_ann) != 1:
    raise SystemExit('checker return annotation drift')
text = text.replace(old_ann, new_ann, 1)

old_return = '    return actual_sha256, {name: found[name] for name in source_map}, source_map\n'
new_return = '    return actual_sha256, {name: found[name] for name in source_map}, source_map, manifest\n'
if text.count(old_return) != 1:
    raise SystemExit('checker archive return drift')
text = text.replace(old_return, new_return, 1)

old_call = '''        actual_archive_sha256, package, source_map = _read_archive_core(\n            archive, expected_archive_sha256\n        )\n        base["archive_sha256"] = actual_archive_sha256\n'''
new_call = '''        actual_archive_sha256, package, source_map, source_manifest = _read_archive_core(\n            archive, expected_archive_sha256\n        )\n        base["archive_sha256"] = actual_archive_sha256\n        actual_metadata = dict(source_manifest)\n        actual_metadata.pop("runtime", None)\n        expected_metadata = _canonical_source_metadata(\n            repo_root, live_rel, expected_commit, package\n        )\n        if actual_metadata != expected_metadata:\n            raise InvalidEvidence(\n                "SOURCE.json top-level metadata does not match canonical publisher construction"\n            )\n'''
if text.count(old_call) != 1:
    raise SystemExit('checker archive call drift')
text = text.replace(old_call, new_call, 1)
checker.write_text(text, encoding='utf-8')

# Established fixture: make RELEASE metadata part of exact commit and SOURCE construction.
t = tests.read_text(encoding='utf-8')
setup_anchor = '''        self.live.mkdir(parents=True)\n        for name, data in PACKAGE.items():\n'''
setup_repl = '''        self.live.mkdir(parents=True)\n        release = self.live / "runtime/integrated-selected/RELEASE.json"\n        release.parent.mkdir(parents=True, exist_ok=True)\n        release.write_text('{"fixture":1,"release":"TEST"}\\n', encoding="utf-8")\n        for name, data in PACKAGE.items():\n'''
if t.count(setup_anchor) != 1:
    raise SystemExit('main test setup anchor drift')
t = t.replace(setup_anchor, setup_repl, 1)

sig_anchor = '''        declared_members=None,\n        extra_unmapped=None,\n    ):\n'''
sig_repl = '''        declared_members=None,\n        extra_unmapped=None,\n        manifest_overrides=None,\n    ):\n'''
if t.count(sig_anchor) != 1:
    raise SystemExit('main test archive signature drift')
t = t.replace(sig_anchor, sig_repl, 1)

source_anchor = '''        source = (json.dumps({"runtime": runtime}, sort_keys=True) + "\\n").encode()\n        path = self.root / "candidate.tar.gz"\n'''
source_repl = '''        source_doc = {\n            "fixture": 1,\n            "release": "TEST",\n            "entrypoint": "main.py::agent",\n            "config": "TITAN-CONFIG.json",\n            "default": json.loads(members["TITAN-CONFIG.json"].decode("utf-8")),\n            "runtime": runtime,\n        }\n        if manifest_overrides:\n            source_doc.update(manifest_overrides)\n        source = (json.dumps(source_doc, sort_keys=True) + "\\n").encode()\n        path = self.root / "candidate.tar.gz"\n'''
if t.count(source_anchor) != 1:
    raise SystemExit('main test source manifest anchor drift')
t = t.replace(source_anchor, source_repl, 1)

insert_before = '    def test_wrong_authenticated_digest_invalid(self):\n'
new_test = '''    def test_source_top_level_metadata_tamper_invalid(self):\n        poisons = (\n            ("entrypoint", "evil.py::agent"),\n            ("config", "OTHER.json"),\n            ("default", {"consumer": "forged"}),\n            ("release", "FORGED"),\n            ("extra_provenance", "untrusted"),\n        )\n        for key, value in poisons:\n            with self.subTest(key=key):\n                archive, digest = self.archive(manifest_overrides={key: value})\n                report = self.verify(archive, digest)\n                self.assertEqual("INVALID", report["verdict"])\n                self.assertIn("top-level metadata", report["problems"][0])\n\n'''
if t.count(insert_before) != 1:
    raise SystemExit('main test insertion anchor drift')
t = t.replace(insert_before, new_test + insert_before, 1)
tests.write_text(t, encoding='utf-8')

# Focused tracked-deletion fixture also needs canonical RELEASE/SOURCE metadata.
d = deletions.read_text(encoding='utf-8')
d_setup = '''        self.live.mkdir(parents=True)\n        for name, data in PACKAGE.items():\n'''
d_setup_repl = '''        self.live.mkdir(parents=True)\n        release = self.live / "runtime/integrated-selected/RELEASE.json"\n        release.parent.mkdir(parents=True, exist_ok=True)\n        release.write_text('{"fixture":1,"release":"TEST"}\\n', encoding="utf-8")\n        for name, data in PACKAGE.items():\n'''
if d.count(d_setup) != 1:
    raise SystemExit('deletion test setup anchor drift')
d = d.replace(d_setup, d_setup_repl, 1)
d_source = '''        source = (json.dumps({"runtime": runtime}, sort_keys=True) + "\\n").encode()\n        path = self.root / "candidate.tar.gz"\n'''
d_source_repl = '''        source_doc = {\n            "fixture": 1,\n            "release": "TEST",\n            "entrypoint": "main.py::agent",\n            "config": "TITAN-CONFIG.json",\n            "default": json.loads(PACKAGE["TITAN-CONFIG.json"].decode("utf-8")),\n            "runtime": runtime,\n        }\n        source = (json.dumps(source_doc, sort_keys=True) + "\\n").encode()\n        path = self.root / "candidate.tar.gz"\n'''
if d.count(d_source) != 1:
    raise SystemExit('deletion test source anchor drift')
d = d.replace(d_source, d_source_repl, 1)
deletions.write_text(d, encoding='utf-8')

r = readme.read_text(encoding='utf-8')
old = '5. require authenticated packaged `SOURCE.json.runtime` to match that canonical map exactly;\n'
new = ('5. require authenticated packaged `SOURCE.json.runtime` to match that canonical map exactly, and require every top-level `SOURCE.json` field to match canonical publisher construction from exact-commit `runtime/integrated-selected/RELEASE.json`, literal `entrypoint` / `config`, and the strict-parsed packaged `TITAN-CONFIG.json` default;\n')
if r.count(old) != 1:
    raise SystemExit('README numbered anchor drift')
r = r.replace(old, new, 1)
readme.write_text(r, encoding='utf-8')
