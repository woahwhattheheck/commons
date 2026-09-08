# SPDX-License-Identifier: MIT
"""Compose only the exact objective comparator into an existing fleet source.

The original source is never rewritten. Independent distance, topology, and
neighborhood changes remain byte-identical. Optional manifest handling updates
only the one main.cpp record, after checking that it describes the input bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

OLD = '''        std::sort(before.begin(), before.end(), std::greater<long long>());
        std::sort(after.begin(), after.end(), std::greater<long long>());
        if (!(after < before)) return false;'''
NEW = '''        if (!quantizedImproves(before, after)) return false;'''
ANCHOR = '''    // Simultaneous moves are evaluated against the same incumbent. No tentative'''


def function_body() -> str:
    source = Path(__file__).with_name('quantized_compare.hpp').read_text(encoding='utf-8')
    body = source[source.index('    if (before.size()'):source.index('\n} // namespace')]
    body = body[:body.rfind('\n}')]
    body = '\n'.join(line for line in body.splitlines() if 'if (stats)' not in line)
    return '''    // Exact first-stratum shortcut; all unresolved comparisons retain the
    // original full descending sort. Quantization remains at the call site.
    static bool quantizedImproves(std::vector<long long>& before,
                                  std::vector<long long>& after) {
''' + '\n'.join('    ' + line for line in body.splitlines()) + '\n    }\n\n'


def apply(source: str) -> str:
    helper = function_body()
    if source.count(helper) == 1 and source.count(NEW) == 1 and OLD not in source:
        return source
    if source.count(OLD) != 1 or source.count(ANCHOR) != 1 or 'quantizedImproves' in source:
        raise ValueError('Expected one original comparison and one placement anchor')
    return source.replace(ANCHOR, helper + ANCHOR, 1).replace(OLD, NEW, 1)


def update_manifest(manifest: dict[str, Any], original: bytes, changed: bytes) -> dict[str, Any]:
    # JSON round-trip makes a detached document; all other entries are retained.
    result = json.loads(json.dumps(manifest))
    entries = [row for row in result['files'] if row['path'] == 'main.cpp']
    if len(entries) != 1:
        raise ValueError('Expected exactly one main.cpp manifest record')
    entry = entries[0]
    if entry['bytes'] != len(original) or entry['sha256'] != hashlib.sha256(original).hexdigest():
        raise ValueError('Manifest does not describe the supplied source')
    entry.update(bytes=len(changed), sha256=hashlib.sha256(changed).hexdigest())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--manifest-output', type=Path)
    args = parser.parse_args()
    if (args.manifest is None) != (args.manifest_output is None):
        parser.error('Supply both manifest options together')
    for path in (args.output, args.manifest_output):
        if path is not None and path.exists():
            raise FileExistsError(path)
    if args.manifest_output is not None and args.output.resolve() == args.manifest_output.resolve():
        raise ValueError('Use distinct output paths')
    original = args.source.read_bytes()
    changed = apply(original.decode('utf-8')).encode('utf-8')
    document = None
    if args.manifest is not None:
        document = update_manifest(json.loads(args.manifest.read_text(encoding='utf-8')), original, changed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(changed)
    if document is not None:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest_output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(document, indent=2) + '\n')
    print(json.dumps({'source_sha256': hashlib.sha256(original).hexdigest(),
                      'output_sha256': hashlib.sha256(changed).hexdigest(),
                      'bytes': len(changed), 'changed': changed != original}))


if __name__ == '__main__':
    main()
