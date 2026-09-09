from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from adapter import AdapterError, Detection, Scale, VoxelBounds, build_btrack_payload, tracks_to_rows


@dataclass
class FakeTrack:
    ID: int
    refs: list[int]
    dummy: list[bool]
    t: list[int]
    x: list[float]
    y: list[float]
    z: list[float]
    detection_tags: list[int | float]
    parent: int | None = None
    children: list[int] | None = None

    @property
    def properties(self) -> dict[str, list[Any]]:
        return {"commons_detection_id": self.detection_tags}


class AllDummyTrackTests(unittest.TestCase):
    def test_all_dummy_track_is_rejected_but_real_plus_dummy_is_allowed(self):
        scale = Scale()
        bounds = VoxelBounds(0, 20, 0, 20, 0, 20)
        detections = [Detection("a", 0, 10, 5, 5, 5)]
        payload, ref_map = build_btrack_payload(detections, scale, bounds)

        real_plus_dummy = FakeTrack(
            ID=1,
            refs=[0, -1],
            dummy=[False, True],
            t=[payload["t"][0], 1],
            x=[payload["x"][0], payload["x"][0]],
            y=[payload["y"][0], payload["y"][0]],
            z=[payload["z"][0], payload["z"][0]],
            detection_tags=[payload["commons_detection_id"][0], float("nan")],
            children=[],
        )
        rows = tracks_to_rows("a", detections, [real_plus_dummy], ref_map, scale)
        self.assertEqual(1, sum(row["row_type"] == "node" for row in rows))
        self.assertEqual(0, sum(row["row_type"] == "edge" for row in rows))

        all_dummy = FakeTrack(
            ID=2,
            refs=[-1],
            dummy=[True],
            t=[0],
            x=[0.0],
            y=[0.0],
            z=[0.0],
            detection_tags=[float("nan")],
            children=[],
        )
        with self.assertRaisesRegex(AdapterError, "track 2 has no real observations"):
            tracks_to_rows("a", detections, [all_dummy], ref_map, scale)


if __name__ == "__main__":
    unittest.main(verbosity=2)
