# SPDX-License-Identifier: Apache-2.0
"""Direct-entrypoint consumer tests; synthetic protocol data, not game results."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import profile_saved as p

TIMING = Path(os.environ.get('TITAN_TIMING_SOURCE', str(
    Path(__file__).resolve().parent.parent / 'cloud-combination-analysis/execution_timing.py')))

# Exact PR10177 main.py, Git blob44f056938ab78212f74e6cf0987e5645702fd0ae.
# Its imported runtime is an explicit test fixture below, not a policy substitute.
CANONICAL = '''# SPDX-License-Identifier: Apache-2.0
"""Canonical TITAN entrypoint. Feature choices are deterministic package data."""
_INSTANCE = None


def agent(observation, configuration=None):
    global _INSTANCE
    import time
    entry_started = time.perf_counter()
    from pathlib import Path
    import json
    import sys
    cfg = dict(configuration or {})
    path = globals().get('__file__') or cfg.get('__raw_path__')
    if not path:
        raise ValueError('Entrypoint path required')
    root = Path(path).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from titan_runtime import TitanAgent, Features
    step = observation.get('step')
    if step is None:
        step = int(observation['day'])*int(cfg.get('turnsPerDay', 24))+int(observation['hour'])
    if _INSTANCE is None or int(step) == 0:
        _INSTANCE = TitanAgent(Features(**json.loads((root/'TITAN-CONFIG.json').read_text())))
    return _INSTANCE.act(observation, cfg, entry_started=entry_started)
'''


def action(count, marker=7):
    return {'count': count, 'marker': marker}


class DirectEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = self.root/'runtime'/'main.py'
        self.target.parent.mkdir()
        self.input = self.root/'work.json'
        self.work = {'schema':'titan.profile.observations.v1',
          'configuration':{'seed':123,'marker':7,'turnsPerDay':24},
          'provenance':{'kind':'constructed direct-entrypoint contract'},
          'records':[{'observation':{'step':i,'player':0,'day':0,'hour':i,
                       'private':{},'farms':[{},{}],'market':{}},
                      'expected_action':action(i+1)} for i in range(3)]}
        self.input.write_text(json.dumps(self.work))
        self.index=0

    def call(self, source, *, direct='agent', expected_code=0, extra=()):
        self.target.write_text(source)
        self.index+=1
        output=self.root/f'result{self.index}.json'
        command=[sys.executable,'-B',str(Path(p.__file__).resolve()),
            '--entrypoint',str(self.target),'--timing-source',str(TIMING),
            '--replay',str(self.input),'--output',str(output),
            '--max-decisions','3','--profile-slowest','1','--process-timeout','8']
        if direct is not None: command+=['--entrypoint-callable',direct]
        command+=list(extra)
        run=subprocess.run(command,capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,expected_code,run.stdout+run.stderr)
        if not output.exists(): return None,run
        report=json.loads(output.read_text())
        for mode in ('ordinary','instrumented'):
            self.assertEqual(report[mode]['process_exit_code'],expected_code)
        return report,run

    def complete(self, report):
        self.assertTrue(report['instrumentation_action_parity'])
        for mode in ('ordinary','instrumented'):
            row=report[mode]
            self.assertEqual(row['status'],'complete')
            self.assertEqual(len(row['calls']),3)
            self.assertEqual(row['timings']['calls'],3)
            self.assertEqual(row['expected_actions']['mismatches'],0)
            self.assertEqual(row['call_binding']['kind'],'module_callable')
            self.assertTrue(row['sources_unchanged'])
            self.assertTrue(row['loaded_sources_unchanged'])

    def test_one_argument_function_keeps_fresh_persistent_state(self):
        report,_=self.call('''count=0
def agent(obs):
 global count
 count+=1
 return {'count':count,'marker':7}
''')
        self.complete(report)

    def test_two_argument_function_receives_config_without_hidden_seed(self):
        report,_=self.call('''count=0
def agent(obs,cfg):
 global count
 assert 'seed' not in cfg
 count+=1
 return {'count':count,'marker':cfg['marker']}
''')
        self.complete(report)

    def test_optional_config_typeerror_is_one_failure_not_a_retry(self):
        log=self.root/'body-calls'
        report,_=self.call(f'''from pathlib import Path
import os
def agent(obs,cfg=None):
 with Path({str(log)!r}).open('a') as f: f.write(str(os.getpid())+'\\n')
 raise TypeError('original direct body')
''',expected_code=2)
        self.assertEqual(len(log.read_text().splitlines()),2)
        for mode in ('ordinary','instrumented'):
            row=report[mode]
            self.assertEqual(row['error'],{'type':'TypeError','message':'original direct body'})
            self.assertEqual(len(row['calls']),1)
            self.assertEqual(row['timings']['failures'],1)

    def test_exported_callable_object_is_not_constructed_again(self):
        report,_=self.call('''class Actor:
 def __init__(self): self.count=0
 def __call__(self,obs,cfg=None):
  self.count+=1
  return {'count':self.count,'marker':7}
agent=Actor()
''')
        self.complete(report)

    def test_unused_factory_is_never_called(self):
        report,_=self.call('''count=0
def make_agent(): raise AssertionError('unselected factory')
def agent(obs,cfg=None):
 global count
 count+=1
 return {'count':count,'marker':7}
''')
        self.complete(report)

    def test_missing_callable_keeps_original_attribute_error(self):
        report,_=self.call('other=1\n',expected_code=2)
        self.assertFalse(report['instrumentation_action_parity'])
        for mode in ('ordinary','instrumented'):
            self.assertEqual(report[mode]['error']['type'],'AttributeError')
            self.assertEqual(report[mode]['calls'],[])

    def test_noncallable_attribute_cannot_become_a_policy(self):
        report,_=self.call('agent=4\n',expected_code=2)
        for mode in ('ordinary','instrumented'):
            self.assertEqual(report[mode]['error']['type'],'TypeError')
            self.assertEqual(report[mode]['calls'],[])

    def test_non_mapping_result_remains_a_policy_error(self):
        report,_=self.call('def agent(obs,cfg=None): return 3\n',expected_code=2)
        for mode in ('ordinary','instrumented'):
            self.assertEqual(report[mode]['error']['type'],'TypeError')
            self.assertEqual(len(report[mode]['calls']),1)

    def test_later_failure_preserves_successful_prefix(self):
        report,_=self.call('''count=0
def agent(obs,cfg=None):
 global count
 count+=1
 if count==2: raise ValueError('second action')
 return {'count':count,'marker':7}
''',expected_code=2)
        for mode in ('ordinary','instrumented'):
            row=report[mode]
            self.assertEqual(row['error']['message'],'second action')
            self.assertEqual(len(row['calls']),2)
            self.assertEqual(row['expected_actions']['present'],1)
            self.assertIn('action_sha256',row['calls'][0])
            self.assertNotIn('action_sha256',row['calls'][1])

    def test_lazy_construction_stays_inside_first_action_timing(self):
        log=self.root/'events'
        report,_=self.call(f'''from pathlib import Path
import time
count=0
def agent(obs,cfg=None):
 global count
 if not count:
  with Path({str(log)!r}).open('a') as f: f.write(str(obs['step'])+'\\n')
  time.sleep(.02)
 count+=1
 return {{'count':count,'marker':7}}
''')
        self.complete(report)
        self.assertEqual(log.read_text().splitlines(),['0','0'])
        for mode in ('ordinary','instrumented'):
            row=report[mode]
            self.assertGreaterEqual(row['timings']['first_action_s'],.018)
            self.assertIn('lazy controller construction',row['call_binding']['initialization_scope'])

    def test_explicit_factory_conflict_precedes_source_execution(self):
        marker=self.root/'imported'
        report,run=self.call(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n',
            expected_code=2,extra=['--factory','make_agent'])
        self.assertIsNone(report)
        self.assertFalse(marker.exists())

    def test_factory_kwargs_conflict_precedes_source_execution(self):
        marker=self.root/'imported'
        report,run=self.call(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n',
            expected_code=2,extra=['--factory-kwargs','{"funded": false}'])
        self.assertIsNone(report)
        self.assertFalse(marker.exists())

    def test_factory_default_remains_unchanged(self):
        report,_=self.call('''class Actor:
 def __init__(self): self.count=0
 def act(self,obs,cfg=None):
  self.count+=1
  return {'count':self.count,'marker':7}
def make_agent(): return Actor()
''',direct=None)
        self.assertTrue(report['instrumentation_action_parity'])
        for mode in ('ordinary','instrumented'):
            self.assertNotIn('call_binding',report[mode])
            self.assertEqual(report[mode]['expected_actions']['mismatches'],0)

    def test_row_configuration_and_input_detachment(self):
        for i,row in enumerate(self.work['records']):
            row['configuration']={'marker':i,'seed':900+i}
            row['expected_action']=action(i+1,i)
        self.input.write_text(json.dumps(self.work)); before=self.input.read_bytes()
        report,_=self.call('''count=0
def agent(obs,cfg=None):
 global count
 count+=1
 assert 'seed' not in cfg
 marker=cfg.pop('marker')
 obs['private']['new']=1
 return {'count':count,'marker':marker}
''')
        self.complete(report)
        self.assertEqual(self.input.read_bytes(),before)

    def test_exact_canonical_entrypoint_with_explicit_runtime_fixture(self):
        raw=CANONICAL.encode()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
                         '44f056938ab78212f74e6cf0987e5645702fd0ae')
        (self.target.parent/'TITAN-CONFIG.json').write_text('{"marker":7}')
        (self.target.parent/'titan_runtime.py').write_text('''import time
constructed=0
class Features:
 def __init__(self,**values): self.marker=values['marker']
class TitanAgent:
 def __init__(self,features):
  global constructed
  constructed+=1
  assert constructed==1
  self.count=0; self.features=features
 def act(self,obs,cfg,entry_started=None):
  assert isinstance(entry_started,float) and entry_started<=time.perf_counter()
  assert 'seed' not in cfg
  self.count+=1
  return {'count':self.count,'marker':self.features.marker}
''')
        report,_=self.call(CANONICAL)
        self.complete(report)
        for mode in ('ordinary','instrumented'):
            self.assertEqual(report[mode]['loaded_sources']['finch_profile_target']['sha256'],
                             hashlib.sha256(raw).hexdigest())

    def test_exported_diagnostics_only_no_private_actor_introspection(self):
        report,_=self.call('''count=0
_INSTANCE=object()
def agent(obs,cfg=None):
 global count
 count+=1
 agent.diagnostics={'status':'observed','reason':'direct','secret':42}
 return {'count':count,'marker':7}
''')
        self.complete(report)
        for mode in ('ordinary','instrumented'):
            for call in report[mode]['calls']:
                self.assertEqual(call['diagnostics'],{'status':'observed','reason':'direct'})

    def test_binary_diagnostics_use_the_current_supervisor_decoding(self):
        report,_=self.call("import os\ncount=0\ndef agent(obs,cfg=None):\n global count\n os.write(1,b'notice \\xff\\n')\n count+=1\n return {'count':count,'marker':7}\n")
        self.complete(report)
        for mode in ('ordinary','profile'):
            data=(self.root/f'result{self.index}.{mode}.log').read_text()
            self.assertEqual(data.count('notice \\xff\n'),3)

if __name__=='__main__':
    unittest.main(verbosity=2)
