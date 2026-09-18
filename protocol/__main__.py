"""Conformance CLI: python3 -m protocol --self-test"""
from __future__ import annotations

import json
import sys

from protocol.emit import EXAMPLES, continue_from_observation
from protocol.projector import project
from protocol.schema import PROTOCOL_ID, PROTOCOL_VERSION


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    events = list(EXAMPLES.values())
    first = project(events, now="2026-08-28T09:30:00Z")
    second = project(events, now="2026-08-28T09:30:00Z")
    if first["digest"] != second["digest"]:
        sys.stderr.write("protocol projector is not deterministic\n")
        return 1
    if first["protocol"] != PROTOCOL_ID or first["protocol_version"] != PROTOCOL_VERSION:
        sys.stderr.write("protocol id mismatch\n")
        return 1
    cont = continue_from_observation(first)
    if cont.get("replay_finished_prompt") is not False:
        sys.stderr.write("continuation must refuse prompt replay\n")
        return 1
    if "--json" in argv:
        sys.stdout.write(json.dumps(first, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write("commons-protocol/v0.1 conformance: PASS digest=%s\n" % first["digest"][:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
