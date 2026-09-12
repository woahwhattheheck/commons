# SPDX-License-Identifier: Apache-2.0
"""Regression coverage for standalone TITAN release closure."""
import io
import json
import tarfile

import build_integrated


def test_enabled_town_procurement_is_in_standalone_archive():
    config = json.loads((build_integrated.ROOT / "TITAN-CONFIG.json").read_text())
    assert config["town_procurement"] is True

    data, _manifest, receipt = build_integrated.render()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        names = set(archive.getnames())

    assert "main.py" in names
    assert "town_procurement.py" in names
    assert receipt["runtime_files"] == len(build_integrated.source_files())
