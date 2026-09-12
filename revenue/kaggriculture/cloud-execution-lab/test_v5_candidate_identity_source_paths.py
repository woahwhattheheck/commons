# SPDX-License-Identifier: Apache-2.0
"""Regression contracts for canonical V5 candidate source identity paths."""

from pathlib import Path
import tempfile

from v5_candidate_identity import build_manifest


def _spec(source: str):
    return {
        "base_id": "main@abc123",
        "engine_id": "engine@3c202c7e",
        "opponent_pack_id": "top30@v1",
        "config": {"enabled": True},
        "components": [
            {
                "name": "candidate",
                "source": source,
                "activation": {"enabled": True},
            }
        ],
    }


def _check_same_identity(root: Path, *sources: str) -> None:
    manifests = [build_manifest(root, _spec(source)) for source in sources]
    candidate_ids = {manifest["candidate_id"] for manifest in manifests}
    if len(candidate_ids) != 1:
        raise AssertionError((sources, candidate_ids))
    recorded_sources = {manifest["components"][0]["source"] for manifest in manifests}
    if recorded_sources != {"candidate.py"}:
        raise AssertionError((sources, recorded_sources))


def test_lexical_aliases_collapse_to_authenticated_source():
    with tempfile.TemporaryDirectory() as parent:
        root = Path(parent)
        (root / "candidate.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "sub").mkdir()
        _check_same_identity(root, "candidate.py", "./candidate.py", "sub/../candidate.py")


def test_in_root_symlink_alias_collapses_to_authenticated_source():
    with tempfile.TemporaryDirectory() as parent:
        root = Path(parent)
        (root / "candidate.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "alias.py").symlink_to(root / "candidate.py")
        _check_same_identity(root, "candidate.py", "alias.py")


def run():
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    run()
