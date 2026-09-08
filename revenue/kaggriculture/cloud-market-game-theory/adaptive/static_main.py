# SPDX-License-Identifier: Apache-2.0
"""Preserved static weak-dominance ablation, without evaluator metadata."""
from pathlib import Path
import sys

_AGENT=None


def agent(observation,configuration=None):
    global _AGENT
    if _AGENT is None or int(observation.get('step',0))==0:
        import importlib.util
        source=globals().get('__file__') or (configuration or {})['__raw_path__']
        here=Path(source).resolve().parent;sys.path.insert(0,str(here))
        spec=importlib.util.spec_from_file_location('adaptive_static_runtime',here/'runtime.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        _AGENT=module.Agent('static')
    return _AGENT.act(observation,configuration)
