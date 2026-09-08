# SPDX-License-Identifier: Apache-2.0
"""Check the existing optimized core at the FrozenSelected callsite.

Only supplied local sources execute; retained game frames are observations, not
new games. This consumer does not alter the canonical runtime or build archives.
"""
from __future__ import annotations
import argparse, ast, copy, hashlib, importlib.util, json, random, sys, time, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT.parent / 'cloud-execution-lab'
COUNTS = {'score_comparisons': 0, 'optimizer_comparisons': 0, 'capacity_calls': 0}

def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def score_node(tree):
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MarketPath')
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'score')

def load(name, root, filename):
    source=(root/filename).read_bytes()
    spec=importlib.util.spec_from_file_location(name,root/filename)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    exec(compile(source,str(root/filename),'exec'),module.__dict__)
    return module

SOURCE = DONOR_SOURCE = BOUND_SOURCE = ''
ORIGINAL = CANDIDATE = BOUND = None

class FrozenScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global SOURCE,DONOR_SOURCE,BOUND_SOURCE,ORIGINAL,CANDIDATE,BOUND
        cls.old_modules={name:sys.modules.get(name) for name in ('scheduler','selected_sell_core','mechanics','frozen_selected')}
        cls.old_path=list(sys.path);sys.path.insert(0,str(ARCHIVE.resolve()))
        cls.addClassCleanup(cls.restore_imports)
        SOURCE=(ARCHIVE/'scheduler.py').read_text()
        DONOR_SOURCE=(ARCHIVE/'selected_sell_core.py').read_text()
        BOUND_SOURCE=(ARCHIVE/'frozen_selected.py').read_text()
        # One real source closure, not whichever module a previous suite left loaded.
        load('mechanics',ARCHIVE,'mechanics.py')
        ORIGINAL=load('scheduler',ARCHIVE,'scheduler.py')
        CANDIDATE=load('selected_sell_core',ARCHIVE,'selected_sell_core.py')
        BOUND=load('frozen_selected',ARCHIVE,'frozen_selected.py')

    @classmethod
    def restore_imports(cls):
        sys.path[:]=cls.old_path
        for name,previous in cls.old_modules.items():
            if previous is None:sys.modules.pop(name,None)
            else:sys.modules[name]=previous

    def models(self, item='MILK', inventory=5, now=20, end=28, shops=None, cfg=None):
        shops = list(ORIGINAL.m.SHOPS)[:4] if shops is None else shops
        cfg = {'townShopSellInterval':4, 'townCenterSellInterval':24} if cfg is None else cfg
        return [m.MarketPath(item, inventory, None, copy.deepcopy(shops), copy.deepcopy(cfg), now, end)
                for m in (ORIGINAL, CANDIDATE)]

    def pair(self, models, plan, quantity, rival, alignment='paired', terminal=False):
        result = [m.score(plan, quantity, rival, alignment, terminal) for m in models]
        self.assertEqual(result[0], result[1])
        COUNTS['score_comparisons'] += 1
        return result[0]

    def test_shared_optimizer_and_mechanics_keep_the_same_algorithm(self):
        old,new=ast.parse(SOURCE),ast.parse(DONOR_SOURCE)
        for name in ('absorption','optimize_lot','MarketPath'):
            parts=[copy.deepcopy(next(n for n in tree.body if getattr(n,'name',None)==name)) for tree in (old,new)]
            if name=='MarketPath':
                for node in parts:node.body=[n for n in node.body if getattr(n,'name',None)!='score']
            self.assertEqual(ast.dump(parts[0]),ast.dump(parts[1]),name)

    def test_selected_consumer_calls_existing_core_without_rebinding_scheduler(self):
        self.assertIs(BOUND.optimize_lot,CANDIDATE.optimize_lot)
        self.assertIs(BOUND.FrozenSelected.transform.__globals__['optimize_lot'],CANDIDATE.optimize_lot)
        self.assertIs(BOUND.FrozenSelected.__bases__[0],ORIGINAL.SellScheduler)
        self.assertIs(BOUND.post_units,ORIGINAL.post_units)
        self.assertIsNot(ORIGINAL.optimize_lot,CANDIDATE.optimize_lot)

    def test_all_products_floor_and_terminal(self):
        for item in ORIGINAL.PRODUCTS:
            for inventory in (-5, 0, 15, 1200):
                models=self.models(item,inventory)
                for quantity in (0,1,7,20):
                    for terminal in (False,True):
                        self.pair(models,((20,quantity//2),(24,quantity-quantity//2)),quantity,6,terminal=terminal)

    def test_rival_shapes_and_alignment(self):
        for rival in (0,7,(),((20,3),(24,4)),((20,2),(20,6))):
            for alignment in ('paired','before','after'):
                self.pair(self.models(),((20,3),(23,1),(28,4)),8,rival,alignment)

    def test_shop_and_interval_edits_invalidate_schedule(self):
        models=self.models()
        for interval in (4,3,8):
            for m in models:m.config['townShopSellInterval']=interval
            self.pair(models,((24,5),),8,2)
            for m in models:m.shops.append(list(ORIGINAL.m.SHOPS)[-1])
            self.pair(models,((24,5),),8,2)
        for m in models:m.config['townCenterSellInterval']=3
        self.pair(models,((25,8),),8,2)

    def test_time_and_item_edits_invalidate_schedule(self):
        models=self.models()
        self.pair(models,((24,7),),7,2)
        for m in models:m.now=23;m.end=30
        self.pair(models,((25,7),),7,2)
        for m in models:m.item='CARROT'
        self.pair(models,((25,7),),7,2)

    def test_empty_and_single_turn_horizons(self):
        for now,end in ((24,23),(24,24),(718,718)):
            self.pair(self.models(now=now,end=end),((now,7),),7,((now,2),),terminal=True)

    def test_repeated_calls_leave_inputs_unchanged(self):
        models=self.models(); plan=((20,3),(24,5)); rival=((20,1),(23,3))
        snapshots=[copy.deepcopy((m.shops,m.config)) for m in models]
        for _ in range(10):self.pair(models,plan,8,rival)
        self.assertEqual(snapshots,[(m.shops,m.config) for m in models])

    def test_every_joint_receipt_invocation_order_matches(self):
        models=self.models(); logs=[[],[]]
        for i,m in enumerate(models):
            original=m.joint
            def traced(*a,_fn=original,_log=logs[i]):
                result=_fn(*a);_log.append((a,result));return result
            m.joint=traced
        self.pair(models,((20,3),(24,5)),8,((21,2),(25,4)))
        self.assertEqual(logs[0],logs[1])

    def test_full_optimizer_and_capacity_order(self):
        rng=random.Random(9096)
        for case in range(80):
            now=rng.choice((0,21,23,24,709,713,715))
            dates=sorted(set((now,min(now+2,718),min(now+6,718))))
            q=rng.randrange(1,20);ref=((now,q),)
            params=dict(item=rng.choice(ORIGINAL.PRODUCTS),quantity=q,inventory=rng.randrange(-5,80),
                        params=None,shops=list(ORIGINAL.m.SHOPS)[:case%8],config={},now=now,dates=dates,
                        reference=ref,rival_quantity=rng.randrange(0,15),minimum_now=case%3,last=718)
            logs=[[],[]]; outputs=[]
            for i,module in enumerate((ORIGINAL,CANDIDATE)):
                def capacity(plan,_log=logs[i],_q=q):
                    _log.append(plan);return sum(n for _,n in plan)<=_q
                outputs.append(module.optimize_lot(**copy.deepcopy(params),capacity_ok=capacity))
            self.assertEqual(outputs[0],outputs[1]); self.assertEqual(logs[0],logs[1])
            COUNTS['optimizer_comparisons']+=1;COUNTS['capacity_calls']+=len(logs[0])

    def test_schedule_is_reused_at_actual_optimizer_callsite(self):
        params=dict(item='MILK',quantity=18,inventory=5,params=None,shops=list(ORIGINAL.m.SHOPS),
                    config={},now=20,dates=[20,22,25,28],reference=((20,18),),rival_quantity=10)
        calls=[];outputs=[]
        for module in (ORIGINAL,CANDIDATE):
            fn=module.absorption;log=[]
            def capture(*a,_fn=fn,_log=log):_log.append(a[1]);return _fn(*a)
            module.absorption=capture
            try:outputs.append(module.optimize_lot(**copy.deepcopy(params)))
            finally:module.absorption=fn
            calls.append(len(log))
        self.assertEqual(outputs[0],outputs[1]);self.assertEqual(calls[1],9);self.assertGreater(calls[0],1000)
        COUNTS['absorption_calls_original_candidate']=calls

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ARCHIVE,help='Existing cloud-execution-lab source root')
    p.add_argument('--output',type=Path)
    args=p.parse_args();ARCHIVE=args.root.resolve()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FrozenScoreTests))
    out={'schema':'titan.frozen-core-join.tests.v1','tests':result.testsRun,
         'failures':len(result.failures),'errors':len(result.errors),'counts':COUNTS,
         'original_blob':blob(SOURCE.encode()),'core_blob':blob(DONOR_SOURCE.encode()),
         'consumer_blob':blob(BOUND_SOURCE.encode()),'game_evaluations':0,
         'failure_details':[str(t)+'\n'+tb for t,tb in result.failures+result.errors]}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
    raise SystemExit(not result.wasSuccessful())
