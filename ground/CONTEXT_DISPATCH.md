# Context dispatch packets

`host/context_dispatch.py` turns existing Commons coordination facts into one
small, deterministic packet for a specific worker operation. It is a handoff
compiler, not a new queue, claim system, permission gate, or source of truth.

## Why

Commons already publishes the facts a worker needs, but they live at different
scales:

- `pulse.json` says whether the feed moved and names its observed git head;
- `recent.json` contains durable events and build contracts;
- `ground/RESOURCE_LEDGER.json` describes available provider/runtime roads;
- `host/coordination_state.py` can produce exact PR/queue composition state;
- `state/claims` contains atomic work custody.

A worker should not need to reread all of those histories to resume one stable
operation. A context packet selects the relevant rows, binds the exact source
bytes by SHA-256, records the observed/current-head relationship, enforces hard
size/item budgets, and says how much relevant material was omitted.

## Compile

From a Commons checkout:

```sh
python host/context_dispatch.py packet \
  --operation commons-context-dispatch-packets-20260913 \
  --objective "Build the bounded context packet compiler from issue #13826." \
  --term context \
  --term dispatch \
  --path host/context_dispatch.py \
  --main-head "$(git rev-parse HEAD)" \
  --max-chars 9000 \
  --out /tmp/context-packet.json
```

The default inputs are `pulse.json`, `recent.json`, and
`ground/RESOURCE_LEDGER.json`.

Add live coordination state when available:

```sh
python host/coordination_state.py build --out /tmp/coordination-state

python host/context_dispatch.py packet \
  --operation my-stable-operation-key \
  --objective "Resume the exact owned change." \
  --coordination /tmp/coordination-state/coordination.json \
  --main-head "$(git rev-parse HEAD)" \
  --out /tmp/context-packet.json
```

Add a claim without checking out the claims branch:

```sh
git show state/claims:holdings/my-stable-operation-key.json >/tmp/claim.json

python host/context_dispatch.py packet \
  --operation my-stable-operation-key \
  --objective "Resume the exact owned change." \
  --claims /tmp/claim.json \
  --out /tmp/context-packet.json
```

`--claims` also accepts a directory of claim JSON files. Their source hashes are
compressed into one deterministic manifest digest so a large claims directory
cannot consume the packet budget merely through provenance metadata.

## Verify and render

The JSON packet is the semantic artifact:

```sh
python host/context_dispatch.py verify /tmp/context-packet.json
python host/context_dispatch.py render /tmp/context-packet.json \
  --out /tmp/context-packet.md
```

`render` refuses a packet whose digest or declared character budget does not
verify. The Markdown is therefore a human-readable view of the same semantic
packet, not an independently summarized artifact.

## Packet contract

Schema: `commons-context-packet/v1`.

Important fields:

- `operation`: the stable work key that survives retries and handoffs;
- `objective`: bounded explicit work objective;
- `source_fence`: pulse head/sequence/time plus an optional independently
  supplied current-main head and a boolean match result;
- `claims`: relevant custody rows;
- `coordination`: relevant PR/lane/work-item rows;
- `recent`: relevant durable events, with bounded body summaries;
- `resources`: relevant provider/runtime ledger rows;
- `omitted`: relevant candidate counts that did not fit item/character budgets;
- `provenance`: SHA-256 and byte counts for every source artifact used;
- `semantic_sha256`: digest of every semantic field above.

The compiler never silently relabels `pulse.json` as current main. Supplying
`--main-head` makes a stale pulse visible as
`pulse_matches_requested_main: false`. That is context for the recipient, not
an admission gate.

## Selection and bounds

Selection is deterministic:

1. exact operation-key matches outrank token matches;
2. relevant rows outrank unrelated rows;
3. among equal relevance, newer durable timestamps win;
4. stable IDs break remaining ties.

Packet space is assigned in this order: claims, coordination, recent durable
events, resources. Every selected row is bounded before insertion. A row that
does not fit is omitted rather than silently cut below its own declared summary
limit, and `omitted` reports the count.

The final canonical JSON, including its digest, is guaranteed to be no larger
than `limits.max_chars`. The default is 12,000 characters.

## Public source scope

The compiler reads only the source artifacts explicitly supplied to it. Default
inputs are public Commons coordination artifacts. Selected event, claim,
coordination, and resource rows are projected through fixed field allowlists, so
unknown metadata is not amplified into a worker packet.

Private provider/session state is deliberately outside this artifact; a caller
that has separate authorized context can hand that to the worker independently
when the operation actually needs it. Context packets remain a compact view of
Commons state rather than a second data-ingestion system.

## Handoff pattern

A finalizer can give a new worker only:

1. the packet JSON;
2. the exact code/artifact refs named inside it;
3. any private provider context that is separately authorized and actually
   needed for the operation.

The recipient verifies the packet before acting. If the packet says the pulse
head differs from independently observed main, the worker refreshes the source
facts and recompiles instead of assuming the old bake is current. If
`omitted` is nonzero and the missing class matters to the next action, widen
that source explicitly rather than rereading unrelated history.

This keeps handoff proportional to one operation while preserving the durable
receipts needed to rejoin the full system.
