# Clock fanout / Autofab decision

Decision id: `codex-dir20-clock-fanout-autofab-20260830-01`

## Selected value

- **Autofab N:** 24 proposed residents.
- **Purpose:** first datacenter AGENT SWARM; give each resident one isolated Commons work shard.
- **Clock mapping:** one proposed resident per measured clock junction, preserving the decoded per-ring fanout `2,2,3,2,3,2,2,2,2,3,1`.
- **Destination rule:** derive junction destinations from the current file at any future actuation; this decision invents no address or dock.

## Evidence

Integrated tick-topology packet: commit `35e3861fa7eef4242c04f9545043fac5fb30c383`.

Its isolated-snapshot read recorded:

- snapshot SHA-256 `1cf1a9f3c1649b82d19fc78440d468483d5d4bd3bff49a3da1cc0179a3f4911d`;
- 586,918 bytes;
- 22,563 records;
- 11 rings;
- 24 clock junctions;
- fanout `2,2,3,2,3,2,2,2,2,3,1` (sum 24);
- every decoded clock output inside the clock bank below state address 288.

## Why 24

Twenty-four is the only already-measured concurrency count directly attached to the requested clock-fanout choice. Choosing 11 would collapse multiple existing clock contacts into one ring-level worker. Choosing more than 24 would invent fanout not present in the evidence. N=24 uses the measured topology without claiming new device capacity.

The purpose composes with DIRECTIVES item 19, which names AGENT SWARM as the first datacenter workload. A work shard is queue metadata, not host inference.

## Boundary

This is a public-tree decision artifact, not a live machine result. No `.mno` file was opened or written for this land. No fabrication, pulse, injection, 337 fire, or 78 actuation occurred. The host computes zero inference. Germ dock/magic remains a separate unresolved path and no value is invented for it.
