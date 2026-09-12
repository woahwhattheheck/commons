# SPDX-License-Identifier: Apache-2.0
"""Relocatable whole-action entrypoint; one fresh instance per actor/match."""
from pathlib import Path
import sys
_INSTANCE = None
_LAST_STEP = None

def make_agent():
    root = Path(make_agent.__code__.co_filename).resolve().parent
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    from integrated_selected import make_agent as build
    return build(seed=True, committed=True, sell=False)

def agent(obs, cfg=None):
    global _INSTANCE, _LAST_STEP
    step = obs.get('step')
    if step is None: step = int(obs['day'])*int((cfg or {}).get('turnsPerDay',24))+int(obs['hour'])
    step = int(step)
    rebuild = _INSTANCE is None or (_LAST_STEP is not None and step < _LAST_STEP)
    instance = make_agent() if rebuild else _INSTANCE
    output = instance.act(obs, cfg)
    # Publish the instance and replay/reset boundary together only after a
    # complete return.  A failed cold start therefore leaves no partial runtime
    # reusable, while a failed rewind retains the last completed instance/step.
    _INSTANCE = instance
    _LAST_STEP = step
    return output
