from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_feature_receipt():
    md = (ROOT / "p/digit-go-wave-feature-20260905-01.md").read_text(encoding="utf-8")
    assert "lane: FEATURES" in md
    assert "7542b716" in md or "7542b716faba3f551636e99715317eb26f4d012d" in md

def test_registry_row():
    import json
    row = json.loads((ROOT / "features/registry/digit-hermetic-parents-fix-20260905-01.json").read_text(encoding="utf-8"))
    assert row["id"] == "digit-hermetic-parents-fix-20260905-01"
    assert "test_digit_hermetic_parents_fix_20260905_02.py" in row["test_paths"]
