"""Hostiles for exact PR/base/merge/workflow execution authority binding."""
import copy
import inspect
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace

from host import swarm_review as sr

H='1'*40
M='2'*40
MERGE='3'*40
WF='4'*40
PATH='.github/workflows/tests.yml'
ROOT=Path(__file__).resolve().parent


def pull(number=77, base=M, merge=MERGE):
    return {'number':number,'state':'open','merged':False,'head':{'sha':H},
            'base':{'ref':'main','sha':base},'merge_commit_sha':merge,'body':''}


def assoc(number=77, base=M, merge=MERGE, head=H):
    return {'number':number,'head':{'sha':head},'base':{'ref':'main','sha':base},
            'merge_commit_sha':merge}


def run(rows=None):
    return {'id':9001,'head_sha':H,'event':'pull_request','status':'completed',
            'conclusion':'success','path':PATH,'html_url':'https://example.test/run/9001',
            'pull_requests':[] if rows is None else rows}


def job():
    return {'id':42,'name':'contract','status':'completed','conclusion':'success',
            'steps':[{'name':'Set up job','conclusion':'success'},
                     {'name':'unit','conclusion':'success'},
                     {'name':'hostile','conclusion':'success'},
                     {'name':'Complete job','conclusion':'success'}]}


class Hub:
    repo='woahwhattheheck/commons'
    def __init__(self, p=None, associations=None, runs=None, workflow_blob=WF):
        self.p=p or pull(); self.associations=[assoc()] if associations is None else associations
        self.runs=[run()] if runs is None else runs; self.workflow_blob=workflow_blob
    def rest(self,path,params=None):
        page=(params or {}).get('page',1)
        if '/commits/' in path and path.endswith('/pulls'):
            return self.associations if page==1 else []
        if path.endswith('/actions/runs'):
            return {'workflow_runs':self.runs if page==1 else []}
        if '/actions/runs/9001/jobs' in path:
            return {'jobs':[job()] if page==1 else []}
        if '/contents/' in path:
            return {'type':'file','sha':self.workflow_blob}
        if path.endswith('/pulls/77'):
            return copy.deepcopy(self.p)
        if path.endswith('/pulls/77/reviews'):
            return []
        raise AssertionError((path,params))


class Git:
    def __init__(self, blob=WF): self.blob=blob
    def run(self,*args,**kwargs):
        if args[:2]==('rev-parse','--verify'):
            return SimpleNamespace(returncode=0,stdout=self.blob+'\n')
        raise AssertionError(args)


def subject(authorities=None):
    context={'pull_number':77,'head':H,'base_ref':'main','base':M,'merge_commit':MERGE}
    return {'number':77,'head':H,'main':M,'merge_base':M,'paths':['host/x.py'],
            'execution_required':True,'execution_context':context,
            'execution_authority':authorities if authorities is not None else
                                  sr.actions_authorities(Hub(),pull(),M)}


def evidence(**kw):
    row={'result':'PASS','kind':'execution','provider':'github-actions',
         'pull_number':77,'head':H,'base_ref':'main','base':M,'merge_commit':MERGE,
         'run_id':9001,'job_id':42,'workflow_path':PATH,'workflow_blob':WF,
         'reference':'https://example.test/run/9001','steps':['unit','hostile']}
    row.update(kw); return row


class ProviderBinding(unittest.TestCase):
    def test_empty_workflow_run_pr_array_uses_unique_commit_association(self):
        rows=sr.actions_authorities(Hub(),pull(),M)
        self.assertEqual(1,len(rows)); self.assertEqual(M,rows[0]['base'])
        self.assertEqual(MERGE,rows[0]['merge_commit']); self.assertEqual(WF,rows[0]['workflow_blob'])

    def test_same_head_wrong_pr_is_rejected(self):
        self.assertEqual([],sr.actions_authorities(Hub(associations=[assoc(number=78)]),pull(),M))

    def test_same_head_ambiguous_prs_are_rejected(self):
        self.assertEqual([],sr.actions_authorities(Hub(associations=[assoc(),assoc(number=78)]),pull(),M))

    def test_stale_base_is_rejected(self):
        stale='5'*40
        self.assertEqual([],sr.actions_authorities(Hub(p=pull(base=stale)),pull(base=stale),M))

    def test_nonempty_run_association_must_match(self):
        wrong=[{'number':78,'head':{'sha':H},'base':{'ref':'main','sha':M}}]
        self.assertEqual([],sr.actions_authorities(Hub(runs=[run(wrong)]),pull(),M))

    def test_matching_nonempty_run_association_passes(self):
        exact=[{'number':77,'head':{'sha':H},'base':{'ref':'main','sha':M}}]
        self.assertEqual(1,len(sr.actions_authorities(Hub(runs=[run(exact)]),pull(),M)))

    def test_provider_workflow_blob_must_be_sha(self):
        self.assertEqual([],sr.actions_authorities(Hub(workflow_blob='bad'),pull(),M))

    def test_full_context_execution_passes(self):
        self.assertTrue(sr.exact_execution_pass(Git(),[evidence()],subject(),M))

    def test_merge_identity_replay_fails(self):
        self.assertFalse(sr.exact_execution_pass(Git(),[evidence(merge_commit='6'*40)],subject(),M))

    def test_workflow_revision_splice_fails(self):
        self.assertFalse(sr.exact_execution_pass(Git(),[evidence(workflow_blob='7'*40)],subject(),M))

    def test_provider_context_splice_fails(self):
        authorities=sr.actions_authorities(Hub(),pull(),M)
        authorities[0]['base']='8'*40
        self.assertFalse(sr.exact_execution_pass(Git(),[evidence()],subject(authorities),M))

    def test_old_head_after_main_movement_fails(self):
        s=subject(); s['merge_base']='9'*40
        self.assertFalse(sr.exact_execution_pass(Git(),[evidence()],s,M))

    def test_live_pull_stale_base_has_no_authority(self):
        stale='5'*40
        hub=Hub(p=pull(base=stale))
        live=sr.live_pull(hub,77,M)
        self.assertEqual({},live['_execution_context'])
        self.assertEqual([],live['_execution_authority'])


_BOOTSTRAP = textwrap.dedent(r'''
    import runpy
    import sys
    import types
    from pathlib import Path

    mode=sys.argv[1]
    root=Path.cwd()
    if mode=='script':
        sys.path.insert(0,str(root/'host'))
        module_name='swarm_review'
    else:
        module_name='host.swarm_review'

    stub=types.ModuleType(module_name)
    stub.__package__='host' if mode=='module' else ''
    stub._pr_identity=lambda *a,**k: None

    def gate(*a,**k):
        print('HARDENED_GATE')
        return {}, {'state':'HOLD','reason':'fresh-process hostile fixture'}
    def noop(*a,**k):
        return []
    def identity(*a,**k):
        return a[0] if a else {}

    stub.actions_authorities=noop
    stub.exact_execution_pass=lambda *a,**k: False
    stub.change=identity
    stub.review_template=identity
    stub.live_pull=noop
    stub.verify_live=gate
    stub._core=types.SimpleNamespace(
        actions_authorities=stub.actions_authorities,
        exact_execution_pass=stub.exact_execution_pass,
        change=stub.change,
        review_template=stub.review_template,
        live_pull=stub.live_pull,
        verify_live=stub.verify_live,
    )

    class MutationReached(RuntimeError): pass
    class FakeGit:
        def compose(self,*a,**k): raise MutationReached('MUTATION_REACHED compose')
        def out(self,*a,**k): raise MutationReached('MUTATION_REACHED commit-tree')
        def run(self,*a,**k): raise MutationReached('MUTATION_REACHED push')
    class FakeHub: pass
    class GitError(Exception): pass
    class GitHubError(Exception): pass
    stub.cs=types.SimpleNamespace(
        DEFAULT_REPO='fixture/fixture',
        Git=lambda root: FakeGit(),
        GitHub=lambda repo,token: FakeHub(),
        discover_token=lambda: 'fixture-token',
        GitError=GitError,
        GitHubError=GitHubError,
        _iso=lambda value: 'fixture-time',
        _now=lambda: None,
        _commit_env=lambda: {},
    )
    sys.modules[module_name]=stub
    sys.argv=['swarm_review_core.py','merge','--pr','77']
    if mode=='script':
        runpy.run_path(str(root/'host'/'swarm_review_core.py'),run_name='__main__')
    else:
        runpy.run_module('host.swarm_review_core',run_name='__main__',alter_sys=True)
''')


class CoreFrontDoorHostiles(unittest.TestCase):
    def test_core_import_before_wrapper_has_no_live_mutation_surface(self):
        code=("import inspect; from host import swarm_review_core as c; "
              "assert 'live_pull' not in c.__dict__; "
              "assert 'verify_live' not in c.__dict__; "
              "s=inspect.getsource(c.main); "
              "assert 'commit-tree' not in s and 'push' not in s and '.compose(' not in s; "
              "print('CORE_PURE')")
        for optimized in (False,True):
            cmd=[sys.executable]+(['-O'] if optimized else [])+['-c',code]
            proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=False)
            self.assertEqual(0,proc.returncode,proc.stderr)
            self.assertIn('CORE_PURE',proc.stdout)

    def test_direct_script_and_module_merge_delegate_to_hardened_gate(self):
        for optimized in (False,True):
            for mode in ('script','module'):
                with self.subTest(optimized=optimized,mode=mode):
                    cmd=[sys.executable]+(['-O'] if optimized else [])+['-c',_BOOTSTRAP,mode]
                    proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=False)
                    combined=proc.stdout+'\n'+proc.stderr
                    self.assertEqual(1,proc.returncode,combined)
                    self.assertIn('HARDENED_GATE',proc.stdout)
                    self.assertNotIn('MUTATION_REACHED',combined)


if __name__=='__main__': unittest.main()