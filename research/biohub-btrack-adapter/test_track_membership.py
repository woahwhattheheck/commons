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


def track_from_refs(payload: dict[str, list[Any]], track_id: int, refs: list[int]) -> FakeTrack:
    return FakeTrack(
        ID=track_id,
        refs=refs,
        dummy=[False] * len(refs),
        t=[payload["t"][ref] for ref in refs],
        x=[payload["x"][ref] for ref in refs],
        y=[payload["y"][ref] for ref in refs],
        z=[payload["z"][ref] for ref in refs],
        detection_tags=[payload["commons_detection_id"][ref] for ref in refs],
        children=[],
    )


class TrackMembershipTests(unittest.TestCase):
    def test_real_ref_cannot_appear_in_two_tracklets(self):
        scale = Scale()
        bounds = VoxelBounds(0, 20, 0, 20, 0, 20)
        detections = [
            Detection("a", 0, 10, 5, 5, 5),
            Detection("a", 1, 11, 5, 6, 5),
            Detection("a", 1, 12, 5, 4, 5),
        ]
        payload, ref_map = build_btrack_payload(detections, scale, bounds)
        tracks = [
            track_from_refs(payload, 1, [0, 1]),
            track_from_refs(payload, 2, [0, 2]),
        ]
        with self.assertRaisesRegex(AdapterError, "appears in multiple track observations"):
            tracks_to_rows("a", detections, tracks, ref_map, scale)

    def test_nonpositive_track_ids_are_rejected(self):
        scale = Scale()
        bounds = VoxelBounds(0, 20, 0, 20, 0, 20)
        detections = [Detection("a", 0, 10, 5, 5, 5)]
        payload, ref_map = build_btrack_payload(detections, scale, bounds)
        for track_id in (0, -1):
            with self.subTest(track_id=track_id):
                track = track_from_refs(payload, track_id, [0])
                with self.assertRaisesRegex(AdapterError, "track ID must be positive"):
                    tracks_to_rows("a", detections, [track], ref_map, scale)

    def test_self_child_declaration_is_rejected_but_self_parent_root_is_allowed(self):
        scale = Scale()
        bounds = VoxelBounds(0, 20, 0, 20, 0, 20)
        detections = [Detection("a", 0, 10, 5, 5, 5)]
        payload, ref_map = build_btrack_payload(detections, scale, bounds)

        root = track_from_refs(payload, 1, [0])
        root.parent = 1
        tracks_to_rows("a", detections, [root], ref_map, scale)

        root.children = [1]
        with self.assertRaisesRegex(AdapterError, "cannot declare itself as a child"):
            tracks_to_rows("a", detections, [root], ref_map, scale)

    def test_duplicate_child_declaration_is_rejected(self):
        scale = Scale()
        bounds = VoxelBounds(0, 20, 0, 20, 0, 20)
        detections = [
            Detection("a", 0, 10, 5, 5, 5),
            Detection("a", 1, 11, 5, 6, 5),
        ]
        payload, ref_map = build_btrack_payload(detections, scale, bounds)
        parent = track_from_refs(payload, 1, [0])
        child = track_from_refs(payload, 2, [1])
        parent.children = [2, 2]
        child.parent = 1

        with self.assertRaisesRegex(AdapterError, "declares duplicate child 2"):
            tracks_to_rows("a", detections, [parent, child], ref_map, scale)

    def test_parent_relation_requires_reciprocal_child_declaration(self):
        scale = Scale()
        bounds = VoxelBounds(0, 20, 0, 20, 0, 20)
        detections = [
            Detection("a", 0, 10, 5, 5, 5),
            Detection("a", 1, 11, 5, 6, 5),
            Detection("a", 1, 12, 5, 4, 5),
        ]
        payload, ref_map = build_btrack_payload(detections, scale, bounds)
        parent = track_from_refs(payload, 1, [0])
        child_one = track_from_refs(payload, 2, [1])
        child_two = track_from_refs(payload, 3, [2])
        child_one.parent = 1
        child_two.parent = 1

        with self.assertRaisesRegex(AdapterError, "missing reciprocal parent child declaration"):
            tracks_to_rows("a", detections, [parent, child_one, child_two], ref_map, scale)

        parent.children = [2, 3]
        rows = tracks_to_rows("a", detections, [parent, child_one, child_two], ref_map, scale)
        edge_rows = [row for row in rows if row["row_type"] == "edge"]
        self.assertEqual(2, len(edge_rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
