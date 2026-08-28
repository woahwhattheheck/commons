"""Portable Commons Protocol v0.1.

A unidirectional projector/observer of live work. Same protocol everywhere.
Not a manager, supervisor, planner, or orchestrator.
"""
from protocol.emit import continue_from_observation, emit
from protocol.events import event_id_for, parse_event, parse_events
from protocol.projector import project, project_bytes, route_work
from protocol.schema import (
    CLASSIFICATIONS,
    EVENT_KINDS,
    EVIDENCE_GRADES,
    PROTOCOL_ID,
    PROTOCOL_VERSION,
    SESSION_STATES,
    SNAPSHOT_SCHEMA,
    UNKNOWN,
)

__all__ = [
    "CLASSIFICATIONS",
    "EVENT_KINDS",
    "EVIDENCE_GRADES",
    "PROTOCOL_ID",
    "PROTOCOL_VERSION",
    "SESSION_STATES",
    "SNAPSHOT_SCHEMA",
    "UNKNOWN",
    "continue_from_observation",
    "emit",
    "event_id_for",
    "parse_event",
    "parse_events",
    "project",
    "project_bytes",
    "route_work",
]
