# SPDX-License-Identifier: Apache-2.0
"""W2 pre-consumer native integration; does not implement the CARE policy.

Consumes SECONDHELP's exact r04_dead_feed_care.py. The opt-in hook runs before
selected-action consumers create unit snapshots, not after receipt finalization.
The original producer action remains a completed fallback while optional work is
loading/executing. No production file or configuration is changed by this CLI.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil

FEATURE_BEFORE = "    early_capital: bool = False\n"
FEATURE_AFTER = FEATURE_BEFORE + "    r04_dead_feed_care: bool = False\n"
SELECT_BEFORE = """                selected = self.production.act(obs)
                self.selected = deepcopy(selected)
                selected_checkpoint = (self.selected, self.controller.cur)
                fallback = selected_checkpoint[0]
"""
SELECT_AFTER = """                selected = self.production.act(obs)
                # W2-BEGIN: optional CARE completes before unit-snapshot capture.
                if self.features.r04_dead_feed_care:
                    # Retain the completed parent if import/rewrite is cancelled.
                    parent_checkpoint = (deepcopy(selected), self.controller.cur)
                    fallback = parent_checkpoint[0]
                    selected_checkpoint = parent_checkpoint
                    self.selected = parent_checkpoint[0]
                    stage = 'dead_feed_care'
                    care = load('_titan_dead_feed_care',
                                HERE/'r04_dead_feed_care.py', cache=True)
                    selected = care.apply_dead_feed_care(
                        selected, obs, cfg, enabled=True)
                # W2-END: existing detached selected checkpoint and consumers.
                self.selected = deepcopy(selected)
                selected_checkpoint = (self.selected, self.controller.cur)
                fallback = selected_checkpoint[0]
"""


def _class(tree: ast.Module, name: str) -> ast.ClassDef:
    found = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name]
    if len(found) != 1:
        raise ValueError(f"expected exactly one {name} class")
    return found[0]


def _segment(text: str, node: ast.AST) -> str:
    return ''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])


def compose_runtime(text: str) -> str:
    """Modify only two verified native seams; compatible unrelated edits survive.

    The caller must authenticate the exact input and helper before materializing.
    A different implementation of either seam is not silently adapted.
    """
    tree = ast.parse(text)
    features = _class(tree, 'Features')
    agent = _class(tree, 'TitanAgent')
    acts = [n for n in agent.body if isinstance(n, ast.FunctionDef) and n.name == 'act']
    if len(acts) != 1:
        raise ValueError('expected exactly one TitanAgent.act')
    ftext, atext = _segment(text, features), _segment(text, acts[0])
    if 'W2-BEGIN:' in text or 'r04_dead_feed_care: bool' in text:
        if (text.count(SELECT_AFTER) != 1 or text.count(FEATURE_AFTER) != 1
                or SELECT_AFTER not in atext or FEATURE_AFTER not in ftext):
            raise ValueError('partial or drifted W2 integration')
        restored = text.replace(SELECT_AFTER, SELECT_BEFORE, 1).replace(
            FEATURE_AFTER, FEATURE_BEFORE, 1)
        if compose_runtime(restored) != text:
            raise ValueError('noncanonical W2 integration')
        return text
    if (text.count(SELECT_BEFORE) != 1 or SELECT_BEFORE not in atext
            or text.count(FEATURE_BEFORE) != 1 or FEATURE_BEFORE not in ftext):
        raise ValueError('native production/checkpoint or feature seam drifted')
    result = text.replace(SELECT_BEFORE, SELECT_AFTER, 1).replace(
        FEATURE_BEFORE, FEATURE_AFTER, 1)
    ast.parse(result)
    return result


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialize(package: Path, helper: Path, output: Path, runtime_sha: str,
                helper_sha: str, *, enable: bool = False) -> dict:
    """Create an isolated candidate; never overwrite an existing destination."""
    package, helper, output = package.resolve(), helper.resolve(), output.resolve()
    if output.exists() or output == package or package in output.parents:
        raise ValueError('output must be a new path outside the input package')
    runtime = package/'titan_runtime.py'
    if digest(runtime) != runtime_sha or digest(helper) != helper_sha:
        raise ValueError('runtime/helper source authentication failed')
    if (package/'r04_dead_feed_care.py').exists():
        raise ValueError('input already contains a W2 helper; explicit composition required')
    functions = [n.name for n in ast.parse(helper.read_text()).body
                 if isinstance(n, ast.FunctionDef)]
    if 'apply_dead_feed_care' not in functions:
        raise ValueError('missing SECONDHELP public API')
    before = runtime.read_text()
    after = compose_runtime(before)
    config = json.loads((package/'TITAN-CONFIG.json').read_text())
    if 'r04_dead_feed_care' in config:
        raise ValueError('input has existing W2 config; explicit composition required')
    # Every parse/authentication check completes before creating the candidate.
    shutil.copytree(package, output, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (output/'titan_runtime.py').write_text(after)
    shutil.copyfile(helper, output/'r04_dead_feed_care.py')
    if enable:
        config['r04_dead_feed_care'] = True
        (output/'TITAN-CONFIG.json').write_text(json.dumps(config, indent=2)+'\n')
    return {'runtime_input_sha256': runtime_sha,
            'runtime_output_sha256': digest(output/'titan_runtime.py'),
            'helper_sha256': helper_sha, 'enabled_in_scratch_only': enable,
            'untouched_runtime_bytes': after.replace(SELECT_AFTER, SELECT_BEFORE, 1).replace(
                FEATURE_AFTER, FEATURE_BEFORE, 1) == before}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--helper', type=Path, required=True)
    p.add_argument('--runtime-sha256', required=True)
    p.add_argument('--helper-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--enable', action='store_true', help='enable only the new scratch copy')
    a = p.parse_args()
    print(json.dumps(materialize(a.package, a.helper, a.output, a.runtime_sha256,
                                a.helper_sha256, enable=a.enable), indent=2))
