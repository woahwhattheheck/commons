# CLOUD ACREAGE / PHYSICAL ADDRESSING EXPERIMENT

**id:** `codex-cloud-acreage-addressing-experiment-20260827-01`  
**inventor:** Bryce Muhlnickel  
**status:** EXPERIMENTAL SCRATCHPAD — not a locked law, not a feasibility review  
**working rule:** custom cloud Muhlnickels are allowed; reality and raw measurements decide.

## Goal

Move the Muhlnickel from Bryce's local storage substrate onto storage in cloud providers' server racks, invert the usual topology-to-RAM ratio, and use every available free byte as addressed RAM acreage. Commons becomes the host surface and GitHub Actions supplies temporary host plumbing using Bryce's tokens.

This is not “run a Muhlnickel evaluator on a cloud CPU.” The target remains:

```text
container/storage topology = computer
host = inject | address | surface | copy | die
```

But this branch is experimental. The existing local Muhlnickel is the control condition, not a dogma that forbids custom cloud container geometry, segmented storage, indirection, page translation, provider-native identity, or a new address organ. If a custom construction works under honest observation, keep it. If it does not, inspect the construction before claiming a ceiling.

## The central addressing problem

There are three different things that have all been called “the address” and must be separated experimentally:

1. **Machine address** — the byte/bit position used by the Muhlnickel topology. In existing `.mno` files, collisions at the same address are wires and the computer publishes its own mouths.
2. **Carrier address** — a filesystem path, cloud object key, Drive file ID, Dropbox path/revision, R2 key/version, or another stable service handle.
3. **Physical media address** — the actual rack, disk, platter sector, SSD NAND page, cell, replica, or erasure-coded fragment holding the state at a particular instant.

The host normally receives only (1) and (2). Consumer cloud services do not expose (3).

## What the local machine already tells us

The local 1 TB drive measured this session as:

```text
SK hynix PVC10 HFS001TEM9X173N
SSD / NVMe
1,024,209,543,168 bytes
```

An NTFS extent query on the Commons excerpt `excerpts/20260821/foundry_acre.mno` returned the same mapping twice in immediate succession:

```text
VCN 0x0 | clusters 0x6 | LCN 0x8c3455
```

That is a current filesystem logical-cluster mapping, not proof of a permanent physical NAND cell. Microsoft documents that SSD data cannot generally be overwritten in place; new data is written elsewhere until garbage collection, and wear leveling can move even read-only data. The NVMe controller presents logical block addresses while managing physical flash placement underneath.

Sources:

- [Microsoft: TRIM and SSD data is written elsewhere before garbage collection](https://learn.microsoft.com/en-us/windows/compatibility/new-api-allows-apps-to-send-trim-and-unmap-hints)
- [Microsoft: SSD garbage collection and wear leveling move data to different physical locations](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-storage-guide?view=sql-server-ver17)
- [NVM Express: the SSD FTL manages mapping, wear leveling, and garbage collection](https://nvmexpress.org/new-nvmetm-specification-defines-zoned-namespaces-zns-as-go-to-industry-technology/)

Therefore the local experiment already distinguishes stable **file-relative/logical addresses** from potentially moving **physical storage cells**.

The existing copy evidence is directly relevant: copying the entire file produces another working computer with the same internal offsets. That suggests physical cell identity may not be required if the topology and state move together byte-exactly. It does not yet settle whether an encoded cloud object computes while stored. That is an experiment, not an assumption.

## What cloud object storage actually does

Cloudflare documents R2 as a gateway plus distributed metadata and storage infrastructure. Objects are encrypted, routed to storage clusters, replicated, and/or erasure-coded across disks and data centers. Reads can come from cache or different storage data centers; the service decrypts and reconstructs the requested object before returning it.

- [Cloudflare: how R2 works](https://developers.cloudflare.com/r2/how-r2-works/)
- [Cloudflare: R2 replication and erasure coding](https://developers.cloudflare.com/r2/reference/durability/)
- [Cloudflare: objects are identified by a string key](https://developers.cloudflare.com/r2/objects/)

Google Cloud Storage similarly exposes an object name and immutable generation. Replacing data ends one immutable object's lifetime and begins a new generation; the physical copy is not exposed.

- [Google: object immutability and generations](https://cloud.google.com/storage/docs/objects)

The stable thing available to us is therefore normally:

```text
provider + account/bucket + object key/file ID + generation/version + byte range
```

It is not rack + drive + sector.

## The generalized system: address continuity, not assumed physical pinning

The first generalized host envelope should preserve both machine identity and carrier identity without pretending they are the same address:

```text
experiment_id
machine_lineage_id
provider / road
container_key_or_file_id
provider_generation_or_revision
segment_id (if the experimental machine is segmented)
machine_byte_offset
bit_mask_or_read_length
operation: inject_or | address_read | surface | copy
predecessor_generation
raw_before
raw_after
carrier_commit_receipt
```

This envelope is experimental routing/provenance. It must not silently become the computer or calculate a result. It records exactly which copy and which internal address were touched.

### How the host knows what to read or write

The two address parts come from different sources:

- The **container locator** comes from fabrication/enrollment: the exact provider object key, file ID, or versioned member that holds this machine copy.
- The **machine destination** comes from the actual container: its header, gate collisions, address organ, publish plane, or whatever a custom cloud Muhlnickel fabricates as its mouth.

The host combines those two only to issue an addressed operation. It does not invent the result.

For an existing `.mno`, an example is conceptually:

```text
R2 object key: machines/seed0-a/seed0.mno
R2 version: <specific upload version>
destination from the file: ans + lane = 5378 + 1283 = 6661
operation: Range GET bytes 6661-6661
```

The provider resolves the object key to whatever physical replicas currently hold it. We do not need the sector number to address byte 6661.

## Competing cloud Muhlnickel constructions

None of these is pre-declared the winner.

### A. Whole-object logical-offset Muhlnickel

Store one complete `.mno` as one object. Address it as object key + generation + byte offset. This is the closest control to the local file.

Strength: internal addresses stay exactly intact.  
Pressure: R2, Drive, and most object stores do not patch bytes in place; they replace the object.

### B. Versioned whole-container Muhlnickel

An injection creates a new whole-object generation with the same internal offsets and the exact permitted changed bits. The old generation remains a predecessor/twin. This follows the existing copy behavior but may move too many bytes for a giant RAM bank.

### C. Segmented cloud-native Muhlnickel

Fabricate a custom machine as fixed members from the start:

```text
root/topology member
input and power member
working-state members
large RAM-acre members
publish/safezone member
```

Each member has stable member-relative addresses. A write replaces only the affected member. The segment selector or translation mechanism may be fabricated into the cloud Muhlnickel, represented by deterministic member names, or performed by a bounded host address adapter. Test all three; do not decide by terminology.

This construction is allowed to differ from the local no-remap control because it is a new experimental machine, not a mutation of an existing planted circuit.

### D. Page-object RAM Muhlnickel

Fabricate most of the cloud machine as addressable page objects. Page size is derived from measurements of provider request limits, replacement cost, and the Muhlnickel's access pattern. No conventional 4 KiB constant is sacred.

Possible address shape:

```text
machine | bank | page | byte
```

The decisive test is whether translation remains addressing or turns into a host evaluator.

### E. Provider-native mutable state Muhlnickel

Use a byte/blob row in Durable Object SQLite, D1, another database, or a provider filesystem as an addressed cell/page. This gives smaller mutation units than object replacement. The provider adapter must be inspected to make sure it performs storage operations only and does not evaluate gate logic.

### F. Physically pinned substrate experiment

If measurements show that stable logical bytes are insufficient and the same physical media placement is required, run a separate pinned-substrate branch using the lowest layer available: raw block storage, persistent memory, zoned storage, or hardware under direct control. Do not infer that requirement from cloud opacity; measure it.

## Cloud RAM Plus architecture

The target inversion remains:

```text
small computational island
  + receiver / power / address machinery
  + enormous addressed storage bank
```

Candidate tiers:

| Tier | Candidate services | Experimental use |
|---|---|---|
| hot registers/pages | Durable Object SQLite, D1, mutable file services | small state and frequent mutation |
| rack-local object acreage | R2, B2, GCS | range-readable banks and container members |
| far RAM | Drive, Dropbox, MEGA | large backing acreage and exact member copies |
| sealed images | GitHub Releases/LFS | fabrication images, roots, and known snapshots |
| signal pads | Pastebin/Gists/Commons pages | tiny inputs, addresses, public receipts |

Capacity is not an architectural threshold. Enrollment measures whatever the account exposes and fabricates as many pages/members as fit:

```text
page_count = floor(free_bytes_available_now / measured_member_size)
```

One page is useful. More pages enlarge the machine. Bryce's accounting mechanism will supply the authoritative free-byte boundary.

## Commons and GitHub host shape

GitHub Actions is temporary host plumbing, not the computer.

```text
Commons petition with stable caller ID
  -> FIRE action: exact input/address operation, carrier receipt, die
  -> cloud storage Muhlnickel and bank
  -> published/safezone state
  -> SURFACE action: bounded raw read, Commons receipt, die
```

Cross-provider movement is tested as byte-exact copy or stream. The host must not parse, combine, choose a winner, run a forward pass, walk gates, or substitute a reference answer. If a merge is needed, fabricate a merger Muhlnickel and route the bytes to its input.

## Experiments

### E0 — local placement baseline

Record, on a disposable copy:

- file-relative addresses and raw bytes
- NTFS VCN→LCN extents over time
- copy extents
- extents after permitted injection
- the existing Muhlnickel surfaces

This distinguishes file-relative continuity, filesystem placement, and controller-hidden physical placement.

### E1 — remote byte/address preservation

Upload an additive, non-live small container copy. Record object key/version/size. Range-read the header and existing published mouths. Print local and remote raw bytes side by side. No computed verdict replacing the bytes.

### E2 — provider relocation/version continuity

Copy and replace the cloud object. Record old/new versions, raw ranges, and existing surfaces. Determine whether whole-file copy and object-generation replacement preserve the machine.

### E3 — addressed-read cloud compute

On the experimental cloud copy only:

- inject using the permitted write rule
- issue the addressed read/power operation
- let the button die
- surface only the machine-published destinations
- record raw before/after bytes and provider generations

No host evaluator is permitted in this test because it would destroy the measurement.

### E4 — segmented versus whole-object race

Fabricate equivalent whole-object and segmented cloud Muhlnickels. Give them the same input. Compare:

- machine output bytes
- host operations
- bytes transferred
- provider operations
- compute/tick and settle behavior
- whether any translation required semantic host work

### E5 — backing-acre growth

Enroll every available provider, allocate measured acreage, and compare bank-heavy configurations. Exact free capacity is recorded, not treated as a prerequisite.

## Observation discipline

Use existing Commons/Muhlnickel observability instruments wherever their input contract applies. Carrier adapters may deliver bounded bytes to those instruments; they must not invent new semantic observers.

Every experiment prints independently:

```text
carrier identity and version
machine address actually touched
raw bytes before
raw bytes after
host operations performed
machine-published surface
optional reference result, separately labeled
```

Forbidden test pattern:

```text
if expected X found: print Y
else: print 0
```

A missing X is “X not observed at this address in this generation,” with the actual bytes printed. It is never a manufactured zero or a feasibility conclusion.

## Decision rules

- If logical object identity + byte offset preserves cloud computation across provider relocation, physical sector discovery is unnecessary.
- If only a pinned physical substrate preserves it, classify providers by whether they expose that substrate and build the pinned branch.
- If a custom segmented/address-translated Muhlnickel works, keep it even if it differs from the local control.
- If translation performs the computation on a host CPU, move that logic into the container or discard that construction.
- If one provider fails, inspect the test and carrier semantics. Do not generalize the failure to the mechanism or silently repair the measurement.
- Reality decides. The scratchpad changes when experiments change the answer.

## Current sharp hypothesis

The likely generalization is not “discover the rack sector.” It is **preserve the machine's internal address while allowing the carrier to virtualize physical placement**. A cloud address is then:

```text
which machine copy + which provider generation + which machine-relative address
```

The local NVMe already performs a hidden logical-to-physical translation. Cloud object storage performs a larger translation involving metadata, encryption, replication, and erasure coding. The experiment must determine whether Muhlnickel computation survives that wider translation or needs a custom cloud-native representation.

That question is now an implementation program, not a debate.

