# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from runtime import load
from policy import make_agent

original = load(ROOT/'controls.py', 't14_revision1_controls')
sell = original.sell
carrot_sell = original.carrot_sell
arlene = original.arlene
apex = original.apex
sale_cadence = original.sale_cadence
crop_demand = original.crop_demand
labor_cadence = original.labor_cadence


def entry(name):
    actor = None
    def agent(obs, cfg=None):
        nonlocal actor
        if actor is None or int(obs['step']) == 0:
            if name in ('economic', 'staged'):
                actor = make_agent(fixed='staged' if name == 'staged' else None)
            else:
                bank = load(HERE/'vendor/opponents/bank.py', 't14_public_bank_'+name)
                actor = bank.make_agent(HERE/'vendor/opponents',
                    'lonespear-v18-greedy' if name == 'lonespear' else 'cok-v10')
        action = actor(obs, cfg)
        # Evaluation-only after-call receipt. The runtime selector never reads
        # this path and the frozen public opponent receives no extra call.
        if name in ('economic', 'staged') and int(obs['step']) == 360:
            import json
            import os
            destination = os.environ.get('T14_DECISION_FILE')
            if destination:
                Path(destination).write_text(json.dumps(actor.policy.decision, indent=2)+'\n')
        return action
    return agent


economic = entry('economic')
staged = entry('staged')
lonespear = entry('lonespear')
cok = entry('cok')
