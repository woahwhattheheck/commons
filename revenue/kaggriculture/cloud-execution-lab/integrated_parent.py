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
    if _INSTANCE is None or (_LAST_STEP is not None and step < _LAST_STEP):
        _INSTANCE = make_agent()
    output = _INSTANCE.act(obs, cfg)
    # Publish the replay/reset boundary only after a complete agent return. If a
    # rebuilt instance raises, the prior completed step keeps forcing a rebuild.
    _LAST_STEP = step
    return output
