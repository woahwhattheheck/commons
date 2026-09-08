# SPDX-License-Identifier: Apache-2.0
"""Run the new integration checks and cold actors from a relocated exact archive."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,tempfile
ROOT=Path(__file__).resolve().parent
RUN=r'''
import sys,pathlib,runpy,json,time,copy
root=pathlib.Path(sys.argv[1]);sys.path.insert(0,str(root));sys.path.insert(1,str(root/'checks'))
def offline(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):raise RuntimeError('offline test')
sys.addaudithook(offline)
if sys.argv[2]=='boundaries':
 try:runpy.run_path(str(root/'checks/test_terminal_history_join.py'),run_name='__main__')
 except SystemExit as e:
  if e.code:raise
elif sys.argv[2]=='fixture':
 from test_ordered_selected_sell import OrderedSelectedSellTests
 OrderedSelectedSellTests.setUpClass();h=OrderedSelectedSellTests();obs,cfg,_,_=h.fixture(0)
 print(json.dumps({'observation':obs,'configuration':cfg}))
else:
 d=json.loads(pathlib.Path(sys.argv[3]).read_text());t=time.perf_counter()
 if sys.argv[2]=='cold_default':
  import main
  out=main.agent(d['observation'],d['configuration']);diag=main._INSTANCE.diagnostics
 else:
  from titan_runtime import TitanAgent,Features
  obj=TitanAgent(Features(**json.loads((root/'TITAN-HISTORY-CONFIG.json').read_text())))
  out=obj.act(d['observation'],d['configuration']);diag=obj.diagnostics
 elapsed=time.perf_counter()-t
 assert elapsed<1 and diag['parent_calls']==1
 print(json.dumps({'case':sys.argv[2],'seconds':elapsed,'action':out,'diagnostics':diag}))
for mod in list(sys.modules.values()):
 p=getattr(mod,'__file__',None)
 if p and '/commons-work/' in p:raise AssertionError('original repository import '+p)
'''

def main():
 archive=ROOT/'exports/titan-history-v2.tar.gz'
 assert hashlib.sha256((ROOT/'exports/titan-current.tar.gz').read_bytes()).hexdigest()=='70554dc01f8e84336ede169cf109f3d61152e169dce8ad5265b9625216fe52cb'
 result={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'new_games':0,'cold_actions':[]}
 with tempfile.TemporaryDirectory(prefix='titan-history-clean-',dir='/tmp') as folder:
  w=Path(folder);r=w/'candidate';r.mkdir()
  with tarfile.open(archive) as t:t.extractall(r,filter='data')
  source=(r/'SOURCE.json').read_bytes();result['source_manifest_sha256']=hashlib.sha256(source).hexdigest()
  for p,row in json.loads(source)['runtime'].items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==row['sha256']
  worker=w/'run.py';worker.write_text(RUN)
  def run(mode,*args):
   p=subprocess.run([sys.executable,'-I',str(worker),str(r),mode,*args],cwd=w,capture_output=True,text=True,timeout=15)
   if p.returncode:raise RuntimeError(p.stdout+p.stderr)
   return p
  check=run('boundaries');result['boundaries']=json.loads((r/'checks/runtime/integrated-selected/HISTORY-TESTS.json').read_text())
  fixture=w/'fixture.json';fixture.write_text(run('fixture').stdout)
  for mode in ('cold_default','cold_history'):result['cold_actions'].append(json.loads(run(mode,str(fixture)).stdout))
  result['identical_first_action']=result['cold_actions'][0]['action']==result['cold_actions'][1]['action']
  assert result['identical_first_action']
 result['max_cold_seconds']=max(x['seconds'] for x in result['cold_actions'])
 result['episode_allowance']='No full game run here; exact version/config to Claude/WIDEFIELD for separate panel.'
 (ROOT/'runtime/integrated-selected/HISTORY-ARCHIVE-TESTS.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'archive':result['archive_sha256'],'tests':result['boundaries']['tests'],'max_cold_seconds':result['max_cold_seconds'],'offline':True}))
if __name__=='__main__':main()
