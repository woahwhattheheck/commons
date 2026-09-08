"""Run declared complete town paths through the existing saved-input consumer.

Uses OSPREY's source-pinned HAZEL -> ROUTE-FLOW -> DATE join unchanged. The input
is a saved observation, not a restored controller; future paths are assumptions.
"""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

from flow_scenarios import make_flow_scenario
from test_town_demand import load_engine


def run(row, paths, dependencies, mechanics, compare_saved_input):
    if not isinstance(paths, list) or not paths:
        raise ValueError('Supply at least one named full shop path')
    safe = dependencies.inputs.actor_input(row, row['seat'])
    obs, cfg = safe['observation'], safe['configuration']
    # The consumer's frozen mechanics omits the cap constant; use the exact
    # official engine for timing/cap, and verify the common demand catalogue.
    if (mechanics.SHOPS != dependencies.mechanics.SHOPS
            or mechanics.PRODUCTS != dependencies.mechanics.PRODUCTS
            or mechanics.TOWN_CENTER_PRODUCTS != dependencies.mechanics.TOWN_CENTER_PRODUCTS):
        raise ValueError('Town catalogues differ between the source inputs')
    specifications, bindings = [], []
    for path in paths:
        scenario, binding = make_flow_scenario(
            obs, cfg, mechanics, dependencies.flow.Scenario,
            name=path['name'], future_shops=path['future_shops'],
            rival_orders=path.get('rival_orders', {}))
        specifications.append(dataclasses.asdict(scenario))
        bindings.append(binding)
    start = time.perf_counter()
    result = compare_saved_input(row, specifications, dependencies,
                                 max_units=200_000, seconds=None, retain_trace=True)
    elapsed = time.perf_counter() - start
    return {'schema': 'town.reached-flow-join.v1', 'bindings': bindings,
            'scope': 'saved_observation_with_declared_complete_town_paths_not_physical_fills',
            'declared_paths': paths, 'scenario_bank_exhaustive': False,
            'probabilities': None, 'elapsed_quote_flow_rank_seconds': elapsed,
            'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--paths', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root / 'cloud-capital-bundles/reached_quote_case.py'
    raw = source.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob not in ('e8851922cedbf0692a02fa372599e9dbdc3798fa',
                    '794b56813daf89e06b76aaa8cbb291498e15c73c'):
        raise ValueError('Saved-input consumer differs from the tested source pin')
    spec = importlib.util.spec_from_file_location('_amber_reached', source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    dependencies = module.load_dependencies(args.source_root)
    row = dependencies.inputs.decode(args.input.read_bytes())
    paths = dependencies.inputs.decode(args.paths.read_bytes())
    report = run(row, paths, dependencies, load_engine(args.engine), module.compare_saved_input)
    report['joined_consumer_git_blob'] = blob
    report['input_file_sha256'] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    report['adapter_sha256'] = hashlib.sha256(Path(__file__).with_name('flow_scenarios.py').read_bytes()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'complete': report['result']['complete'],
                      'conditional_choice': report['result']['ranking']['selected'],
                      'paths': len(paths), 'games': 0,
                      'wall_seconds': report['elapsed_quote_flow_rank_seconds']}))


if __name__ == '__main__':
    main()
