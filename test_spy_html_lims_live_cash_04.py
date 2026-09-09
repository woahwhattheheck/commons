import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['qlabs-qconnect-cutover-verification-lims.html', 'rosecity-olcc-metrc-sampling-lims.html', 'roslinct-hopkinton-paperless-qc-lims.html', 'sharp-rtu-vial-isolator-lineage-lims.html', 'slo-cls-cutover-evidence-lims.html']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('id="live-cash"', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
