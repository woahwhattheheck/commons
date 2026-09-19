"""Enroll the real-parent HTML reader regressions in root unittest discovery."""
from pathlib import Path
import subprocess
import sys
import unittest


class HandoffReaderDiscovery(unittest.TestCase):
    def test_reader_with_actual_parent(self):
        root=Path(__file__).resolve().parent
        workbench=root/'revenue'/'uiowa_rfq_18649_workbench'
        command=[sys.executable]
        if sys.flags.optimize:
            command.append('-O')
        command += ['-m','unittest','-v','test_handoff_review_html.py']
        result=subprocess.run(command,cwd=workbench,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Ran 18 tests',result.stderr)
        self.assertNotIn('skipped=',result.stderr)


if __name__=='__main__':
    unittest.main()
