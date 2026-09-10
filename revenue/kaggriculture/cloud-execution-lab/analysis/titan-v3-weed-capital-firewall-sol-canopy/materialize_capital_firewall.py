#!/usr/bin/env python3
"""Materialize the exact V2 weed-capital-firewall candidate used by RESULTS."""
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import shutil
from pathlib import Path

from materialize_weed_off import manifest, sha256, tree_digest

EXPECTED_BASE_TREE_SHA256 = "98cd13d3c2cc6d16639be4bd932d313bfd6bfd1d084c0183113021ec3dad8ac2"
EXPECTED_OUTPUT_TREE_SHA256 = "d655582b1fbf9f59a92c66463bff0bd9404392a18d52a2403837df3369bc8be1"
EXPECTED_SPATIAL_SOURCE_SHA256 = "1ace1547a0f091ce36de1bbb8e023baa7b9699346968ebbc1468433733dbd50d"
EXPECTED_SPATIAL_OUTPUT_SHA256 = "4646cb1ef2529e635c7442ef2f83621a6610c4129efbb42da21b3dbcdaa97ae3"
EXPECTED_RUNTIME_SOURCE_SHA256 = "31b9366d8f04f0d7df71ceb9d3a0ce84548f2f4d419f4e9e72bf665d0192778a"
EXPECTED_RUNTIME_OUTPUT_SHA256 = "1a4c32826566947b04572da1d342942e225efe1a91304d61261463e036e503ba"

SPATIAL_INIT_OLD = """        self.supported=True
        self.seed_reserve=seed_reserve
"""
SPATIAL_INIT_NEW = """        self.supported=True
        self.seed_reserve=seed_reserve
        # Episode-local provenance for a structure rescued by weed continuation.
        self.weed_continuation_sites=set()
"""
SPATIAL_COMMIT_OLD = """            self.plans[i]=event;self.active[i]=stop+1;self.events.append(event)
            return True
"""
SPATIAL_COMMIT_NEW = """            self.plans[i]=event;self.active[i]=stop+1;self.events.append(event)
            self.weed_continuation_sites.add(origin)
            return True
"""
RUNTIME_METHOD_ANCHOR = """    def _market_pressure_selected(self, obs, cfg, selected):
"""
RUNTIME_METHOD = '''    def _weed_capital_firewall_selected(self, obs, cfg, selected):
        """Keep a rescued weed asset from bootstrapping sale-funded copies.

        The weed continuation may make one intended structure executable. Once
        that exact site contains an animal, suppress a later purchase of the same
        species when pre-market cash cannot fund one unit and earlier queue rows
        contain sales. This retains the rescued productive asset but blocks a
        same-turn liquidation-funded capital cascade.
        """
        spatial=self.spatial
        sites=() if spatial is None else getattr(spatial,'weed_continuation_sites',())
        if not sites:return selected
        farm=obs['farms'][int(obs['player'])]
        animals=set()
        for x,y in sites:
            tile=farm['tiles'][y][x]
            if isinstance(tile,dict) and tile.get('animal'):
                animals.add(tile['animal'])
        if not animals:return selected
        market=selected.get('market',[])
        money=float(farm['money'])
        from scheduler import m
        for slot,order in enumerate(market[:int(cfg.get('maxMarketOrdersPerTurn',10))]):
            if (not isinstance(order,list) or len(order)<3 or order[0]!='BUY_ANIMAL'
                    or order[1] not in animals):continue
            try: quantity=int(order[2]);cost=float(m.ANIMALS[order[1]]['cost'])
            except (TypeError,ValueError,KeyError):continue
            if quantity<=0 or money>=cost:continue
            if not any(isinstance(prior,list) and prior and prior[0]=='SELL'
                       for prior in market[:slot]):continue
            result=deepcopy(selected);result['market'][slot]=[]
            self.diagnostics['weed_capital_firewall']={
                'changed':True,'slot':slot,'animal':order[1],
                'pre_market_money':money,'unit_cost':cost,
                'weed_sites':[list(site) for site in sorted(sites)]}
            return result
        self.diagnostics['weed_capital_firewall']={'changed':False}
        return selected

'''
RUNTIME_CALL_OLD = """                stage = 'operating_stock'
                output = self._operating_stock_selected(obs, cfg, output)
                if self.history is not None:
"""
RUNTIME_CALL_NEW = """                stage = 'operating_stock'
                output = self._operating_stock_selected(obs, cfg, output)
                stage = 'weed_capital_firewall'
                output = self._weed_capital_firewall_selected(obs, cfg, output)
                if self.history is not None:
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new)


def materialize(source: Path, output: Path, *, enforce_exact: bool = True) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(output)
    base_rows = manifest(source)
    base_tree = tree_digest(base_rows)
    spatial_source = (source / "spatial_tempo.py").read_bytes()
    runtime_source = (source / "titan_runtime.py").read_bytes()
    if enforce_exact and (base_tree != EXPECTED_BASE_TREE_SHA256 or
                          sha256(spatial_source) != EXPECTED_SPATIAL_SOURCE_SHA256 or
                          sha256(runtime_source) != EXPECTED_RUNTIME_SOURCE_SHA256):
        raise ValueError("unexpected exact V2 source identity")
    shutil.copytree(source, output)
    spatial = spatial_source.decode("utf-8")
    spatial = replace_once(spatial, SPATIAL_INIT_OLD, SPATIAL_INIT_NEW, "spatial init")
    spatial = replace_once(spatial, SPATIAL_COMMIT_OLD, SPATIAL_COMMIT_NEW, "spatial commit")
    runtime = runtime_source.decode("utf-8")
    runtime = replace_once(runtime, RUNTIME_METHOD_ANCHOR, RUNTIME_METHOD + RUNTIME_METHOD_ANCHOR,
                           "runtime method")
    runtime = replace_once(runtime, RUNTIME_CALL_OLD, RUNTIME_CALL_NEW, "runtime call")
    (output / "spatial_tempo.py").write_text(spatial, encoding="utf-8")
    (output / "titan_runtime.py").write_text(runtime, encoding="utf-8")
    py_compile.compile(str(output / "spatial_tempo.py"), doraise=True)
    py_compile.compile(str(output / "titan_runtime.py"), doraise=True)
    output_rows = manifest(output)
    output_tree = tree_digest(output_rows)
    before = {row["path"]: row["sha256"] for row in base_rows}
    after = {row["path"]: row["sha256"] for row in output_rows}
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    spatial_output_sha = sha256((output / "spatial_tempo.py").read_bytes())
    runtime_output_sha = sha256((output / "titan_runtime.py").read_bytes())
    if changed != ["spatial_tempo.py", "titan_runtime.py"]:
        raise ValueError(f"non-factor source delta: {changed}")
    if enforce_exact and (output_tree != EXPECTED_OUTPUT_TREE_SHA256 or
                          spatial_output_sha != EXPECTED_SPATIAL_OUTPUT_SHA256 or
                          runtime_output_sha != EXPECTED_RUNTIME_OUTPUT_SHA256):
        raise ValueError("firewall output identity mismatch")
    return {
        "schema_version": 1,
        "operation": "exact weed-continuation capital-firewall materialization",
        "base_tree_sha256": base_tree,
        "output_tree_sha256": output_tree,
        "base_file_count": len(base_rows),
        "output_file_count": len(output_rows),
        "changed_paths": changed,
        "files": {
            "spatial_tempo.py": {
                "source_sha256": sha256(spatial_source), "output_sha256": spatial_output_sha,
            },
            "titan_runtime.py": {
                "source_sha256": sha256(runtime_source), "output_sha256": runtime_output_sha,
            },
        },
        "policy": {
            "rescued_asset": "retain",
            "same_species_sale_funded_copy": "suppress",
            "queue_index_preserved": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--allow-nonexact-fixture", action="store_true")
    args = parser.parse_args()
    receipt = materialize(args.source, args.output, enforce_exact=not args.allow_nonexact_fixture)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
