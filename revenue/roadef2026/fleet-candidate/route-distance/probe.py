#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile exact transition-cost methods and compare source-bound behavior.

This is a method-level differential/benchmark, not a solver or official-checker
performance result. --candidate takes the full solver source (or one method).
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
SIGNATURE = '    int distance(int d, const Route& a, const Route& b) const {'

def extract(source: str) -> str:
    if source.count(SIGNATURE) != 1:
        raise ValueError('Expected exactly one Solver::distance method')
    start = source.index(SIGNATURE)
    depth = 1
    offset = start + len(SIGNATURE)
    while offset < len(source) and depth:
        depth += (source[offset] == '{') - (source[offset] == '}')
        offset += 1
    if depth:
        raise ValueError('Incomplete distance method')
    return source[start:offset] + '\n'

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=HERE.parent/'main.cpp')
    parser.add_argument('--compiler', default='g++')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=10)
    parser.add_argument('--sanitizers', action='store_true')
    parser.add_argument('--allocations', action='store_true', help='Count allocations in a separate non-timed run')
    args = parser.parse_args()
    if not 0 <= args.repetitions <= 10000:
        parser.error('repetitions must be between 0 and 10000')
    if args.allocations and args.repetitions:
        parser.error('allocation instrumentation requires --repetitions 0')
    source = args.candidate.read_bytes()
    original = (HERE/'distance_original.inc').read_bytes()
    candidate = extract(source.decode())
    expected = original.decode().replace('        if (a == b) return 0;\n',
        '        if (a == b) return 0;\n'+(HERE/'fast_path.inc').read_text(), 1)
    if candidate != expected:
        raise ValueError('Candidate differs from the scoped early fast-path insertion')
    flags = ['-std=c++20', '-Wall', '-Wextra', '-Werror', '-Wno-mismatched-new-delete']
    flags += ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer'] if args.sanitizers else ['-O3','-DNDEBUG']
    if args.allocations:
        flags.append('-DROADEF_COUNT_ALLOCATIONS')
    with tempfile.TemporaryDirectory(prefix='roadef-distance-') as tmp:
        root = Path(tmp)
        (root/'old_method.inc').write_bytes(original)
        (root/'new_method.inc').write_text(candidate)
        binary = root/'probe'
        compile_result = subprocess.run([args.compiler,*flags,'-I',str(root),str(HERE/'probe.cpp'),'-o',str(binary)],
            capture_output=True,text=True,timeout=90)
        if compile_result.returncode:
            raise RuntimeError(compile_result.stderr)
        binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
        result = subprocess.run([str(binary),str(args.repetitions)],capture_output=True,text=True,timeout=90)
        if result.returncode:
            raise RuntimeError(f'Probe exit {result.returncode}: {result.stderr}')
        report = json.loads(result.stdout)
        report.update(allocation_instrumentation=args.allocations,source_sha256=hashlib.sha256(source).hexdigest(),
                      method_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
                      original_method_sha256=hashlib.sha256(original).hexdigest(),
                      harness_sha256=hashlib.sha256((HERE/'probe.cpp').read_bytes()).hexdigest(),
                      binary_sha256=binary_sha,flags=flags,
                      compiler=subprocess.check_output([args.compiler,'--version'],text=True).splitlines()[0],
                      platform=platform.platform(),python=platform.python_version(),
                      stderr=result.stderr,scope='extracted exact method; no full solver or official checker run')
        if report['rounds']:
            a=statistics.median(r['original_seconds'] for r in report['rounds'])
            b=statistics.median(r['candidate_seconds'] for r in report['rounds'])
            report.update(original_median_seconds=a,candidate_median_seconds=b,median_reduction_percent=100*(1-b/a))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k!='rounds'},indent=2))

if __name__=='__main__':
    main()
