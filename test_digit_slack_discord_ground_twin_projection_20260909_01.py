"""Regression: DIGIT Slack/Discord ground twin must appear in the committed tracker."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
FID = "digit-slack-discord-ground-twin-20260909-01"


def test_digit_slack_discord_ground_twin_projection_20260909_01():
    registry_path = ROOT / "features" / "registry" / ("%s.json" % FID)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["id"] == FID
    assert registry["schema"] == "commons-feature-v1"
    for rel in list(registry.get("claimed_paths") or []) + list(registry.get("test_paths") or []):
        assert (ROOT / rel).is_file(), rel

    committed = json.loads((ROOT / "feature-tracker.json").read_text(encoding="utf-8"))
    by_id = {row.get("id"): row for row in committed.get("features") or []}
    assert FID in by_id, "committed feature-tracker.json missing %s" % FID
    row = by_id[FID]
    assert row.get("source_status") == "SOURCE_BUILT", row
    assert row.get("test_status") == "TESTS_PRESENT", row
    assert not row.get("claimed_paths_missing"), row.get("claimed_paths_missing")
    assert not row.get("test_paths_missing"), row.get("test_paths_missing")
    assert row.get("live_status") == "UNMEASURED", row.get("live_status")
    html = (ROOT / "feature-tracker.html").read_text(encoding="utf-8")
    assert FID in html

    registry_ids = {p.stem for p in (ROOT / "features" / "registry").glob("*.json")}
    missing = sorted(registry_ids - set(by_id))
    assert missing == [], "committed projection missing registry ids: %s" % missing

    sys.path.insert(0, str(ROOT / "host"))
    import feature_tracker as ft
    live = ft.project(str(ROOT))
    live_ids = {r.get("id") for r in live.get("features") or []}
    assert FID in live_ids
    assert live_ids >= registry_ids


if __name__ == "__main__":
    test_digit_slack_discord_ground_twin_projection_20260909_01()
    print("ok")
