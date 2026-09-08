#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Source-bound compiled controls for the route distance fast path.

No external libraries or solver instance are needed. This tests the extracted
method on repeated/degenerate paths as well as valid lengths; it is not an
independent competition benchmark. Use --candidate for the actual full source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from probe import extract

HERE = Path(__file__).resolve().parent
CONFIG = None

class DistanceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = (HERE / 'distance_original.inc').read_text()
        cls.new = extract(CONFIG.candidate.read_text())
        cls.prefix = (HERE / 'fast_path.inc').read_text()
        cls.records = []

    def run_source(self, name, source, good):
        with tempfile.TemporaryDirectory(prefix='route-cost-control-') as directory:
            root = Path(directory)
            (root/'old_method.inc').write_text(self.old)
            (root/'new_method.inc').write_text(source)
            command=[CONFIG.compiler,'-std=c++20','-O2','-Wall','-Wextra',
                     '-I',str(root),str(HERE/'probe.cpp'),'-o',str(root/'probe')]
            compiled = subprocess.run(command,capture_output=True,text=True,timeout=60)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            # Retain crashes as child evidence; do not create core files.
            env=dict(os.environ)
            process=subprocess.run([str(root/'probe'),'0'],capture_output=True,text=True,
                                   timeout=30,env=env)
            record={'name':name,'method_sha256':hashlib.sha256(source.encode()).hexdigest(),
                    'returncode':process.returncode,'stdout':process.stdout,'stderr':process.stderr}
            self.records.append(record)
            if good:
                self.assertEqual(process.returncode,0,process.stderr)
                report=json.loads(process.stdout)
                self.assertEqual(report['comparisons'],137600)
                self.assertEqual(report['checksum'],786075)
            else:
                self.assertNotEqual(process.returncode,0)
                self.assertIn('distance mismatch at case',process.stderr)

    def test_scoped_insertion_only(self):
        expected=self.old.replace('        if (a == b) return 0;\n',
                                 '        if (a == b) return 0;\n'+self.prefix,1)
        self.assertEqual(self.new,expected)

    def test_original_matches_independent_oracle(self):
        self.run_source('unchanged-original',self.old,True)

    def test_candidate_matches_independent_oracle(self):
        self.run_source('exact-candidate',self.new,True)

    def test_duplicate_segment_mutation_detected(self):
        token='if (j == count) out[count++] = value;'
        self.assertEqual(self.new.count(token),1)
        self.run_source('count-duplicates',self.new.replace(token,'out[count++] = value;'),False)

    def test_undirected_segment_mutation_detected(self):
        token='Segment value{from, to};'
        self.assertEqual(self.new.count(token),1)
        self.run_source('lose-direction',self.new.replace(token,
            'Segment value{std::min(from,to), std::max(from,to)};'),False)

    def test_final_segment_mutation_detected(self):
        token='                append(demands[d].to);'
        self.assertEqual(self.new.count(token),1)
        self.run_source('omit-final-segment',self.new.replace(token,'                // final segment omitted'),False)

    def test_general_length_fallback_mutation_detected(self):
        token='        auto segments = [&](const Route& path) {'
        self.assertEqual(self.new.count(token),1)
        self.run_source('disable-general-fallback',self.new.replace(token,'        return 0;\n'+token),False)


def main():
    global CONFIG
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=HERE.parent/'main.cpp')
    parser.add_argument('--compiler',default='g++')
    parser.add_argument('--report',type=Path,required=True)
    CONFIG=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(DistanceControls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'methods':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'successful':result.wasSuccessful(),'compiler':subprocess.check_output([CONFIG.compiler,'--version'],text=True).splitlines()[0],
            'candidate_source_sha256':hashlib.sha256(CONFIG.candidate.read_bytes()).hexdigest(),
            'harness_sha256':hashlib.sha256((HERE/'probe.cpp').read_bytes()).hexdigest(),
            'records':DistanceControls.records,'scope':'compiled method controls; no full solver/checker execution'}
    CONFIG.report.parent.mkdir(parents=True,exist_ok=True)
    CONFIG.report.write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':
    main()
