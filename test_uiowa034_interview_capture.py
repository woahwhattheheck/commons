"""Root discovery bridge for the isolated interview capture component."""
from pathlib import Path
import os
import re
import subprocess
import sys
import unittest


class InterviewCaptureSuite(unittest.TestCase):
    def test_component_normal_and_optimized(self):
        lane=Path(__file__).parent/'revenue/uiowa_rfq_18649_interview_adapter'
        env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
        env['PYTHONDONTWRITEBYTECODE']='1'
        for flags in ([],['-O']):
            with self.subTest(flags=flags):
                proc=subprocess.run([sys.executable,*flags,'-m','unittest','discover','-v'],
                    cwd=lane,env=env,capture_output=True,text=True,timeout=60)
                transcript=proc.stdout+proc.stderr
                self.assertEqual(proc.returncode,0,transcript)
                count=re.search(r'Ran (\d+) tests?',transcript)
                self.assertIsNotNone(count,transcript)
                self.assertGreaterEqual(int(count.group(1)),51)
                self.assertNotIn('OK (skipped=',transcript)


if __name__=='__main__':unittest.main()
