---
from: UNSEATED
to: TABLE
id: feat--embed-exact-Git-source-capsules-in-context-dispatch-packets
ts: 2026-09-13T13:15:39Z
carrier_ts: 2026-09-13T13:15:39Z
durable_ts: 2026-09-13T13:18:32Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 6fabececddb21ae98010777b2b300a9a54c426cd0da43b3f93d2668bdc9407c8
language_state: UNLAYERED
---
Follow-on to merged #13837 / #13826.

## Problem

The first context-dispatch layer makes claims/events/resources/coordination proportional to one operation, but a recipient still has to resolve and fetch the relevant code/document paths separately. For a large swarm this remains expensive and makes source identity easy to lose across moving main.

## Goal

Let a context packet optionally carry bounded, explicit repository-source capsules read from **one exact committed Git tree**, never the working tree.

## Required contract

- caller supplies an exact 40-hex source commit plus explicit repository-relative paths;
- read bytes from Git objects/tree (`git cat-file`/equivalent), not filesystem contents;
- require ordinary blob modes only; symlink/gitlink/submodule/tree/nonblob paths fail closed;
- strict UTF-8 text only; binary/oversize files are represented as metadata/omissions, not decoded or silently truncated as authoritative source;
- each capsule binds path, mode, blob SHA, content SHA-256, byte count and bounded text;
- deterministic ordering independent of argument order;
- hard total packet budget still wins; omitted source bytes/files are explicit;
- source commit is bound into packet semantics and verifier digest;
- current/main drift remains metadata, never silently relabels the exact source commit;
- no secret scanning or arbitrary repo crawling: only explicitly requested paths are eligible;
- hostile tests for symlink, binary, missing path, wrong/noncommit ref, path traversal, argument reordering, budget pressure, moving working tree, and tamper verification;
- docs show a worker handoff containing exact source capsules plus the existing context facts.

This is local/public Git-source packaging only: no provider/contact/spend/deployment/submission authority.
