# SPDX-License-Identifier: Apache-2.0
"""Relocatable whole-action entrypoint; one fresh instance per actor/match."""
from pathlib import Path
import sys
_INSTANCE = None

def make_agent():
    root = Path(make_agent.__code__.co_filename).resolve().parent
    if str(root) not in sys.path: sys.path.insert(0, str(root))
    from integrated_selected import make_agent as build
    return build(seed=True, committed=True, sell=False)

def agent(obs, cfg=None):
    global _INSTANCE
    step = obs.get('step')
    if step is None: step = int(obs['day'])*int((cfg or {}).get('turnsPerDay',24))+int(obs['hour'])
    if _INSTANCE is None or step == 0: _INSTANCE = make_agent()
    return _INSTANCE.act(obs, cfg)
