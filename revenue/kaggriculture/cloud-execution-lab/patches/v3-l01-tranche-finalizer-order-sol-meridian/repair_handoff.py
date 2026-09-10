# SPDX-License-Identifier: Apache-2.0
"""Exact-anchor repair for the TITAN V3 L01 tranche finalizer ordering defect."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json

OPERATION = 'TITAN-V3-L01-TRANCHE-FINALIZER-ORDER-20260910-01'
HANDOFF_SHA256 = 'f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728'
EXPECTED_APPLY_PREIMAGE = '8e1093429a1bb463e2b82490963b43d9c9a4fcbd16f9d1b8d02fd75434f84436'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repair(root: Path) -> dict[str, dict[str, str]]:
    before: dict[str, str] = {}
    after: dict[str, str] = {}

    apply_path = root / "apply_v3.py"
    before[str(apply_path.relative_to(root))] = sha(apply_path)
    if before[str(apply_path.relative_to(root))] != EXPECTED_APPLY_PREIMAGE:
        raise RuntimeError(
            f"apply_v3.py preimage drift: expected {EXPECTED_APPLY_PREIMAGE}, "
            f"got {before[str(apply_path.relative_to(root))]}"
        )
    text = apply_path.read_text(encoding="utf-8")

    old_methods = '''    "    def _v3_post(self, obs, cfg, output):\\n"
    "        \\\"\\\"\\\"V3 lanes O01 (queue-safe BUY_LAND append) and E20 (low-demand HIRE limiter).\\n\\n"
    "        Runs on the completed path before _finish_production so the early_capital\\n"
    "        ordering stage sees the edited queue.  Identity when both keys are off.  A\\n"
    "        raised error keeps the selected action and is recorded, never swallowed.\\n"
    "        \\\"\\\"\\\"\\n"
    "        v3 = cfg.get('titan_v3') or {}\\n"
    "        if not (v3.get('rival_model') or v3.get('e20_hire_guard')):\\n"
    "            return output\\n"
    "        params = dict(cfg)\\n"
    "        params.update(v3.get('params') or {})\\n"
    "        report = {}\\n"
    "        try:\\n"
    "            if v3.get('rival_model'):\\n"
    "                from rival_model import apply_rival_model\\n"
    "                previous = getattr(self, '_v3_prev_prices', None)\\n"
    "                output, report['rival_model'] = apply_rival_model(obs, output, previous, params, enabled=True)\\n"
    "                self._v3_prev_prices = dict((obs.get('market') or {}).get('prices') or {})\\n"
    "            if v3.get('e20_hire_guard'):\\n"
    "                from e20_hire_guard import apply_hire_guard\\n"
    "                output, report['e20_hire_guard'] = apply_hire_guard(obs, output, params, enabled=True)\\n"
    "        except Exception as error:\\n"
    "            report['error'] = type(error).__name__\\n"
    "        self.diagnostics['v3'] = report\\n"
    "        return output\\n\\n"
'''
    new_methods = '''    "    def _v3_post(self, obs, cfg, output):\\n"
    "        \\\"\\\"\\\"V3 completed-path lanes before canonical finalization.\\n\\n"
    "        O01 and E20 edit the market queue, and L01 tranche may enlarge supported\\n"
    "        SELLs.  All run before _finish_production so final spatial/crop/feed/capital\\n"
    "        guards and receipt/history finalization observe the returned queue.\\n"
    "        Identity when every key is off.\\n"
    "        \\\"\\\"\\\"\\n"
    "        v3 = cfg.get('titan_v3') or {}\\n"
    "        l01_tranche = bool(self.features.l01_tranche)\\n"
    "        if not (v3.get('rival_model') or v3.get('e20_hire_guard') or l01_tranche):\\n"
    "            return output\\n"
    "        params = dict(cfg)\\n"
    "        params.update(v3.get('params') or {})\\n"
    "        report = {}\\n"
    "        try:\\n"
    "            if v3.get('rival_model'):\\n"
    "                from rival_model import apply_rival_model\\n"
    "                previous = getattr(self, '_v3_prev_prices', None)\\n"
    "                output, report['rival_model'] = apply_rival_model(obs, output, previous, params, enabled=True)\\n"
    "                self._v3_prev_prices = dict((obs.get('market') or {}).get('prices') or {})\\n"
    "            if v3.get('e20_hire_guard'):\\n"
    "                from e20_hire_guard import apply_hire_guard\\n"
    "                output, report['e20_hire_guard'] = apply_hire_guard(obs, output, params, enabled=True)\\n"
    "        except Exception as error:\\n"
    "            report['error'] = type(error).__name__\\n"
    "        if l01_tranche:\\n"
    "            try:\\n"
    "                from collections import Counter\\n"
    "                from l01_mechanics import apply_tranche, flags_from_features, shed_snapshot\\n"
    "                activations = Counter()\\n"
    "                output = apply_tranche(output, obs, flags_from_features(self.features), activations,\\n"
    "                                       shed=shed_snapshot(self, obs))\\n"
    "                self.diagnostics['v3_l01_tranche'] = {'activations': dict(activations)}\\n"
    "            except Exception as error:\\n"
    "                self.diagnostics['v3_l01_tranche'] = {'activations': {}, 'error': type(error).__name__}\\n"
    "        self.diagnostics['v3'] = report\\n"
    "        return output\\n\\n"
'''
    text = replace_once(text, old_methods, new_methods, "pre-final lane block")

    old_late = '''    "    def _v3_post_final(self, obs, cfg, output):\\n"
    "        \\\"\\\"\\\"V3 lane L01 tranche: live SELL enlargement after _finish_production (as measured).\\\"\\\"\\\"\\n"
    "        if not self.features.l01_tranche:\\n"
    "            return output\\n"
    "        try:\\n"
    "            from collections import Counter\\n"
    "            from l01_mechanics import apply_tranche, flags_from_features, shed_snapshot\\n"
    "            activations = Counter()\\n"
    "            output = apply_tranche(output, obs, flags_from_features(self.features), activations,\\n"
    "                                   shed=shed_snapshot(self, obs))\\n"
    "            self.diagnostics['v3_l01_tranche'] = {'activations': dict(activations)}\\n"
    "        except Exception as error:\\n"
    "            self.diagnostics['v3_l01_tranche'] = {'activations': {}, 'error': type(error).__name__}\\n"
    "        return output\\n\\n"
'''
    text = replace_once(text, old_late, "", "late tranche helper")

    text = replace_once(
        text,
        '    "tranche edits the queue after `_finish_production`. Checks: `checks/test_v3_l01.py`.\\n"\n',
        '    "tranche edits the queue before `_finish_production`, so canonical spatial/crop/feed/\\n"\n'
        '    "capital guards and receipt/history finalization see it. Checks: `checks/test_v3_l01.py`.\\n"\n',
        "release note seam",
    )

    text = replace_once(
        text,
        '        "        output = self._v3_post(obs, cfg, output)\\n"\n'
        '        "        output = self._finish_production(obs, output, cfg)\\n"\n'
        '        "        output = self._v3_post_final(obs, cfg, output)\\n"\n'
        '        "        return output\\n",\n',
        '        "        output = self._v3_post(obs, cfg, output)\\n"\n'
        '        "        output = self._finish_production(obs, output, cfg)\\n"\n'
        '        "        return output\\n",\n',
        "runtime hook order",
    )

    apply_path.write_text(text, encoding="utf-8", newline="\n")
    after[str(apply_path.relative_to(root))] = sha(apply_path)

    test_path = root / "overlay/checks/test_v3_l01.py"
    before[str(test_path.relative_to(root))] = sha(test_path)
    text = test_path.read_text(encoding="utf-8")
    text = replace_once(text, "import importlib.util\n", "import importlib.util\nimport inspect\n", "inspect import")
    old_test = '''    def test_post_final_tranche_seam(self):
        action = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'WHEAT', 3]]}
        obs = {'step': 696, 'day': 29, 'private': {'shed': {'WHEAT': 80, 'CARROT': 40}}}
        agent = TitanAgent(Features())
        agent.diagnostics = {}
        self.assertIs(agent._v3_post_final(obs, {}, action), action)
        agent = TitanAgent(Features(l01_tranche=True))
        agent.diagnostics = {}
        out = agent._v3_post_final(obs, {}, action)
        self.assertEqual([o for o in out['market'] if o[1] == 'WHEAT'][0][2], 57)
        self.assertEqual([o for o in out['market'] if o[1] == 'CARROT'][0][2], 32)
        self.assertEqual(agent.diagnostics['v3_l01_tranche']['activations'], {'TRANCHE': 2})
        self.assertEqual(action['market'], [['SELL', 'WHEAT', 3]])
'''
    new_test = '''    def test_pre_finish_tranche_seam(self):
        action = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'WHEAT', 3]]}
        obs = {'step': 696, 'day': 29, 'private': {'shed': {'WHEAT': 80, 'CARROT': 40}}}
        agent = TitanAgent(Features())
        agent.diagnostics = {}
        self.assertIs(agent._v3_post(obs, {}, action), action)
        agent = TitanAgent(Features(l01_tranche=True))
        agent.diagnostics = {}
        out = agent._v3_post(obs, {}, action)
        self.assertEqual([o for o in out['market'] if o[1] == 'WHEAT'][0][2], 57)
        self.assertEqual([o for o in out['market'] if o[1] == 'CARROT'][0][2], 32)
        self.assertEqual(agent.diagnostics['v3_l01_tranche']['activations'], {'TRANCHE': 2})
        self.assertEqual(action['market'], [['SELL', 'WHEAT', 3]])

    def test_tranche_enters_canonical_finalization(self):
        source = inspect.getsource(TitanAgent.act)
        pre = 'output = self._v3_post(obs, cfg, output)'
        finish = 'output = self._finish_production(obs, output, cfg)'
        self.assertIn(pre, source)
        self.assertIn(finish, source)
        self.assertLess(source.index(pre), source.index(finish))
        self.assertNotIn('_v3_post_final', source)
'''
    text = replace_once(text, old_test, new_test, "tranche wiring tests")
    test_path.write_text(text, encoding="utf-8", newline="\n")
    after[str(test_path.relative_to(root))] = sha(test_path)

    l01_path = root / "overlay/l01_mechanics.py"
    before[str(l01_path.relative_to(root))] = sha(l01_path)
    text = l01_path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "The four tape keys mutate `controller.R` once, at TitanAgent._initialize (seam\n`_v3_l01_install`).  l01_tranche edits the returned queue at TitanAgent._v3_post_final,\nafter _finish_production, where the L01 lane measured it.  Every flag off is a documented\n",
        "The four tape keys mutate `controller.R` once, at TitanAgent._initialize (seam\n`_v3_l01_install`).  l01_tranche edits the returned queue at TitanAgent._v3_post before\n_finish_production, so canonical spatial/crop/feed/capital guards and receipt/history\nfinalization observe it.  Every flag off is a documented\n",
        "l01 module seam docs",
    )
    l01_path.write_text(text, encoding="utf-8", newline="\n")
    after[str(l01_path.relative_to(root))] = sha(l01_path)

    readme_path = root / "README.md"
    before[str(readme_path.relative_to(root))] = sha(readme_path)
    text = readme_path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "| `l01_tranche` | L01 live sale tranches from day 28 (WHEAT ≤57, CARROT ≤32, pack the other shed products) | same | `TitanAgent._v3_post_final`, after `_finish_production` | off |",
        "| `l01_tranche` | L01 live sale tranches from day 28 (WHEAT ≤57, CARROT ≤32, pack the other shed products) | same | `TitanAgent._v3_post`, before `_finish_production` so canonical spatial/crop/feed/capital guards and receipt/history finalization see the queue | off |",
        "README seam",
    )
    readme_path.write_text(text, encoding="utf-8", newline="\n")
    after[str(readme_path.relative_to(root))] = sha(readme_path)

    manifest_path = root / "V3-MANIFEST.json"
    before[str(manifest_path.relative_to(root))] = sha(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["keys"]["l01_tranche"]["seam"] == "TitanAgent._v3_post_final after _finish_production"
    manifest["keys"]["l01_tranche"]["seam"] = (
        "TitanAgent._v3_post before _finish_production; canonical spatial/crop/feed/capital guards and receipt/history finalization observe the queue"
    )
    lane = next(row for row in manifest["lanes"] if row.get("id") == "L01")
    old_lineage = "V3 port 2026-09-09: flags from Features, tape patch at _initialize, tranche after _finish_production, checks/test_v3_l01.py (13 cases)"
    assert old_lineage in lane["lineage"]
    lane["lineage"][lane["lineage"].index(old_lineage)] = (
        "V3 port repaired 2026-09-10: flags from Features, tape patch at _initialize, tranche before _finish_production, checks/test_v3_l01.py (14 cases)"
    )
    manifest["overlay"]["apply_v3.py"] = after["apply_v3.py"]
    manifest["overlay"]["checks/test_v3_l01.py"] = after["overlay/checks/test_v3_l01.py"]
    manifest["overlay"]["l01_mechanics.py"] = after["overlay/l01_mechanics.py"]
    repairs = manifest.setdefault("repairs", [])
    if any(row.get("operation") == OPERATION for row in repairs if isinstance(row, dict)):
        raise RuntimeError(f"{OPERATION} is already recorded")
    repairs.append({
        "operation": OPERATION,
        "date": "2026-09-10",
        "input_handoff_sha256": HANDOFF_SHA256,
        "scope": "move unchanged L01 tranche application before canonical finalization",
        "policy_changed": False,
        "source_order": ["_v3_post", "_finish_production", "return"],
        "predecessor_killer": "checks/test_v3_l01.py::WiringTests.test_tranche_enters_canonical_finalization",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    after[str(manifest_path.relative_to(root))] = sha(manifest_path)

    return {"before": before, "after": after}


def validate_root(root: Path) -> None:
    required = {
        "README.md", "V3-MANIFEST.json", "apply_v3.py",
        "overlay/checks/test_v3_l01.py", "overlay/l01_mechanics.py",
    }
    missing = sorted(name for name in required if not (root / name).is_file())
    if missing:
        raise RuntimeError("candidate root is missing: " + ", ".join(missing))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="materialized candidates/v3 source directory")
    parser.add_argument("--receipt", type=Path, help="optional JSON receipt output")
    args = parser.parse_args()
    root = args.root.resolve()
    validate_root(root)
    receipt = repair(root)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
