from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent

def test_registry():
    row = json.loads((ROOT / "features/registry/digit-seat-trail-20260909-01.json").read_text(encoding="utf-8"))
    assert row["id"] == "digit-seat-trail-20260909-01"
    assert "boards.html" in row["claimed_paths"]

def test_evidence_schema():
    ev = json.loads((ROOT / "features/evidence/ev-digit-seat-trail-git-20260909-01.json").read_text(encoding="utf-8"))
    assert ev["schema"] == "commons-feature-evidence-v1"
    assert ev["kind"] == "GIT_SHA"
