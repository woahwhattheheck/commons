# SPDX-License-Identifier: Apache-2.0
"""Source-tree entrypoint for the isolated KESTREL Titan V3 candidate."""
_INSTANCE = None


def _new_instance(root, feature_data):
    from candidate_runtime import KestrelTitanAgent
    from titan_runtime import Features, load

    features = Features(**feature_data)
    admission = None
    if features.fourth_quadrant:
        source = root / 'funded_payback.py'
        if not source.is_file():
            source = root / '../cloud-economic-stress/funded_payback/funded_payback.py'
        module = load('_kestrel_funded_payback', source, cache=True)
        adapter = load(
            '_kestrel_funded_payback_runtime',
            root / 'funded_payback_runtime.py',
            cache=True,
        )
        admission = adapter.make_admission(module.FundedPaybackAdmission)(
            seconds=features.budget_seconds,
            max_proposals=24,
        )
    return KestrelTitanAgent(
        features,
        fourth_quadrant_admission=admission,
    )


def agent(observation, configuration=None):
    global _INSTANCE
    import json
    from pathlib import Path
    import sys
    import time

    entry_started = time.perf_counter()
    cfg = dict(configuration or {})
    path = globals().get('__file__') or cfg.get('__raw_path__')
    if not path:
        raise ValueError('Entrypoint path required')
    candidate = Path(path).resolve().parent
    root = candidate.parents[1]
    for source in (candidate, root):
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    step = observation.get('step')
    if step is None:
        step = (
            int(observation['day'])
            * int(cfg.get('turnsPerDay', 24))
            + int(observation['hour'])
        )
    if _INSTANCE is None or int(step) == 0:
        feature_data = json.loads((root / 'TITAN-CONFIG.json').read_text())
        _INSTANCE = _new_instance(root, feature_data)
    return _INSTANCE.act(
        observation,
        cfg,
        entry_started=entry_started,
    )
