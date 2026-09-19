#!/usr/bin/env python3
"""Exercise the real thin renderer against verified synthetic completion markers.

This is not the four-suite/full board_ingest integration run. It verifies and
loads the two whole published modules, creates a temporary Git history, uses
real merge-base ancestry, and measures actual HTML and JSON output. No network,
source patching, mocked renderer, or changes to a user's checkout are involved.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

HEAD = 'fad7e3dbbc61dc4f110395c408c8a9fe1c0629ad'
BLOBS = {'chunk_board.py': 'fda86b05c83714aa47dddd547992d865acb2d6a5',
         'completion_projection.py': '0700a3459d6adb12eb494cf4a8d156c78588d97c'}
DONE = 'THALWEG-COMPLETE-20260918'
OPEN = 'THALWEG-OPENWORK-20260918'
HIDDEN = 'THALWEG-HIDDEN-20260918'
BODY = 'Fictional completed work retained as historical evidence.'
CHROME = {'css': '', 'board_js': '', 'doors': ''}


def load(root, name):
    path = root / (name + '.py')
    raw = path.read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if actual != BLOBS[path.name]:
        raise RuntimeError('Published source mismatch: ' + path.name)
    spec = importlib.util.spec_from_file_location('thalweg_probe_' + name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Module unavailable: ' + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root, *args, expected=0):
    env = dict(os.environ, GIT_AUTHOR_NAME='Synthetic fixture',
               GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Synthetic fixture',
               GIT_COMMITTER_EMAIL='fixture@example.invalid',
               GIT_AUTHOR_DATE='2026-09-18T12:00:00Z',
               GIT_COMMITTER_DATE='2026-09-18T12:00:00Z')
    result = subprocess.run(['git', '-C', str(root), *args], env=env,
                            capture_output=True, text=True, timeout=20, check=False)
    if expected is not None and result.returncode != expected:
        raise RuntimeError('Git fixture failure: ' + result.stderr)
    return result


def case(chunk, completion, name, *, current_writer=False):
    with tempfile.TemporaryDirectory(prefix='thalweg-chunk-') as tmp:
        root = Path(tmp)
        (root / 'p').mkdir()
        source = root / 'p' / (DONE + '.md')
        source.write_text('---\nfrom: UNSEATED\nto: TABLE\nid: ' + DONE + '\n---\n' + BODY + '\n', encoding='utf-8')
        git(root, 'init', '--quiet', '--initial-branch=main')
        git(root, 'add', 'p')
        git(root, 'commit', '--quiet', '-m', 'Synthetic completed work; not provider evidence')
        merge = git(root, 'rev-parse', 'HEAD').stdout.strip()
        def ancestor(sha):
            return git(root, 'merge-base', '--is-ancestor', sha, 'HEAD', expected=None).returncode == 0
        issue = {'number': 1, 'title': DONE, 'body': 'Operation: ' + DONE,
                 'state': 'closed', 'state_reason': 'completed',
                 'closed_at': '2026-09-18T12:00:01Z',
                 'html_url': 'https://github.com/woahwhattheheck/commons/issues/1'}
        pull = {'number': 2, 'merged': True, 'base': {'ref': 'main'},
                'merged_at': '2026-09-18T12:00:00Z', 'merge_commit_sha': merge,
                'body': 'Closes #1.',
                'html_url': 'https://github.com/woahwhattheheck/commons/pull/2'}
        marker = completion.build_marker(root, DONE, issue, pull)
        completion.write_marker(root, marker, ancestor)
        common = {'from': 'UNSEATED', 'to': 'TABLE', 'ts': '2026-09-18T12:00:00Z'}
        records = [dict(common, id=DONE, body=BODY, completed='1', completion_marker=completion.marker_rel(DONE)),
                   dict(common, id=OPEN, body='Fictional unfinished work'),
                   dict(common, id=HIDDEN, body='', hidden='1')]
        if name == 'reopened_stale_history_flag':
            completion.remove_markers_for_issue(root, 1)
        elif name == 'source_drift':
            source.write_bytes(source.read_bytes() + b'\nnew evidence\n')
        elif name == 'nonancestor_marker':
            marker['merge']['merge_commit_sha'] = '0' * 40
            (root / completion.marker_rel(DONE)).write_text(json.dumps(marker), encoding='utf-8')
        elif name == 'other_route':
            records[0]['to'] = 'COURT'
        elif name == 'named_sender':
            records[0]['from'] = 'PLAYER1'
        elif name == 'moderated_completed':
            records[0]['hidden'] = '1'
            records[0]['body'] = ''
        elif name != 'verified_completion':
            raise RuntimeError('Unknown case: ' + name)
        history = json.dumps(records, sort_keys=True).encode()
        (root / 'posts.json').write_bytes(history)
        before_source = source.read_bytes()
        verified = completion.completed_operation_ids(root, ancestor)
        projected = [r for r in records if not completion.is_completed_actionable(r, verified)]
        expected_ids = sorted(r['id'] for r in chunk.visible_feed(projected))
        # Exactly the unprojected input road used by chunk_board.main(): load
        # persisted full posts.json, call the unchanged production thin writer.
        persisted = json.loads((root / 'posts.json').read_bytes())
        snapshot = copy.deepcopy(persisted)
        if current_writer:
            index = chunk.write_current_thin_board(persisted, str(root), CHROME, ancestor)
        else:
            index = chunk.write_thin_board(persisted, str(root), CHROME)
        actual_ids = sorted(r['id'] for path in (root / 'chunks').glob('*/p*.json')
                            for r in json.loads(path.read_bytes()))
        html = (root / 'board.html').read_text(encoding='utf-8')
        if persisted != snapshot or source.read_bytes() != before_source or (root / 'posts.json').read_bytes() != history:
            raise RuntimeError('Source/history input mutation')
        if index['n'] != len(actual_ids):
            raise RuntimeError('Index and actual chunk count differ')
        return {'case': name, 'verified_ids': sorted(verified), 'expected_active_ids': expected_ids,
                'actual_chunk_ids': actual_ids, 'completed_body_in_html': BODY in html,
                'projection_agrees': expected_ids == actual_ids,
                'history_and_input_unchanged': True, 'real_git_ancestry': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--require-fixed', action='store_true', help='exit 1 when any projection disagrees')
    args = parser.parse_args()
    chunk = load(args.root.resolve(), 'chunk_board')
    completion = load(args.root.resolve(), 'completion_projection')
    cases = [case(chunk, completion, name) for name in (
        'verified_completion', 'reopened_stale_history_flag', 'source_drift',
        'nonancestor_marker', 'other_route', 'named_sender', 'moderated_completed')]
    failures = [r['case'] for r in cases if not r['projection_agrees']]
    print(json.dumps({'source_head': HEAD, 'source_blobs': BLOBS,
                      'state': 'DEFECT_REPRODUCED' if failures else 'NO_DISAGREEMENT_OBSERVED',
                      'mismatches': failures, 'cases': cases,
                      'limits': ['Real thin-renderer/component run, not full board_ingest import or four-suite execution.',
                                 'Provider metadata is synthetic; ancestry checks use an actual temporary Git repository.',
                                 'Cached completed flags must not replace current marker validation.']}, indent=2))
    if args.require_fixed and failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
