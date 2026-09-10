#!/usr/bin/env python3
"""Install fail-closed, non-mutating diagnostics into build_integrated.py.

This patcher is intentionally exact and idempotent. It refuses to edit an
unknown builder shape so the one-shot closure workflow cannot silently rewrite
concurrent release work.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
TARGET = LAB / "build_integrated.py"
MARKER = "def _runtime_drift(actual_manifest, expected_manifest):"

DIAGNOSTICS = r'''

def _read_json_file(path):
    """Return (object, raw bytes, error) without hiding missing/corrupt state."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None, None, 'missing'
    except OSError as error:
        return None, None, type(error).__name__+': '+str(error)
    try:
        return json.loads(raw.decode('utf-8')), raw, None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return None, raw, type(error).__name__+': '+str(error)


def _runtime_drift(actual_manifest, expected_manifest):
    """Describe exact archive-member metadata drift, sorted for stable receipts."""
    actual = (actual_manifest.get('runtime', {})
              if isinstance(actual_manifest, dict) else {})
    expected = (expected_manifest.get('runtime', {})
                if isinstance(expected_manifest, dict) else {})
    if not isinstance(actual, dict):
        actual = {}
    if not isinstance(expected, dict):
        expected = {}
    actual_names = set(actual)
    expected_names = set(expected)
    changed = []
    for member in sorted(actual_names & expected_names):
        if actual[member] != expected[member]:
            changed.append({'member': member,
                            'actual': actual[member],
                            'expected': expected[member]})
    return {
        'added': sorted(expected_names-actual_names),
        'removed': sorted(actual_names-expected_names),
        'changed': changed,
        'unchanged': sum(actual[name] == expected[name]
                         for name in actual_names & expected_names),
    }


def _diagnose_rendered(data, manifest, receipt):
    """Compare one rendered release with all three committed publication points."""
    pointer_path = ROOT/(RECORD+'CURRENT-ARCHIVE.json')
    manifest_path = ROOT/(RECORD+'CURRENT-SOURCE.json')
    archive_path = ROOT/ARCHIVE
    actual_pointer, pointer_bytes, pointer_error = _read_json_file(pointer_path)
    actual_manifest, actual_manifest_bytes, manifest_error = _read_json_file(manifest_path)
    try:
        actual_archive = archive_path.read_bytes()
        archive_error = None
    except FileNotFoundError:
        actual_archive = None
        archive_error = 'missing'
    except OSError as error:
        actual_archive = None
        archive_error = type(error).__name__+': '+str(error)
    expected_manifest = json.loads(manifest.decode('utf-8'))
    pointer_matches = pointer_error is None and actual_pointer == receipt
    manifest_matches = manifest_error is None and actual_manifest_bytes == manifest
    archive_matches = archive_error is None and actual_archive == data
    report = {
        'status': ('clean' if pointer_matches and manifest_matches and archive_matches
                   else 'drift'),
        'pointer': {
            'path': RECORD+'CURRENT-ARCHIVE.json',
            'matches': pointer_matches,
            'error': pointer_error,
            'actual': actual_pointer,
            'expected': receipt,
            'actual_sha256': (hashlib.sha256(pointer_bytes).hexdigest()
                              if pointer_bytes is not None else None),
        },
        'archive': {
            'path': ARCHIVE,
            'matches': archive_matches,
            'error': archive_error,
            'actual_sha256': (hashlib.sha256(actual_archive).hexdigest()
                              if actual_archive is not None else None),
            'expected_sha256': hashlib.sha256(data).hexdigest(),
            'actual_bytes': (len(actual_archive)
                             if actual_archive is not None else None),
            'expected_bytes': len(data),
        },
        'manifest': {
            'path': RECORD+'CURRENT-SOURCE.json',
            'matches': manifest_matches,
            'error': manifest_error,
            'actual_sha256': (hashlib.sha256(actual_manifest_bytes).hexdigest()
                              if actual_manifest_bytes is not None else None),
            'expected_sha256': hashlib.sha256(manifest).hexdigest(),
            'actual_bytes': (len(actual_manifest_bytes)
                             if actual_manifest_bytes is not None else None),
            'expected_bytes': len(manifest),
        },
        'runtime': _runtime_drift(actual_manifest, expected_manifest),
    }
    return report


def diagnose_current():
    """Return a deterministic, non-mutating source/archive/pointer drift report."""
    return _diagnose_rendered(*render())


def _drift_summary(report, limit=8):
    runtime = report['runtime']
    groups = (
        ('runtime_added', runtime['added']),
        ('runtime_removed', runtime['removed']),
        ('runtime_changed', [item['member'] for item in runtime['changed']]),
    )
    parts = []
    for label, names in groups:
        if names:
            suffix = ',...(+%d)' % (len(names)-limit) if len(names) > limit else ''
            parts.append(label+'='+','.join(names[:limit])+suffix)
    stale = [name for name in ('pointer', 'archive', 'manifest')
             if not report[name]['matches']]
    parts.append('stale='+','.join(stale))
    return '; '.join(parts)
'''

OLD_VERIFY = '''def verify_current():
    """Fail on stale source, stale pointer, changed config or archive contents."""
    data,manifest,receipt=render()
    actual=json.loads((ROOT/(RECORD+'CURRENT-ARCHIVE.json')).read_text())
    if actual!=receipt:raise ValueError('Current release pointer differs from current source')
    if (ROOT/ARCHIVE).read_bytes()!=data:raise ValueError('Canonical archive differs from current source')
    if (ROOT/(RECORD+'CURRENT-SOURCE.json')).read_bytes()!=manifest:
        raise ValueError('Current manifest differs from current source')
    return receipt
'''

NEW_VERIFY = '''def verify_current():
    """Fail on stale source, stale pointer, changed config or archive contents."""
    data,manifest,receipt=render()
    report=_diagnose_rendered(data,manifest,receipt)
    detail=_drift_summary(report)
    if not report['pointer']['matches']:
        raise ValueError('Current release pointer differs from current source: '+detail)
    if not report['archive']['matches']:
        raise ValueError('Canonical archive differs from current source: '+detail)
    if not report['manifest']['matches']:
        raise ValueError('Current manifest differs from current source: '+detail)
    return receipt
'''

OLD_CLI = '''if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--release',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    print(json.dumps(verify_current() if args.check else build_release()))
'''

NEW_CLI = '''if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--diagnose',action='store_true',
                      help='report exact source/archive/pointer drift without writing')
    mode.add_argument('--release',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    result=(diagnose_current() if args.diagnose else
            verify_current() if args.check else build_release())
    print(json.dumps(result,sort_keys=True))
'''


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    before = TARGET.read_bytes()
    text = before.decode("utf-8")
    if MARKER in text:
        if "--diagnose" not in text or NEW_VERIFY not in text:
            raise SystemExit("partial or foreign diagnostic patch already present")
        print(json.dumps({"changed": False, "path": str(TARGET.relative_to(LAB)),
                          "sha256": digest(before)}, sort_keys=True))
        return
    if text.count("\ndef verify_current():\n") != 1:
        raise SystemExit("verify_current anchor count differs from one")
    if text.count(OLD_VERIFY) != 1:
        raise SystemExit("known verify_current body not found exactly once")
    if text.count(OLD_CLI) != 1:
        raise SystemExit("known CLI body not found exactly once")
    text = text.replace("\ndef verify_current():\n", DIAGNOSTICS + "\ndef verify_current():\n", 1)
    text = text.replace(OLD_VERIFY, NEW_VERIFY, 1)
    text = text.replace(OLD_CLI, NEW_CLI, 1)
    after = text.encode("utf-8")
    TARGET.write_bytes(after)
    print(json.dumps({"changed": True, "path": str(TARGET.relative_to(LAB)),
                      "before_sha256": digest(before),
                      "after_sha256": digest(after)}, sort_keys=True))


if __name__ == "__main__":
    main()
