# SPDX-License-Identifier: Apache-2.0
import hashlib, tempfile, unittest
from pathlib import Path
import compose_h3s420_current as c

class H3S420CurrentAbiTests(unittest.TestCase):
    def test_git_blob_hash(self):
        raw=b"hello\n"; self.assertEqual(c.git_blob_sha(raw),hashlib.sha1(b"blob 6\0"+raw).hexdigest())
    def test_scheduler_changes_only_named_horizon(self):
        src="A=1\n"+c.SCHEDULER_OLD+"B=2\n"; self.assertEqual(c.transform_scheduler(src),"A=1\n"+c.SCHEDULER_NEW+"B=2\n")
    def test_scheduler_anchor_fails_closed(self):
        with self.assertRaises(ValueError): c.transform_scheduler("HORIZON = 7\n")
        with self.assertRaises(ValueError): c.transform_scheduler(c.SCHEDULER_OLD+c.SCHEDULER_OLD)
    def test_guard_exact_boundary_and_direction(self):
        i={}
        self.assertFalse(c.should_suppress_late_pull_forward(419,((419,4),),((419,1),),i))
        self.assertTrue(c.should_suppress_late_pull_forward(420,((420,4),),((420,1),),i))
        self.assertFalse(c.should_suppress_late_pull_forward(420,((420,1),),((420,1),),i))
        self.assertFalse(c.should_suppress_late_pull_forward(420,((420,0),),((420,1),),i))
        self.assertFalse(c.should_suppress_late_pull_forward(420,((420,1),(423,4)),((420,1),(421,4)),i))
    def test_forced_feasibility_is_preserved(self):
        self.assertFalse(c.should_suppress_late_pull_forward(700,((700,9),),((700,0),),{"forced_feasibility":True}))
    def test_frozen_transform_injects_one_guard_and_one_call(self):
        src="prefix"+c.CLASS_ANCHOR+"body\n"+c.FROZEN_ANCHOR+"suffix"; out=c.transform_frozen(src)
        self.assertEqual(out.count("def _h3s420_suppress("),1); self.assertEqual(out.count("if _h3s420_suppress(now,plan,reference,info):"),1)
        self.assertEqual(out.count("acceptance_rule']='h3s420_no_late_pull_forward'"),1)
    def test_frozen_anchor_fails_closed(self):
        with self.assertRaises(ValueError): c.transform_frozen("no anchors")
    def test_compose_paths_refuses_unpinned_sources(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); s=d/"scheduler.py"; f=d/"frozen_selected.py"; s.write_text(c.SCHEDULER_OLD); f.write_text(c.CLASS_ANCHOR+c.FROZEN_ANCHOR)
            with self.assertRaisesRegex(ValueError,"scheduler Git blob mismatch"): c.compose_paths(s,f,d/"out")
if __name__=="__main__": unittest.main()
