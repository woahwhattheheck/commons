from __future__ import annotations
import copy, os, subprocess, tempfile, unittest
from pathlib import Path
from host.context_packet import DIGEST_KEY, canonical, digest, verify_packet, PacketError
from host.context_sources import attach_sources, capture_sources, markdown_with_sources

def run(repo,*args,input=None):
    return subprocess.run(['git','-C',str(repo),*args],input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout.decode().strip()

def packet(max_chars=6000):
    p={'schema':'commons-context-packet/v1','operation':'op','objective':'obj','limits':{'max_chars':max_chars},'omitted':{},'claims':[],'coordination':[],'recent':[],'resources':[],'provenance':[]}
    p[DIGEST_KEY]=digest(p)
    return p

class Tests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(); self.repo=Path(self.td.name)
        run(self.repo,'init','-q'); run(self.repo,'config','user.email','x@example.com'); run(self.repo,'config','user.name','x')
        (self.repo/'a.txt').write_text('alpha\n',encoding='utf-8')
        (self.repo/'b.py').write_text('print("beta")\n',encoding='utf-8')
        run(self.repo,'add','.'); run(self.repo,'commit','-qm','one')
        self.head=run(self.repo,'rev-parse','HEAD')
    def tearDown(self): self.td.cleanup()
    def test_exact_commit_ignores_worktree_and_order(self):
        (self.repo/'a.txt').write_text('WORKTREE\n',encoding='utf-8')
        x=capture_sources(self.repo,self.head,['b.py','a.txt'])
        y=capture_sources(self.repo,self.head,['a.txt','b.py','a.txt'])
        self.assertEqual(x,y); self.assertEqual([c['path'] for c in x['capsules']],['a.txt','b.py'])
        self.assertEqual(x['capsules'][0]['text'],'alpha\n')
    def test_symlink_missing_traversal_and_noncommit_fail(self):
        os.symlink('a.txt',self.repo/'link'); run(self.repo,'add','link'); run(self.repo,'commit','-qm','link'); head=run(self.repo,'rev-parse','HEAD')
        with self.assertRaises(PacketError): capture_sources(self.repo,head,['link'])
        with self.assertRaises(PacketError): capture_sources(self.repo,head,['missing'])
        with self.assertRaises(PacketError): capture_sources(self.repo,head,['../a.txt'])
        blob=run(self.repo,'rev-parse',f'{head}:a.txt')
        with self.assertRaises(PacketError): capture_sources(self.repo,blob,['a.txt'])
    def test_binary_and_large_are_explicit_omissions(self):
        (self.repo/'bin.dat').write_bytes(b'a\x00b'); (self.repo/'large.txt').write_text('x'*100,encoding='utf-8')
        run(self.repo,'add','.'); run(self.repo,'commit','-qm','more'); head=run(self.repo,'rev-parse','HEAD')
        c=capture_sources(self.repo,head,['bin.dat','large.txt'],max_file_bytes=50)
        reasons={x['path']:x['reason'] for x in c['omitted']}
        self.assertEqual(reasons,{'bin.dat':'non_text','large.txt':'file_too_large'})
    def test_excerpt_is_explicit(self):
        c=capture_sources(self.repo,self.head,['b.py'],max_excerpt_chars=5)
        row=c['capsules'][0]; self.assertFalse(row['text_complete']); self.assertGreater(row['omitted_text_chars'],0); self.assertEqual(row['text'],'print')
    def test_attach_hard_budget_tamper_and_markdown(self):
        c=capture_sources(self.repo,self.head,['a.txt','b.py'])
        p=attach_sources(packet(3000),c,max_chars=3000)
        self.assertLessEqual(len(canonical(p)),3000); self.assertTrue(verify_packet(p)[0]); self.assertIn('Exact Git source capsules',markdown_with_sources(p))
        q=copy.deepcopy(p); q['source_context']['commit']='0'*40
        self.assertEqual(verify_packet(q)[0],False)
    def test_budget_omission_is_explicit(self):
        (self.repo/'huge.txt').write_text('q'*5000,encoding='utf-8'); run(self.repo,'add','.'); run(self.repo,'commit','-qm','huge'); head=run(self.repo,'rev-parse','HEAD')
        c=capture_sources(self.repo,head,['a.txt','huge.txt'],max_file_bytes=6000,max_excerpt_chars=3000)
        p=attach_sources(packet(2048),c,max_chars=2048)
        self.assertLessEqual(len(canonical(p)),2048); self.assertGreaterEqual(p['source_context']['omitted_by_reason'].get('packet_budget',0),1)
    def test_bad_commit_and_limits(self):
        for bad in ['HEAD','A'*40,'a'*39]:
            with self.assertRaises(PacketError): capture_sources(self.repo,bad,['a.txt'])
        with self.assertRaises(PacketError): capture_sources(self.repo,self.head,[])

if __name__=='__main__': unittest.main()
