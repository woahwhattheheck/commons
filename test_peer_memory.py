#!/usr/bin/env python3
"""Peer memory couples goal/state to evidence-accepted component evolution."""
import memory_board


def row(n, memory_kind, body, **fields):
    ts = "2026-08-26T20:00:%02dZ" % n
    meta = {
        "from": "KITE", "to": "MEMORY", "id": "kite-memory-entry-%02d" % n,
        "ts": ts, "kind": "MEMORY_APPEND", "actor_id": "KITE",
        "memory_id": "kite-memory-create-01", "memory_kind": memory_kind,
    }
    meta.update(fields)
    return ts, meta, body


def main():
    create_ts = "2026-08-26T20:00:00Z"
    rows = [(create_ts, {
        "from": "KITE", "to": "MEMORY", "id": "kite-memory-create-01",
        "ts": create_ts, "kind": "MEMORY_CREATE", "actor_id": "KITE",
        "memory_id": "kite-memory-create-01", "memory_kind": "ROLE",
        "actor_class": "CLOUD_MODEL", "intelligence_kind": "LLM", "surface": "Commons",
    }, "Peer builder")]
    rows += [
        row(1, "GOAL", "Ship a buyer proof", goal_id="buyer-proof", goal_state="OPEN"),
        row(2, "STATE", "Buyer needs live evidence", goal_id="buyer-proof",
            state="needs exact receipt", trajectory_id="outreach-001"),
        row(3, "SKILL", "Use an exact live receipt", component="proof",
            tags="buyer,receipt"),
        row(4, "SKILL", "Keep reply concise", component="reply"),
        row(5, "EXPERIENCE", "Buyer asked for proof before payment", goal_id="buyer-proof",
            trajectory_id="outreach-001", action="send offer", observation="proof requested",
            outcome="follow-up", tags="buyer,proof,receipt"),
        row(6, "SKILL_PATCH", "Use an invented testimonial", component="proof",
            trajectory_id="outreach-001"),
        row(7, "VALIDATION", "Rejected by evidence check", component="proof",
            patch_entry_id="kite-memory-entry-06", validation_state="REJECTED"),
        row(8, "SKILL_PATCH", "Attach current-main SHA and live receipt", component="proof",
            trajectory_id="outreach-001", tags="buyer,receipt"),
        row(9, "VALIDATION", "Development evidence passed", component="proof",
            patch_entry_id="kite-memory-entry-08", validation_state="ACCEPTED"),
        row(10, "VALIDATION", "Must not validate a missing patch", component="proof",
            patch_entry_id="kite-memory-missing-10", validation_state="ACCEPTED"),
    ]
    actors, boards = memory_board.derive(rows)
    board = boards["KITE"]
    assert actors["KITE"]["entry_count"] == 10
    assert len(board["entries"]) == 10
    assert board["open_goal_count"] == 1
    active = {entry["component"]: entry for entry in board["experiential_memory"]["active_components"]}
    assert active["proof"]["entry_id"] == "kite-memory-entry-08", active
    assert active["proof"]["validation_state"] == "ACCEPTED"
    assert active["reply"]["entry_id"] == "kite-memory-entry-04"
    patches = {entry["entry_id"]: entry["validation_state"]
               for entry in board["experiential_memory"]["candidate_patches"]}
    assert patches == {"kite-memory-entry-06": "REJECTED", "kite-memory-entry-08": "ACCEPTED"}
    assert board["trajectories"][0]["observation"] == "proof requested"
    context = memory_board.retrieve_for_state(board, "buyer proof", "needs receipt", 3)
    assert context[0]["entry_id"] in {"kite-memory-entry-05", "kite-memory-entry-08"}, context
    rendered = memory_board._memory_html(actors["KITE"], board, "test", "")
    assert "Working memory" in rendered and "Candidate patches" in rendered
    print("PEER MEMORY EVOLUTION TEST: ALL PASS")


if __name__ == "__main__":
    main()
