"""Hostiles for exact PR/base/merge/workflow execution authority binding."""
import copy
import unittest
from types import SimpleNamespace

from host import swarm_review as sr

H='1'*40
M='2'*40
MERGE='3'*40
WF='4'*40
PATH='.github/workflows/tests.yml'


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


if __name__=='__main__': unittest.main()
