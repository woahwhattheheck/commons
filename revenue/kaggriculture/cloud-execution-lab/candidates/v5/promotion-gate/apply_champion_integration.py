#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess

BASE = "31f0016b4547958c26c5a4a7a252eb9d09be15d4"
DONOR = "5fa4187b1fe74c8b2bc480af8ba2a7931bd965ad"
BRANCH = "sol/v5-paired-economics-release-firewall-clean-20260912"
ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
PG = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/promotion-gate"
TEMP = {
    ".github/workflows/titan-v5-champion-integrate-one-shot.yml",
    "revenue/kaggriculture/cloud-execution-lab/candidates/v5/promotion-gate/apply_champion_integration.py",
}


def run(*args: str) -> str:
    return subprocess.check_output(list(args), cwd=ROOT, text=True)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    return text.replace(old, new, 1)


def donor(path: str) -> str:
    return run("git", "show", f"{DONOR}:{path}")


# Ref-race / scope guard. The temporary staging commits may be on top of BASE,
# but nothing else is allowed to have moved this branch while this one-shot runs.
if subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT).returncode:
    raise SystemExit("claimed #13409 base is no longer an ancestor")
changed = {line for line in run("git", "diff", "--name-only", f"{BASE}..HEAD").splitlines() if line}
if changed - TEMP:
    raise SystemExit(f"unexpected concurrent #13409 changes since claim: {sorted(changed - TEMP)!r}")

# Import the closed #13420 theorem as donor source only; it is never merged as a
# sibling release path. Permanent files live under the one #13409 firewall.
gate = donor("revenue/kaggriculture/cloud-execution-lab/candidates/v5/champion-ratchet/champion_gate.py")
test_gate = donor("revenue/kaggriculture/cloud-execution-lab/candidates/v5/champion-ratchet/test_champion_gate.py")

gate = replace_once(
    gate,
    'V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"\nMIN_OPPONENTS = 2\n',
    'V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"\n'
    'V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"\n'
    'V31_SUBMISSION_ID = 56172377\n'
    'AUTHORIZED_OPPONENT_IDS = ("apex_v7", "arlene_v14")\n'
    'REFERENCE_POLICIES_GIT_BLOB = "6bce02dad705ccc57656ff2e2139db215f9fcc57"\n'
    'MIN_OPPONENTS = len(AUTHORIZED_OPPONENT_IDS)\n',
    "champion constants",
)
gate = replace_once(
    gate,
    '        bucket = stratum.setdefault((opponent, seat), {"n": 0, "incumbent_own": 0, "champion_own": 0, "candidate_own": 0})\n'
    '        bucket["n"] += 1\n'
    '        bucket["incumbent_own"] += vals["incumbent_own"]\n'
    '        bucket["champion_own"] += vals["champion_own"]\n'
    '        bucket["candidate_own"] += vals["candidate_own"]\n',
    '        bucket = stratum.setdefault((opponent, seat), {\n'
    '            "n": 0, "incumbent_own": 0, "champion_own": 0, "candidate_own": 0,\n'
    '            "incumbent_margin": 0, "champion_margin": 0, "candidate_margin": 0,\n'
    '        })\n'
    '        bucket["n"] += 1\n'
    '        bucket["incumbent_own"] += vals["incumbent_own"]\n'
    '        bucket["champion_own"] += vals["champion_own"]\n'
    '        bucket["candidate_own"] += vals["candidate_own"]\n'
    '        bucket["incumbent_margin"] += im\n'
    '        bucket["champion_margin"] += hm\n'
    '        bucket["candidate_margin"] += cm\n',
    "champion stratum accumulation",
)
gate = replace_once(
    gate,
    '    opponents = sorted(seeds_by_opp)\n'
    '    if len(opponents) < MIN_OPPONENTS:\n'
    '        raise ChampionError(f"panel requires at least {MIN_OPPONENTS} opponents")\n',
    '    opponents = sorted(seeds_by_opp)\n'
    '    if opponents != list(AUTHORIZED_OPPONENT_IDS):\n'
    '        raise ChampionError("opponents do not equal authorized release roster")\n'
    '    if len(opponents) < MIN_OPPONENTS:\n'
    '        raise ChampionError(f"panel requires at least {MIN_OPPONENTS} opponents")\n',
    "champion exact roster",
)
gate = replace_once(
    gate,
    '        d_inc = bucket["candidate_own"] - bucket["incumbent_own"]\n'
    '        d_v31 = bucket["candidate_own"] - bucket["champion_own"]\n'
    '        if d_inc < 0 or d_v31 < 0:\n'
    '            raise ChampionError(\n'
    '                f"negative own-score stratum opponent={opponent!r} seat={seat} incumbent_delta={d_inc} v31_delta={d_v31}"\n'
    '            )\n'
    '        strata.append({\n'
    '            "opponent_id": opponent,\n'
    '            "seat": seat,\n'
    '            "cell_count": bucket["n"],\n'
    '            "own_delta_vs_incumbent": d_inc,\n'
    '            "own_delta_vs_v31": d_v31,\n'
    '        })\n',
    '        d_inc = bucket["candidate_own"] - bucket["incumbent_own"]\n'
    '        d_v31 = bucket["candidate_own"] - bucket["champion_own"]\n'
    '        m_inc = bucket["candidate_margin"] - bucket["incumbent_margin"]\n'
    '        m_v31 = bucket["candidate_margin"] - bucket["champion_margin"]\n'
    '        if d_inc < 0 or d_v31 < 0:\n'
    '            raise ChampionError(\n'
    '                f"negative own-score stratum opponent={opponent!r} seat={seat} incumbent_delta={d_inc} v31_delta={d_v31}"\n'
    '            )\n'
    '        if m_inc < 0 or m_v31 < 0:\n'
    '            raise ChampionError(\n'
    '                f"negative margin stratum opponent={opponent!r} seat={seat} incumbent_delta={m_inc} v31_delta={m_v31}"\n'
    '            )\n'
    '        strata.append({\n'
    '            "opponent_id": opponent,\n'
    '            "seat": seat,\n'
    '            "cell_count": bucket["n"],\n'
    '            "own_delta_vs_incumbent": d_inc,\n'
    '            "own_delta_vs_v31": d_v31,\n'
    '            "margin_delta_vs_incumbent": m_inc,\n'
    '            "margin_delta_vs_v31": m_v31,\n'
    '        })\n',
    "champion stratum safety",
)
gate = replace_once(
    gate,
    '        "champion_archive_sha256": champion_archive,\n'
    '        "candidate_archive_sha256": candidate_archive,\n'
    '        "opponent_ids": opponents,\n',
    '        "champion_archive_sha256": champion_archive,\n'
    '        "champion_source_commit": V31_SOURCE_COMMIT,\n'
    '        "champion_submission_id": V31_SUBMISSION_ID,\n'
    '        "candidate_archive_sha256": candidate_archive,\n'
    '        "opponent_ids": opponents,\n'
    '        "authorized_opponent_ids": list(AUTHORIZED_OPPONENT_IDS),\n'
    '        "opponent_registry_git_blob": REFERENCE_POLICIES_GIT_BLOB,\n',
    "champion authority receipt",
)

test_gate = test_gate.replace('for opp in ("opp:a", "opp:b"):', 'for opp in G.AUTHORIZED_OPPONENT_IDS:')
test_gate = test_gate.replace('c["opponent_id"] == "opp:a"', 'c["opponent_id"] == "apex_v7"')
test_gate = test_gate.replace('c["opponent_id"] == "opp:b"', 'c["opponent_id"] == "arlene_v14"')
test_gate = replace_once(
    test_gate,
    '    def test_wrong_v31_archive_fails(self):\n',
    '    def test_exact_authorized_roster_is_required(self):\n'
    '        x = report()\n'
    '        for cell in x["cells"]:\n'
    '            if cell["opponent_id"] == "arlene_v14":\n'
    '                cell["opponent_id"] = "kaito_v43"\n'
    '        x["cells"].sort(key=lambda c: (c["opponent_id"], c["seed"], c["seat"]))\n'
    '        with self.assertRaisesRegex(G.ChampionError, "authorized release roster"):\n'
    '            G.validate_report(x)\n\n'
    '    def test_per_opponent_seat_margin_regression_cannot_be_masked(self):\n'
    '        x = report()\n'
    '        for c in x["cells"]:\n'
    '            if c["opponent_id"] == "apex_v7" and c["seat"] == 0:\n'
    '                c["candidate_rival"] += 20\n'
    '            elif c["opponent_id"] == "arlene_v14" and c["seat"] == 0:\n'
    '                c["candidate_rival"] -= 20\n'
    '        with self.assertRaisesRegex(G.ChampionError, "negative margin stratum"):\n'
    '            G.validate_report(x)\n\n'
    '    def test_wrong_v31_archive_fails(self):\n',
    "champion tests",
)

(PG / "champion_gate.py").write_text(gate, encoding="utf-8")
(PG / "test_champion_gate.py").write_text(test_gate, encoding="utf-8")

# Wire champion evidence into the one release-authorizing transaction.
release_path = PG / "release_transaction.py"
release = release_path.read_text(encoding="utf-8")
release = replace_once(
    release,
    'paired competitive-economics PASS bound to the exact execution closure, replays\n',
    'paired competitive-economics PASS plus exact submitted V3.1 champion ratchet, replays\n',
    "release docstring",
)
release = replace_once(release, 'SCHEMA = "titan-v5-release-transaction/v4"', 'SCHEMA = "titan-v5-release-transaction/v5"', "release schema")
release = replace_once(
    release,
    'ECONOMICS_RECEIPT_SCHEMA = "titan-v5-paired-economics-receipt/v4"\n',
    'ECONOMICS_RECEIPT_SCHEMA = "titan-v5-paired-economics-receipt/v4"\n'
    'CHAMPION_RECEIPT_SCHEMA = "titan-v5-champion-ratchet-receipt/v1"\n'
    'V31_ARCHIVE_SHA256 = "5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"\n'
    'V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"\n'
    'V31_SUBMISSION_ID = 56172377\n',
    "release champion constants",
)
champion_replay = r'''

def _champion_replay(
    champion_builder: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    champion_raw: bytes,
    economics_raw: bytes,
    *,
    candidate_id: str,
    control_id: str,
    engine_id: Any,
    opponent_pack_id: Any,
    control_archive_sha256: str,
    candidate_archive_sha256: str,
) -> dict[str, Any]:
    """Replay V3.1 score admission and bind it to the authenticated economics cells."""
    champion_report = _loads(champion_raw, "champion report")
    economics_report = _loads(economics_raw, "economics report for champion binding")
    if type(champion_report) is not dict or type(economics_report) is not dict:
        raise TransactionError("champion/economics reports must be objects")
    try:
        receipt = champion_builder(champion_report)
    except Exception as exc:
        raise TransactionError(f"champion gate replay failed: {exc}") from exc
    if type(receipt) is not dict:
        raise TransactionError("champion gate did not return an object")
    if receipt.get("schema") != CHAMPION_RECEIPT_SCHEMA:
        raise TransactionError("champion gate receipt schema is not release-authorized")
    if receipt.get("classification") != "PASS" or receipt.get("champion_ready") is not True:
        raise TransactionError("champion gate is not a release-ready PASS")

    expected = {
        "incumbent_id": control_id,
        "candidate_id": candidate_id,
        "engine_id": engine_id,
        "opponent_pack_id": opponent_pack_id,
        "incumbent_archive_sha256": control_archive_sha256,
        "champion_archive_sha256": V31_ARCHIVE_SHA256,
        "champion_source_commit": V31_SOURCE_COMMIT,
        "champion_submission_id": V31_SUBMISSION_ID,
        "candidate_archive_sha256": candidate_archive_sha256,
        "authorized_opponent_ids": list(AUTHORIZED_OPPONENT_IDS),
        "opponent_registry_git_blob": REFERENCE_POLICIES_GIT_BLOB,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise TransactionError(f"champion receipt {key} disagrees with release authority")
    if receipt.get("opponent_ids") != list(AUTHORIZED_OPPONENT_IDS):
        raise TransactionError("champion receipt opponent_ids do not equal authorized release roster")

    economics_cells = economics_report.get("cells")
    champion_cells = champion_report.get("cells")
    if type(economics_cells) is not list or type(champion_cells) is not list:
        raise TransactionError("champion/economics reports must contain cell lists")
    if len(economics_cells) != len(champion_cells):
        raise TransactionError("champion/economics panel cell counts differ")
    for index, (econ_cell, champ_cell) in enumerate(zip(economics_cells, champion_cells)):
        if type(econ_cell) is not dict or type(champ_cell) is not dict:
            raise TransactionError(f"champion/economics cell[{index}] must be objects")
        for key in ("opponent_id", "seed", "seat"):
            if econ_cell.get(key) != champ_cell.get(key):
                raise TransactionError(f"champion/economics panel identity mismatch at cell[{index}].{key}")
        score_pairs = (
            ("control_own", "incumbent_own"),
            ("control_rival", "incumbent_rival"),
            ("candidate_own", "candidate_own"),
            ("candidate_rival", "candidate_rival"),
        )
        for economics_key, champion_key in score_pairs:
            if econ_cell.get(economics_key) != champ_cell.get(champion_key):
                raise TransactionError(
                    f"champion/economics score mismatch at cell[{index}] "
                    f"{economics_key}/{champion_key}"
                )
    return receipt
'''
release = replace_once(release, '\n\ndef _trust_digest(files: Mapping[str, bytes]) -> str:\n', champion_replay + '\n\ndef _trust_digest(files: Mapping[str, bytes]) -> str:\n', "champion replay insertion")
release = replace_once(
    release,
    '    economics_raw: bytes,\n    promotion_builder: Callable[..., Mapping[str, Any]],\n    economics_builder: Callable[..., Mapping[str, Any]],\n',
    '    economics_raw: bytes,\n    champion_raw: bytes,\n    promotion_builder: Callable[..., Mapping[str, Any]],\n    economics_builder: Callable[..., Mapping[str, Any]],\n    champion_builder: Callable[[Mapping[str, Any]], Mapping[str, Any]],\n',
    "mandatory champion build inputs",
)
release = replace_once(
    release,
    '    bind_promoted_sources(manifest, source_manifest, archive_members)\n\n'
    '    if type(trust_result) is not dict or trust_result.get("ok") is not True:\n',
    '    bind_promoted_sources(manifest, source_manifest, archive_members)\n'
    '    champion = _champion_replay(\n'
    '        champion_builder,\n'
    '        champion_raw,\n'
    '        economics_raw,\n'
    '        candidate_id=promotion["candidate_id"],\n'
    '        control_id=promotion["control_id"],\n'
    '        engine_id=manifest.get("engine_id"),\n'
    '        opponent_pack_id=manifest.get("opponent_pack_id"),\n'
    '        control_archive_sha256=old_pointer["sha256"],\n'
    '        candidate_archive_sha256=new_pointer["sha256"],\n'
    '    )\n\n'
    '    if type(trust_result) is not dict or trust_result.get("ok") is not True:\n',
    "mandatory champion replay",
)
release = replace_once(
    release,
    '            "panel_sha256": economics["panel_sha256"],\n'
    '        },\n'
    '        "trusted_base": {\n',
    '            "panel_sha256": economics["panel_sha256"],\n'
    '        },\n'
    '        "champion": {\n'
    '            "report_sha256": _sha(champion_raw),\n'
    '            "incumbent_id": champion["incumbent_id"],\n'
    '            "candidate_id": champion["candidate_id"],\n'
    '            "champion_archive_sha256": champion["champion_archive_sha256"],\n'
    '            "champion_source_commit": champion["champion_source_commit"],\n'
    '            "champion_submission_id": champion["champion_submission_id"],\n'
    '            "authorized_opponent_ids": champion["authorized_opponent_ids"],\n'
    '            "opponent_registry_git_blob": champion["opponent_registry_git_blob"],\n'
    '            "own_sum_delta_vs_incumbent": champion["own_sum_delta_vs_incumbent"],\n'
    '            "own_sum_delta_vs_v31": champion["own_sum_delta_vs_v31"],\n'
    '            "margin_sum_delta_vs_incumbent": champion["margin_sum_delta_vs_incumbent"],\n'
    '            "margin_sum_delta_vs_v31": champion["margin_sum_delta_vs_v31"],\n'
    '            "strata": champion["strata"],\n'
    '            "panel_sha256": champion["panel_sha256"],\n'
    '            "economics_panel_sha256": economics["panel_sha256"],\n'
    '        },\n'
    '        "trusted_base": {\n',
    "champion transaction binding",
)
release = replace_once(
    release,
    '    parser.add_argument("--economics-report", type=Path, required=True)\n',
    '    parser.add_argument("--economics-report", type=Path, required=True)\n'
    '    parser.add_argument("--champion-report", type=Path, required=True)\n',
    "champion CLI argument",
)
release = replace_once(
    release,
    '        economics_module, _ = _load_module(here.with_name("economics_gate.py"), "_titan_v5_economics_gate")\n',
    '        economics_module, _ = _load_module(here.with_name("economics_gate.py"), "_titan_v5_economics_gate")\n'
    '        champion_module, _ = _load_module(here.with_name("champion_gate.py"), "_titan_v5_champion_gate")\n',
    "champion module loader",
)
release = replace_once(
    release,
    '            economics_raw=_read(args.economics_report, "economics report"),\n'
    '            promotion_builder=promotion_module.build_receipt,\n'
    '            economics_builder=economics_module.validate_report,\n',
    '            economics_raw=_read(args.economics_report, "economics report"),\n'
    '            champion_raw=_read(args.champion_report, "champion report"),\n'
    '            promotion_builder=promotion_module.build_receipt,\n'
    '            economics_builder=economics_module.validate_report,\n'
    '            champion_builder=champion_module.validate_report,\n',
    "champion CLI wiring",
)
release_path.write_text(release, encoding="utf-8")

# Patch central release tests once; every existing build goes through one helper.
test_path = PG / "test_release_transaction.py"
test_release = test_path.read_text(encoding="utf-8")
test_release = replace_once(
    test_release,
    'ECON_SPEC.loader.exec_module(econ)\n\n\ndef canon(value):\n',
    'ECON_SPEC.loader.exec_module(econ)\n'
    'CHAMP_SPEC = importlib.util.spec_from_file_location(\n'
    '    "_champion_gate_for_release_test", HERE / "champion_gate.py"\n'
    ')\n'
    'assert CHAMP_SPEC is not None and CHAMP_SPEC.loader is not None\n'
    'champ = importlib.util.module_from_spec(CHAMP_SPEC)\n'
    'CHAMP_SPEC.loader.exec_module(champ)\n\n\n'
    'def canon(value):\n',
    "champion test module",
)
test_release = replace_once(
    test_release,
    '        self.economics_raw = canon(self.economics)\n'
    '        self.trust_result = {\n',
    '        self.economics_raw = canon(self.economics)\n'
    '        champion_cells = []\n'
    '        for cell in cells:\n'
    '            champion_cells.append({\n'
    '                "opponent_id": cell["opponent_id"],\n'
    '                "seed": cell["seed"],\n'
    '                "seat": cell["seat"],\n'
    '                "incumbent_own": cell["control_own"],\n'
    '                "incumbent_rival": cell["control_rival"],\n'
    '                "champion_own": cell["control_own"] + 5,\n'
    '                "champion_rival": cell["control_rival"],\n'
    '                "candidate_own": cell["candidate_own"],\n'
    '                "candidate_rival": cell["candidate_rival"],\n'
    '            })\n'
    '        self.champion = {\n'
    '            "schema": champ.SCHEMA,\n'
    '            "incumbent_id": self.promotion["control_id"],\n'
    '            "candidate_id": self.promotion["candidate_id"],\n'
    '            "engine_id": self.manifest["engine_id"],\n'
    '            "opponent_pack_id": self.manifest["opponent_pack_id"],\n'
    '            "incumbent_archive_sha256": self.old["sha256"],\n'
    '            "champion_archive_sha256": champ.V31_ARCHIVE_SHA256,\n'
    '            "candidate_archive_sha256": self.new["sha256"],\n'
    '            "cells": champion_cells,\n'
    '        }\n'
    '        self.champion_raw = canon(self.champion)\n'
    '        self.trust_result = {\n',
    "champion release fixture",
)
test_release = replace_once(
    test_release,
    '            economics_raw=self.economics_raw,\n'
    '            promotion_builder=self.builder,\n'
    '            economics_builder=econ.validate_report,\n',
    '            economics_raw=self.economics_raw,\n'
    '            champion_raw=self.champion_raw,\n'
    '            promotion_builder=self.builder,\n'
    '            economics_builder=econ.validate_report,\n'
    '            champion_builder=champ.validate_report,\n',
    "champion release build helper",
)
test_release = replace_once(test_release, 'self.assertEqual("titan-v5-release-transaction/v4", first["schema"])', 'self.assertEqual("titan-v5-release-transaction/v5", first["schema"])', "release schema test")
test_release = replace_once(
    test_release,
    '        self.assertEqual(\n'
    '            first["economics"]["per_opponent"],\n',
    '        self.assertEqual(first["champion"]["champion_archive_sha256"], champ.V31_ARCHIVE_SHA256)\n'
    '        self.assertEqual(first["champion"]["champion_source_commit"], champ.V31_SOURCE_COMMIT)\n'
    '        self.assertGreater(first["champion"]["own_sum_delta_vs_v31"], 0)\n'
    '        self.assertEqual(\n'
    '            first["economics"]["per_opponent"],\n',
    "champion receipt assertions",
)
test_release = replace_once(
    test_release,
    '        second = self.build(economics_raw=canon(better))\n'
    '        self.assertNotEqual(first["economics"]["report_sha256"], second["economics"]["report_sha256"])\n',
    '        better_champion = json.loads(json.dumps(self.champion))\n'
    '        better_champion["cells"][0]["candidate_own"] += 1\n'
    '        second = self.build(\n'
    '            economics_raw=canon(better),\n'
    '            champion_raw=canon(better_champion),\n'
    '        )\n'
    '        self.assertNotEqual(first["economics"]["report_sha256"], second["economics"]["report_sha256"])\n',
    "paired evidence identity test",
)
new_release_tests = r'''
    def test_champion_panel_must_match_authenticated_economics_cells(self):
        bad = json.loads(json.dumps(self.champion))
        bad["cells"][0]["candidate_own"] += 1
        with self.assertRaisesRegex(rt.TransactionError, "champion/economics score mismatch"):
            self.build(champion_raw=canon(bad))

    def test_margin_laundering_cannot_clear_v31_own_score_floor(self):
        economics = json.loads(json.dumps(self.economics))
        champion = json.loads(json.dumps(self.champion))
        for econ_cell, champ_cell in zip(economics["cells"], champion["cells"]):
            econ_cell["candidate_own"] = econ_cell["control_own"] + 5
            econ_cell["candidate_rival"] = econ_cell["control_rival"] - 100
            champ_cell["incumbent_own"] = econ_cell["control_own"]
            champ_cell["incumbent_rival"] = econ_cell["control_rival"]
            champ_cell["champion_own"] = econ_cell["control_own"] + 10
            champ_cell["champion_rival"] = econ_cell["control_rival"]
            champ_cell["candidate_own"] = econ_cell["candidate_own"]
            champ_cell["candidate_rival"] = econ_cell["candidate_rival"]
        with self.assertRaisesRegex(rt.TransactionError, "champion gate replay failed"):
            self.build(economics_raw=canon(economics), champion_raw=canon(champion))

    def test_champion_evidence_changes_transition_identity(self):
        first = self.build()
        changed = json.loads(json.dumps(self.champion))
        changed["cells"][0]["champion_own"] -= 1
        second = self.build(champion_raw=canon(changed))
        self.assertNotEqual(first["champion"]["report_sha256"], second["champion"]["report_sha256"])
        self.assertNotEqual(first["transition_id"], second["transition_id"])

'''
test_release = replace_once(test_release, '    def test_trusted_base_gate_must_pass(self):\n', new_release_tests + '    def test_trusted_base_gate_must_pass(self):\n', "champion integration predecessors")
test_path.write_text(test_release, encoding="utf-8")

# Permanent exact-head workflow must execute champion contracts under both modes.
workflow_path = ROOT / ".github/workflows/titan-v5-promotion-release-gates.yml"
workflow = workflow_path.read_text(encoding="utf-8")
workflow = replace_once(
    workflow,
    '            economics_gate.py release_transaction.py promotion_gate.py \\\n            test_economics_gate.py test_release_transaction.py test_promotion_gate.py\n',
    '            economics_gate.py champion_gate.py release_transaction.py promotion_gate.py \\\n            test_economics_gate.py test_champion_gate.py test_release_transaction.py test_promotion_gate.py\n',
    "permanent compile list",
)
workflow = replace_once(
    workflow,
    '            test_economics_gate test_release_transaction test_promotion_gate\n',
    '            test_economics_gate test_champion_gate test_release_transaction test_promotion_gate\n',
    "permanent normal test list",
)
workflow = replace_once(
    workflow,
    '            test_economics_gate test_release_transaction test_promotion_gate\n',
    '            test_economics_gate test_champion_gate test_release_transaction test_promotion_gate\n',
    "permanent optimized test list",
)
workflow_path.write_text(workflow, encoding="utf-8")

readme_path = PG / "README.md"
readme = readme_path.read_text(encoding="utf-8")
marker = "## Exact submitted V3.1 champion ratchet"
if marker not in readme:
    readme += f"""\n\n{marker}\n\nRelease authorization is serial and mandatory: the exact paired economics panel is\ncross-bound cell-for-cell to a champion report carrying the same incumbent/candidate\nraw scores plus exact submitted V3.1 scores. The candidate must not regress incumbent\nown score, must strictly beat V3.1 terminal own score, must create zero new losses, and\nmust preserve own-score and margin safety in every authorized opponent x seat stratum.\nThe champion authority is exact archive `{ '5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361' }`,\nsource `{ 'a90d888f03987ef0b35cfd20ec3519c6144db08a' }`, submission `56172377`.\nThere is no optional programmatic release path around this replay.\n"""
    readme_path.write_text(readme, encoding="utf-8")

print("champion integration working tree prepared")
