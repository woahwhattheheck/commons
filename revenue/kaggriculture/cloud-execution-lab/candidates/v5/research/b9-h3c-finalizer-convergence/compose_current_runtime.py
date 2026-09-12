#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the merged B9 -> H3c authority at the current finalizer seam.

Evidence-only current-V5 composer. It authenticates the current integration
surfaces and the already-merged #13408 semantic authority, then writes scratch
postimages. It never mutates the canonical runtime, CURRENT pointer, archive, or
submission state.

The integration seam is deliberately in TitanAgent._finish_production:
FinalPressureAgent._early_capital_selected() returns only after the current
late-market/finalizer chain. B9 -> H3c therefore runs after that chain and
before quadrant/spatial/history commits, without calling a second producer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[3]

CURRENT_COMMIT = "d61e0333efe5697b56a867ed84a23e909195d3f4"
PINS = {
    "titan_runtime.py": "922c99a571e4ba49726a753739f95afe86e72290",
    "TITAN-CONFIG.json": "ef0bfb1dfa1ce65103a0b178647fc16bc9c7e791",
    "build_integrated.py": "dc11163b9bf2dd257a7f1fb6956943cf66d62143",
    "outer_wrappers_current.py": "c56b65d12a0886ddb2c26bc49a35f76899b48c98",
    "b9_terminal_fertilizer.py": "ed8d6923541e700c3a0ae4b93695bbd56455a3b6",
    "h3c_goose_eod_cap_rescue.py": "2044d6cf1e0c51f95027229863f910aa43ac7008",
}
AUTHORITY = Path("candidates/v5/research/b9-h3c-current-abi")
AUTHORITY_FILES = {
    "outer_wrappers_current.py": AUTHORITY / "outer_wrappers_current.py",
    "b9_terminal_fertilizer.py": AUTHORITY / "vendor/b9_terminal_fertilizer.py",
    "h3c_goose_eod_cap_rescue.py": AUTHORITY / "vendor/h3c_goose_eod_cap_rescue.py",
}
OUTPUT_AUTHORITY = {
    "outer_wrappers_current.py": Path("b9_h3c/outer_wrappers_current.py"),
    "b9_terminal_fertilizer.py": Path("b9_h3c/vendor/b9_terminal_fertilizer.py"),
    "h3c_goose_eod_cap_rescue.py": Path("b9_h3c/vendor/h3c_goose_eod_cap_rescue.py"),
}


def git_blob(data: bytes) -> str:
    if type(data) is not bytes:
        raise TypeError("git_blob requires exact bytes")
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _capture(path: Path) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"authority path must be a regular non-symlink file: {path}")
    return path.read_bytes()


def _require_pin(name: str, raw: bytes) -> bytes:
    actual = git_blob(raw)
    expected = PINS[name]
    if actual != expected:
        raise ValueError(
            f"{name} drift; explicit current-lineage rebase required "
            f"(expected {expected}, got {actual})"
        )
    return raw


def capture_authorities(root: Path = LAB) -> dict[str, bytes]:
    root = Path(root)
    captured = {}
    for name in ("titan_runtime.py", "TITAN-CONFIG.json", "build_integrated.py"):
        captured[name] = _require_pin(name, _capture(root / name))
    for name, relative in AUTHORITY_FILES.items():
        captured[name] = _require_pin(name, _capture(root / relative))
    return captured


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one source-real anchor, found {count}")
    return text.replace(old, new, 1)


def compose_runtime(text: str) -> str:
    if "terminal_fertilizer: bool" in text or "goose_rescue: bool" in text:
        raise ValueError("B9/H3c runtime integration already present")

    text = _replace_once(
        text,
        "    exec_pace: bool = False\n",
        "    exec_pace: bool = False\n"
        "    terminal_fertilizer: bool = False\n"
        "    goose_rescue: bool = False\n",
        "feature fields",
    )
    text = _replace_once(
        text,
        "        bool_fields = (*bool_fields, 'exec_pace')\n",
        "        bool_fields = (*bool_fields, 'exec_pace', "
        "'terminal_fertilizer', 'goose_rescue')\n",
        "exact-bool registry",
    )
    exec_guard = (
        "        if self.exec_pace and (self.consumer != 'frozen' or self.terminal_route):\n"
        "            raise ValueError('exec_pace is the tested nonterminal frozen SELL composition')\n"
    )
    text = _replace_once(
        text,
        exec_guard,
        exec_guard
        + "        if ((self.terminal_fertilizer or self.goose_rescue)\n"
        + "                and (self.consumer != 'frozen' or self.terminal_route)):\n"
        + "            raise ValueError('B9/H3c require the tested nonterminal frozen composition')\n",
        "B9/H3c topology guard",
    )
    text = _replace_once(
        text,
        "        self.committed_seed_retry_module = None\n",
        "        self.committed_seed_retry_module = None\n"
        "        self.b9_h3c = None\n",
        "adapter state slot",
    )
    history_anchor = (
        "        if (f.terminal_history or f.idle_fertilizer or f.crop_release) and self.history is None:\n"
    )
    install = (
        "        if f.terminal_fertilizer or f.goose_rescue:\n"
        "            source = HERE/'b9_h3c/outer_wrappers_current.py'\n"
        "            if not source.is_file():\n"
        "                source = (HERE/'candidates/v5/research/b9-h3c-current-abi'/\n"
        "                          'outer_wrappers_current.py')\n"
        "            module = load('_titan_b9_h3c_current', source, cache=True)\n"
        "            self.b9_h3c = module.B9H3CCurrentABI(\n"
        "                terminal_fertilizer=f.terminal_fertilizer,\n"
        "                goose_rescue=f.goose_rescue)\n"
        "        else:\n"
        "            self.b9_h3c = None\n"
    )
    text = _replace_once(
        text, history_anchor, install + history_anchor, "adapter installation seam"
    )

    helper_anchor = "    def _seed_selected(self, obs, cfg, selected):\n"
    helper = r"""    def _b9_h3c_selected(self, obs, cfg, selected, post):
        # Apply merged #13408 once after late finalizers, never on fallback.
        adapter = self.b9_h3c
        if adapter is None:
            return selected, post
        if self.diagnostics.get('status') != 'completed':
            self.diagnostics['b9_h3c'] = {
                'enabled': True, 'changed': False, 'reason': 'deadline_fallback_identity'
            }
            return selected, post

        # The submitted B9 wrapper owns per-player episode state. Preserve that
        # state transactionally if a current post-unit rebound cannot be proven.
        prior_state = deepcopy(adapter._b9_state)
        try:
            result, report = adapter.transform(obs, cfg, selected)
            rebound = post
            units_changed = (
                result.get('farmer') != selected.get('farmer')
                or result.get('hands') != selected.get('hands')
            )
            if units_changed:
                from scheduler import post_units
                farm, private = post_units(obs, result, cfg)
                rebound = deepcopy(obs)
                rebound['farms'][int(obs['player'])] = farm
                rebound['private'] = private
        except Exception as error:
            adapter._b9_state = prior_state
            self.diagnostics['b9_h3c'] = {
                'enabled': True,
                'changed': False,
                'reason': 'post_unit_rebind_failed',
                'error_type': type(error).__name__,
            }
            return selected, post

        self.diagnostics['b9_h3c'] = report
        checkpoint = getattr(self, '_checkpoint_finalizer', None)
        if callable(checkpoint):
            checkpoint(obs, result, 'b9_h3c')
        return result, rebound

"""
    text = _replace_once(
        text, helper_anchor, helper + helper_anchor, "selected-action helper seam"
    )

    finish_anchor = (
        "        returned = self._feed_stock_selected(obs, cfg or {}, returned)\n"
        "        returned = self._early_capital_selected(obs, cfg or {}, returned)\n"
        "        if self.quadrant is not None:\n"
    )
    finish_replacement = (
        "        returned = self._feed_stock_selected(obs, cfg or {}, returned)\n"
        "        returned = self._early_capital_selected(obs, cfg or {}, returned)\n"
        "        returned, post = self._b9_h3c_selected(obs, cfg or {}, returned, post)\n"
        "        if self.quadrant is not None:\n"
    )
    text = _replace_once(
        text, finish_anchor, finish_replacement, "outer-finalizer integration seam"
    )
    compile(text, "<b9-h3c-current-titan-runtime>", "exec")
    return text


def compose_config(text: str) -> str:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("TITAN-CONFIG.json must be an object")
    if "terminal_fertilizer" in payload or "goose_rescue" in payload:
        raise ValueError("B9/H3c config keys already present")
    if payload.get("exec_pace") is not False:
        raise ValueError("expected current exec_pace=false anchor")
    payload["terminal_fertilizer"] = False
    payload["goose_rescue"] = False
    return json.dumps(payload, indent=2) + "\n"


def compose_build(text: str) -> str:
    marker = "    mapping['seed_retry.py']='../cloud-committed-seed-retry/seed_retry.py'\n"
    if "b9_h3c/outer_wrappers_current.py" in text:
        raise ValueError("B9/H3c archive mapping already present")
    addition = marker + (
        "    mapping['b9_h3c/outer_wrappers_current.py']='b9_h3c/outer_wrappers_current.py'\n"
        "    mapping['b9_h3c/vendor/b9_terminal_fertilizer.py']='b9_h3c/vendor/b9_terminal_fertilizer.py'\n"
        "    mapping['b9_h3c/vendor/h3c_goose_eod_cap_rescue.py']='b9_h3c/vendor/h3c_goose_eod_cap_rescue.py'\n"
    )
    out = _replace_once(text, marker, addition, "release source mapping seam")
    compile(out, "<b9-h3c-current-build-integrated>", "exec")
    return out


def materialize(root: Path, output: Path) -> dict:
    root = Path(root).resolve(strict=True)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)

    captured = capture_authorities(root)
    rendered = {
        "titan_runtime.py": compose_runtime(
            captured["titan_runtime.py"].decode("utf-8")
        ).encode("utf-8"),
        "TITAN-CONFIG.json": compose_config(
            captured["TITAN-CONFIG.json"].decode("utf-8")
        ).encode("utf-8"),
        "build_integrated.py": compose_build(
            captured["build_integrated.py"].decode("utf-8")
        ).encode("utf-8"),
    }
    for name, relative in OUTPUT_AUTHORITY.items():
        rendered[str(relative)] = captured[name]

    output.mkdir(parents=True)
    for relative, raw in rendered.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    receipt = {
        "schema": "titan.v5.b9-h3c-finalizer-convergence/v1",
        "base_commit": CURRENT_COMMIT,
        "production_activation": False,
        "semantic_authority": {
            "outer_wrappers_git_blob": PINS["outer_wrappers_current.py"],
            "b9_git_blob": PINS["b9_terminal_fertilizer.py"],
            "h3c_git_blob": PINS["h3c_goose_eod_cap_rescue.py"],
            "order": ["terminal_fertilizer", "goose_rescue"],
        },
        "integration": {
            "producer_calls_added": 0,
            "fallback_behavior": "identity",
            "seam": "after _early_capital_selected; before quadrant/spatial/history commit",
            "unit_change_post_snapshot": "recomputed with current scheduler.post_units",
        },
        "inputs": {name: git_blob(raw) for name, raw in captured.items()},
        "outputs": {name: git_blob(raw) for name, raw in rendered.items()},
    }
    (output / "B9-H3C-MATERIALIZATION.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=LAB)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.root, args.out)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
