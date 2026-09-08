#!/usr/bin/env python3
"""Stage the published ROADEF portfolio and one pinned public container input."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import time
import urllib.error
import urllib.request
import zipfile

SOURCE_COMMIT = '2885d176373c33410148829fef93c310c3752c0b'
SOURCE_ROOT = 'revenue/roadef2026/fleet-candidate'
PREPARER_COMMIT = '1e31f2b2bef235bb145980c9ceed49580b1e55fb'  # Existing QUARTZ PR10171.
INPUTS = {'setB/setB-01-net.json': 'network.json',
          'setB/setB-01-tm.json': 'traffic.json',
          'setB/setB-01-scenario.json': 'scenario.json'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(name, *, commit=SOURCE_COMMIT):
    url = f'https://raw.githubusercontent.com/woahwhattheheck/commons/{commit}/{SOURCE_ROOT}/{name}'
    request = urllib.request.Request(url,
                                     headers={'User-Agent': 'ROADEF-container-validation/1'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    source, archives, data = (output / name for name in ('source', 'archives', 'data'))
    for path in (source, archives, data):
        path.mkdir()
    manifest_raw = fetch('PUBLIC-SOURCE-MANIFEST.json')
    manifest = json.loads(manifest_raw)
    (source / 'PUBLIC-SOURCE-MANIFEST.json').write_bytes(manifest_raw)
    source_files = []
    for row in manifest['files']:
        name = PurePosixPath(row['path'])
        if name.is_absolute() or '..' in name.parts:
            raise ValueError(f'Invalid source manifest path: {name}')
        raw = fetch(name.as_posix())
        if len(raw) != row['bytes'] or digest(raw) != row['sha256']:
            raise ValueError(f'Published source identity differs: {name}')
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        source_files.append(row)
    # Preserve the full original publication, then use the source-staging repair
    # from QUARTZ's existing merged repair. Solver/runtime bytes remain pinned.
    used_preparer = fetch('prepare_context.py', commit=PREPARER_COMMIT)
    preparer = output / 'PREPARER.py'
    preparer.write_bytes(used_preparer)
    spec = importlib.util.spec_from_file_location('repaired_roadef_prepare', preparer)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for archive in module.ARCHIVES.values():
        module.fetch_verified(archive, archives, None)
    context = output / 'context'
    context_manifest = module.prepare(context, source, source / 'main.cpp', archives)
    official = module.ARCHIVES['checker']
    input_files = []
    with zipfile.ZipFile(archives / official['file']) as archive:
        for info, relative in module.archive_members(archive, official):
            if str(relative) in INPUTS:
                raw = archive.read(info)
                name = INPUTS[str(relative)]
                (data / name).write_bytes(raw)
                input_files.append({'archive_member': info.filename, 'path': name,
                                    'bytes': len(raw), 'sha256': digest(raw)})
    if {row['path'] for row in input_files} != set(INPUTS.values()):
        raise ValueError('Pinned official archive is missing a B01 input')
    report = {'source_commit': SOURCE_COMMIT, 'source_root': SOURCE_ROOT,
              'public_manifest_sha256': digest(manifest_raw), 'source_files': source_files,
              'preparer': {'path': 'revenue/roadef2026/fleet-candidate/prepare_context.py',
                           'commit': PREPARER_COMMIT, 'existing_repair_pr': 10171,
                           'used_sha256': digest(used_preparer),
                           'original_sha256': digest((source / 'prepare_context.py').read_bytes()),
                           'change': 'Preserve the pinned extensionless SparseHash header family'},
              'archives': context_manifest['archives'], 'inputs': input_files,
              'context_manifest_sha256': digest((context / 'source-manifest.json').read_bytes()),
              'scope': 'Published solver/runtime bytes with explicit source-staging repair; B01 container behavior only'}
    (output / 'PREPARATION.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'source_commit': SOURCE_COMMIT, 'source_files': len(source_files),
                      'archives_verified': len(module.ARCHIVES), 'inputs': len(input_files)}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output.resolve())


if __name__ == '__main__':
    main()
