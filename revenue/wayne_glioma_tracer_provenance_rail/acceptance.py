#!/usr/bin/env python3
"""Deterministic 100-episode synthetic acceptance generator."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _ts(base: datetime, minutes: int) -> str:
    return (base + timedelta(minutes=minutes)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate(episodes: int = 100) -> dict[str, Any]:
    if isinstance(episodes, bool) or not isinstance(episodes, int) or episodes < 1:
        raise ValueError("episodes must be a positive integer")
    events: list[dict[str, Any]] = []
    base = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

    # One released batch per four episodes, with every fifth new batch marked as a
    # resynthesis of the preceding same-tracer batch.
    batch_count = (episodes + 3) // 4
    for b in range(1, batch_count + 1):
        batch_id = f"BATCH-{b:03d}"
        parent = f"BATCH-{b-1:03d}" if b > 1 and b % 5 == 0 else None
        events.append({
            "event_id": f"EV-BATCH-{b:03d}",
            "type": "batch",
            "batch_id": batch_id,
            "synthesis_id": f"SYNTH-{b:03d}",
            "tracer_code": "F18-SYNTHETIC-TRACER",
            "qc_hash": _h(f"qc:{batch_id}"),
            "release_state": "RELEASED",
            "resynthesis_of": parent,
        })

    for i in range(1, episodes + 1):
        sid = f"SUBJ-{i:04d}"
        dose_id = f"DOSE-{i:04d}"
        batch_id = f"BATCH-{((i-1)//4)+1:03d}"
        events.append({"event_id": f"EV-SUBJ-{i:04d}", "type": "subject", "subject_id": sid, "protocol_version": 1 + (i % 3 == 0)})
        events.append({
            "event_id": f"EV-DOSE-{i:04d}", "type": "dose", "dose_id": dose_id,
            "subject_id": sid, "batch_id": batch_id,
            "administered_at": _ts(base, i * 20),
            "administered_activity_bq": 180_000_000 + i * 10_000,
        })

        # Every tenth episode exercises failed-acquisition + retry and a delayed
        # successful acquisition. Everyone else gets one accepted acquisition.
        if i % 10 == 0:
            failed = f"SCAN-{i:04d}-A"
            scan = f"SCAN-{i:04d}-B"
            events.append({
                "event_id": f"EV-SCAN-{i:04d}-A", "type": "scan", "accession_id": failed,
                "subject_id": sid, "dose_id": dose_id, "acquired_at": _ts(base, i * 20 + 55),
                "state": "FAILED", "timing_state": "ON_TIME", "retry_of": None,
            })
            events.append({
                "event_id": f"EV-SCAN-{i:04d}-B", "type": "scan", "accession_id": scan,
                "subject_id": sid, "dose_id": dose_id, "acquired_at": _ts(base, i * 20 + 120),
                "state": "ACQUIRED", "timing_state": "DELAYED", "retry_of": failed,
            })
        else:
            scan = f"SCAN-{i:04d}-A"
            events.append({
                "event_id": f"EV-SCAN-{i:04d}-A", "type": "scan", "accession_id": scan,
                "subject_id": sid, "dose_id": dose_id, "acquired_at": _ts(base, i * 20 + 55),
                "state": "ACQUIRED", "timing_state": "DELAYED" if i % 9 == 0 else "ON_TIME", "retry_of": None,
            })

        seg1 = f"SEG-{i:04d}-V1"
        map1 = f"MAP-{i:04d}-V1"
        events.append({
            "event_id": f"EV-SEG-{i:04d}-V1", "type": "segmentation", "segmentation_id": seg1,
            "subject_id": sid, "accession_id": scan, "version": 1,
            "artifact_hash": _h(f"seg:{seg1}"), "parent_segmentation_id": None,
        })
        events.append({
            "event_id": f"EV-MAP-{i:04d}-V1", "type": "map", "map_id": map1,
            "subject_id": sid, "accession_id": scan, "segmentation_id": seg1, "version": 1,
            "algorithm_version": "synthetic-map-algorithm-v1", "artifact_hash": _h(f"map:{map1}"),
            "parent_map_id": None,
        })
        final_map = map1

        # Revised segmentation/map lineage exercises exact parent/version custody.
        if i % 7 == 0:
            seg2 = f"SEG-{i:04d}-V2"
            map2 = f"MAP-{i:04d}-V2"
            events.append({
                "event_id": f"EV-SEG-{i:04d}-V2", "type": "segmentation", "segmentation_id": seg2,
                "subject_id": sid, "accession_id": scan, "version": 2,
                "artifact_hash": _h(f"seg:{seg2}"), "parent_segmentation_id": seg1,
            })
            events.append({
                "event_id": f"EV-MAP-{i:04d}-V2", "type": "map", "map_id": map2,
                "subject_id": sid, "accession_id": scan, "segmentation_id": seg2, "version": 2,
                "algorithm_version": "synthetic-map-algorithm-v2", "artifact_hash": _h(f"map:{map2}"),
                "parent_map_id": map1,
            })
            final_map = map2

        events.append({
            "event_id": f"EV-HANDOFF-{i:04d}", "type": "handoff", "handoff_id": f"HANDOFF-{i:04d}",
            "subject_id": sid, "map_id": final_map, "state": "ACKED",
            "destination_role": "synthetic-study-planning-reviewer", "observed_at": _ts(base, i * 20 + 180),
        })

        # Byte-identical retry events are intentional transport replays. They must
        # create no duplicate lineage effect.
        if i % 13 == 0:
            events.append(dict(events[-1]))

    # Deliberately ambiguous cross-subject maps: valid schemas and hashes, but each
    # points at another subject's scan/segmentation. They must be quarantined and
    # must never appear in accepted map lineage.
    if episodes >= 4:
        for n, (subject_i, source_i) in enumerate(((1, 2), (2, 3), (3, 4)), start=1):
            subject = f"SUBJ-{subject_i:04d}"
            source_subject = f"SUBJ-{source_i:04d}"
            source_scan = f"SCAN-{source_i:04d}-A"
            if source_i % 10 == 0:
                source_scan = f"SCAN-{source_i:04d}-B"
            source_seg = f"SEG-{source_i:04d}-V2" if source_i % 7 == 0 else f"SEG-{source_i:04d}-V1"
            events.append({
                "event_id": f"EV-AMBIG-MAP-{n}", "type": "map", "map_id": f"AMBIG-MAP-{n}",
                "subject_id": subject, "accession_id": source_scan, "segmentation_id": source_seg,
                "version": 99, "algorithm_version": "synthetic-ambiguous-control",
                "artifact_hash": _h(f"ambig:{subject}:{source_subject}"), "parent_map_id": None,
            })

    return {"review_owner_role": "Wayne State study provenance reviewer", "events": events}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    payload = generate(args.episodes)
    Path(args.output).write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "episodes": args.episodes, "events": len(payload["events"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
