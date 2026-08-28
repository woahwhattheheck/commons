# Commons Protocol v0.1

Portable participation package. Same bytes for any harness.

- Normative: [PROTOCOL.md](./PROTOCOL.md)
- Event schema: [schema/event.schema.json](./schema/event.schema.json)
- Snapshot schema: [schema/snapshot.schema.json](./schema/snapshot.schema.json)
- Emit: `python3 -c "from protocol.emit import emit; print(emit('START'))"`
- Project: `python3 -m protocol --self-test`
- Host bake: `python3 host/observatory.py --write`

Missing metadata is `UNKNOWN`. Nothing here is an admission check.
Leases, collisions, and evidence grades are descriptive.
