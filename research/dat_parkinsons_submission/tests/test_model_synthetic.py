import unittest, tempfile
import numpy as np
import torch
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'submission_src'))
from datpark.model import DaTNet3d
from datpark.preprocess import PreprocessConfig, foreground_crop, robust_normalize, resize_trilinear
class SyntheticModelTests(unittest.TestCase):
    def test_preprocess_and_model_forward(self):
        x=np.zeros((24,32,40),dtype=np.float32); x[5:19,8:25,10:31]=np.linspace(0,10,14*17*21,dtype=np.float32).reshape(14,17,21)
        x=foreground_crop(x,fraction=.05,margin=2); x=robust_normalize(x,lower_q=.01,upper_q=.995); x=resize_trilinear(x,(32,40,40)); self.assertEqual(x.shape,(32,40,40)); self.assertTrue(np.isfinite(x).all())
        model=DaTNet3d(width=16,dropout=.2).eval()
        with torch.no_grad(): y=model(torch.from_numpy(x)[None,None])
        self.assertEqual(tuple(y.shape),(1,)); self.assertTrue(torch.isfinite(y).all())
    def test_bundle_round_trip(self):
        from datpark.bundle import save_bundle, load_bundle
        model=DaTNet3d(width=16,dropout=.2).eval()
        with tempfile.TemporaryDirectory() as td:
            save_bundle(td,[model.state_dict()],temperatures=[1.25],preprocess=PreprocessConfig(),metadata={'synthetic':True}); models,temps,cfg,manifest=load_bundle(td,'cpu')
            self.assertEqual(len(models),1); self.assertEqual(temps,[1.25]); self.assertEqual(cfg.shape,(64,96,96)); self.assertEqual(manifest['metadata'],{'synthetic':True})
    def test_nonfinite_rejected(self):
        x=np.ones((8,8,8),dtype=np.float32); x[0,0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'NaN'): robust_normalize(x,lower_q=.01,upper_q=.99)
if __name__=='__main__': unittest.main()
