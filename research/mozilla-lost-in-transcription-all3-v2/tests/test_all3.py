import json, tempfile, unittest, zipfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from core import *
from priors import build as build_priors
from experiment import run as run_experiment
from pack import build as build_pack, verify
from readiness import aggregate
from profile_runtime import profile

class CoreTests(unittest.TestCase):
    def test_unicode_normalize(self): self.assertEqual(normalize_transcript("  Á—B  O’Neil! "), "á b o'neil")
    def test_combining_marks_normalize(self): self.assertEqual(normalize_transcript("A\u0304"), "ā")
    def test_wer(self): self.assertEqual(corpus_wer(["a b"],["a c"]),0.5)
    def test_empty_ref(self): self.assertEqual(corpus_wer([""],[""]),0.0)
    def test_mismatched_len(self):
        with self.assertRaises(ValueError): corpus_wer(["a"],[])
    def test_evidence_rejects_unknown_class(self):
        with self.assertRaises(ValueError): TranscriptEvidence("sp-en","a","private_competition","x").validate()
    def test_evidence_rejects_track(self):
        with self.assertRaises(ValueError): TranscriptEvidence("xx","a","synthetic","x").validate()
    def test_prior_track_bound(self):
        rows=[TranscriptEvidence("sp-en","a b","synthetic","x")]
        p=TrackPrior.fit("sp-en",rows)
        self.assertEqual(p.track,"sp-en"); self.assertEqual(p.transcript_count,1)
    def test_prior_no_rows(self):
        with self.assertRaises(ValueError): TrackPrior.fit("sp-en",[])
    def test_consensus_deterministic(self):
        hs=[Hypothesis("a b","x",0),Hypothesis("a c","y",1),Hypothesis("a b","z",2)]
        a=choose_consensus("sp-en",hs); b=choose_consensus("sp-en",hs)
        self.assertEqual(a.evidence_sha256,b.evidence_sha256); self.assertEqual(a.text,"a b")
    def test_consensus_prior_mismatch(self):
        p=TrackPrior.fit("id-jv",[TranscriptEvidence("id-jv","a b","synthetic","x")])
        with self.assertRaises(ValueError): choose_consensus("sp-en",[Hypothesis("a b","x"),Hypothesis("a c","y")],prior=p)
    def test_consensus_requires_two(self):
        with self.assertRaises(ValueError): choose_consensus("sp-en",[Hypothesis("a","x")])
    def test_tie_abstains(self):
        r=choose_consensus("sp-en",[Hypothesis("a b","x",0),Hypothesis("a c","y",0)],config=ConsensusConfig(margin_abstain=1.0))
        self.assertTrue(r.abstain)

class PipelineTests(unittest.TestCase):
    def test_prior_and_experiment(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); pri=d/'p.json'; rep=d/'r.json'
            payload=build_priors(ROOT/'fixtures/prior_evidence.jsonl',pri)
            self.assertEqual(set(payload['priors']),set(TRACKS))
            report=run_experiment(ROOT/'fixtures/experiment.jsonl',rep,pri)
            self.assertEqual(set(report['tracks']),set(TRACKS)); self.assertEqual(report['tracks']['sp-en']['consensus_wer'],0.0)
    def _source(self,d:Path,track='sp-en') -> Path:
        s=d/'src'; s.mkdir()
        for f in ('core.py','profiles.json','runtime_contract.json'):
            (s/f).write_bytes((ROOT/f).read_bytes())
        (s/'main.py').write_text("print('offline')\n")
        (s/'model_config.json').write_text(json.dumps({'track':track,'models':[{'name':'a'},{'name':'b'}]}))
        return s
    def test_pack_reproducible_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); s=self._source(d); z1=d/'a.zip'; r1=d/'a.json'; z2=d/'b.zip'; r2=d/'b.json'
            build_pack(s,'sp-en',z1,r1); build_pack(s,'sp-en',z2,r2)
            self.assertEqual(z1.read_bytes(),z2.read_bytes()); self.assertTrue(verify(z1,r1))
    def test_pack_reject_network_import(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); s=self._source(d); (s/'bad.py').write_text('import requests\n')
            with self.assertRaises(ValueError): build_pack(s,'sp-en',d/'a.zip',d/'a.json')
    def test_pack_reject_network_literal(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); s=self._source(d); (s/'bad.py').write_text("X='https://example.com'\n")
            with self.assertRaises(ValueError): build_pack(s,'sp-en',d/'a.zip',d/'a.json')
    def test_pack_reject_oversize(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); s=self._source(d)
            with self.assertRaises(ValueError): build_pack(s,'sp-en',d/'a.zip',d/'a.json',max_bytes=1)
    def test_verify_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); s=self._source(d); z=d/'a.zip'; r=d/'a.json'; build_pack(s,'sp-en',z,r); z.write_bytes(z.read_bytes()+b'x'); self.assertFalse(verify(z,r))
    def test_readiness_all_three(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); receipts=[]
            for t in sorted(TRACKS):
                p=d/f'{t}.json'; p.write_text(json.dumps({'track':t,'accepted':True,'runtime_commit':'abc','internet_at_execution':False,'bundle_sha256':t})); receipts.append(p)
            out=d/'ready.json'; result=aggregate(receipts,out)
            self.assertEqual(result['state'],'ALL_THREE_LOCAL_BUNDLES_STRUCTURALLY_READY'); self.assertFalse(result['provider_submission'])
    def test_readiness_duplicate_track_holds(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); paths=[]
            for i,t in enumerate(('sp-en','sp-en','id-jv')):
                p=d/f'{i}.json'; p.write_text(json.dumps({'track':t,'accepted':True,'runtime_commit':'abc','internet_at_execution':False,'bundle_sha256':str(i)})); paths.append(p)
            result=aggregate(paths,d/'r.json'); self.assertEqual(result['state'],'HOLD')
    def test_runtime_profiler_accepts_bounded_smoke(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'p.json'; r=profile([sys.executable,'-c','print(42)'],out,timeout_s=3,max_wall_s=3,max_rss_mib=4096)
            self.assertTrue(r['accepted']); self.assertEqual(r['returncode'],0)
    def test_runtime_profiler_rejects_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'p.json'; r=profile([sys.executable,'-c','raise SystemExit(7)'],out,timeout_s=3,max_wall_s=3,max_rss_mib=4096)
            self.assertFalse(r['accepted']); self.assertEqual(r['returncode'],7)
    def test_readiness_runtime_mismatch_holds(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); paths=[]
            for i,t in enumerate(sorted(TRACKS)):
                p=d/f'{i}.json'; p.write_text(json.dumps({'track':t,'accepted':True,'runtime_commit':str(i),'internet_at_execution':False,'bundle_sha256':str(i)})); paths.append(p)
            self.assertEqual(aggregate(paths,d/'r.json')['state'],'HOLD')

if __name__=='__main__': unittest.main()
