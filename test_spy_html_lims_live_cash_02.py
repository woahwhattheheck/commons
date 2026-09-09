import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['ats-asphalt-spec-result-lims.html', 'baddl-eia-accession-release-lims.html', 'clark-d4172-proficiency-lims.html', 'eagletrax-split-sample-preflight-lims.html', 'elevatebio-pittsburgh-replication-lims.html']
class X(unittest.TestCase):
    def test_all(self):
        for rel in FILES:
            t=(ROOT/rel).read_text(); self.assertIn('id="live-cash"', t, rel); self.assertIn('agent-rescue.html', t, rel)
if __name__=='__main__':
    unittest.main()
