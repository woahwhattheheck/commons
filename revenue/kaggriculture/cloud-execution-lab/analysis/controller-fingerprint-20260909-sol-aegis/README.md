# SOL-AEGIS controller-fingerprint publication recovery

This additive evidence lane recovers a controller-fingerprint analysis whose original Slack SHIP claim did not resolve to durable GitHub bytes. It does **not** modify TITAN policy, controller, HIRE, SELL, route, engine, evaluator, canonical runtime, provider, or submission state.

## Evidence boundary

The corpus manifest binds five exact Slack replay gzip transports by filename, byte length, SHA-256, expected seat, and externally supplied role label. The analyzer validates the transport before decompressing it, finds `Bryce Muhlnickel` by the replay's agent metadata, rejects bool/type aliases, uses `action[k] <- observation[k-1]` for reachable hand prefixes, and separately fingerprints:

- farmer actions;
- submitted, reachable, and unreachable hand streams;
- prior-observable hand counts;
- full market actions;
- SELL-only market rows;
- non-SELL market rows; and
- empty market-row counts.

The checked-in `EVIDENCE.json` is self-sealed and binds the exact `CORPUS.json` bytes. Unit tests also enforce single-basename corpus filenames, lowercase hex hashes, declared transport byte sizes, exact episode IDs/seats, comparison referential integrity, and malformed replay/action rejection.

## Recovered result

For the exact replay pair `V2 107140666` vs `V1 107142511`, the Bryce stream has zero differing steps for farmer actions, submitted hands, prior-observable hand counts, reachable hand prefixes, unreachable suffixes, and non-SELL market rows. Full market differs at 51 steps and SELL projection differs at 43.

For `V2 107140666` vs `V1 107150217`, the same controller-facing components have zero differing steps. Full market differs at 49 steps and SELL projection differs at 42.

The three matched streams share 6,451 submitted hand rows, 6,429 reachable rows, and 22 unreachable suffix rows. Normalized unreachable opcodes are exactly `MOVE=14`, `PASS=5`, `WATER=3`.

These observations rule out an **observed static non-SELL controller-stream difference in these two matched replay comparisons**. They do not establish SELL causality, because opponents, seeds, market/state trajectories, and rewards differ between episodes.

## Verification

With the five gzip files available in one directory:

```bash
AEGIS_CORPUS_DIR=/path/to/replays python -m unittest -v test_controller_fingerprint.py
python controller_fingerprint.py \
  --manifest CORPUS.json \
  --corpus-dir /path/to/replays \
  --verify-evidence EVIDENCE.json
```

Without the binary corpus, the checked-in CI still runs all synthetic fail-closed tests plus checked-in manifest/evidence binding tests; the binary-corpus integration class is explicitly skipped rather than silently treated as passing.
