# SPDX-License-Identifier: Apache-2.0
"""Offline serial replay of every declared cell, with a fresh process per arm."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import run_wf1_replay as r

HERE = Path(__file__).resolve().parent

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, default=HERE/'runtime-fixture')
    parser.add_argument('--tapes', type=Path, default=HERE/'tapes')
    parser.add_argument('--panel', type=Path, default=HERE/'replay-capacity-evidence/PANEL.json')
    parser.add_argument('--lock', type=Path, default=HERE/'replay-capacity-evidence/SOURCE-LOCK.json')
    parser.add_argument('--output', type=Path, help='A new directory; existing output is never reused.')
    parser.add_argument('--check-inputs', action='store_true', help='Verify every input without playing games.')
    args = parser.parse_args()
    try:
        panel = r.read_json(args.panel)
        r.require(panel.get('schema') == 'wf1-declared-replay-panel/v1', 'wrong panel schema')
        r.require(panel.get('arms') == ['recorded', 'off', 'on'], 'panel arms differ')
        cells = panel.get('cells')
        r.require(type(cells) is list and bool(cells), 'empty declared panel')
        lock = r.read_json(args.lock)
        r.require(lock.get('schema') == 'wf1-replay-source-lock/v1', 'wrong source lock schema')
        r.require(lock.get('seam') == r.SEAM, 'wrong seam')
        r.verify_files(args.runtime, lock.get('runtime'))
        r.verify_files(HERE, lock.get('wf1'))
        r.load_engine(args.runtime)  # Hash gate precedes loader; no downloads.
        seen = set()
        for cell in cells:
            episode = cell.get('episode')
            r.require(type(episode) is int and episode > 0 and episode not in seen,
                      'invalid or duplicate episode')
            seen.add(episode)
            r.seat_value(cell.get('candidate_seat'))
            r.require(cell.get('tape') == f'{episode}.json', 'unexpected tape path')
            tape_path = args.tapes / cell['tape']
            r.require(tape_path.is_file() and not tape_path.is_symlink(), 'missing/nonregular tape')
            r.require(r.sha256(tape_path.read_bytes()) == cell.get('tape_sha256'), 'tape hash mismatch')
            tape = r.read_json(tape_path)
            r.validate_tape(tape)
            r.require(tape['id'] == episode and tape['seed'] == cell.get('seed'), 'wrong tape identity')
            r.require(tape['names'] == cell.get('names'), 'wrong team names')
            r.require(cell.get('pinned_opponent_seat') == 1-cell['candidate_seat'], 'wrong opponent seat')
            r.require(type(cell.get('self_play')) is bool and
                      cell['self_play'] == (tape['names'][0] == tape['names'][1]), 'wrong self-play label')
        print(f'INPUTS VERIFIED: {len(cells)} declared cells; exact source and engine locks.', flush=True)
        if args.check_inputs:
            return 0
        r.require(args.output is not None, '--output is required to play the panel')
        r.require(not args.output.exists(), 'output already exists; refusing to mix runs')
        args.output.mkdir(parents=True, exist_ok=False)
        completed = []
        for cell in cells:
            episode = cell['episode']
            for arm in panel['arms']:
                command = [sys.executable, str(HERE/'run_wf1_replay.py'),
                           '--runtime', str(args.runtime), '--lock', str(args.lock),
                           '--tape', str(args.tapes/cell['tape']), '--arm', arm,
                           '--candidate-seat', str(cell['candidate_seat']),
                           '--output', str(args.output/f'{episode}-{arm}.json')]
                if arm != 'recorded':
                    command += ['--control', str(args.output/f'{episode}-recorded.json')]
                # This is an outer experiment watchdog, not a change to the
                # unmodified parent's one-second per-callback deadline.
                subprocess.run(command, check=True, timeout=120, stdin=subprocess.DEVNULL)
            off = r.read_json(args.output/f'{episode}-off.json')
            on = r.read_json(args.output/f'{episode}-on.json')
            completed.append(r.paired_delta(off, on))
        (args.output/'PAIRS.json').write_text(json.dumps(completed, sort_keys=True, indent=2)+'\n')
        print(f'COMPLETE: {len(completed)} paired cells plus recorded controls. No promotion authority.')
        return 0
    except (r.EvidenceError, OSError, json.JSONDecodeError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f'FAILED CLOSED: {error}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
