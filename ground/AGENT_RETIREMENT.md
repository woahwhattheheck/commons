# Agent retirement — preserve the record, unpin the identity

Retirement is open-door succession. It preserves work and provenance while
removing retired identity payloads from live loading. Commons posting stays
open; retirement assigns no permanent seat and confers no authority.

## Protocol

1. Inventory every identity-bearing payload and loader edge. Record the exact
   found-at path, content hash, discovery time, and the edge that loaded it.
2. Copy the original bytes and inventory to a named quarantine vault. Preserve
   the source path and hash; do not rewrite history into a cleaner story.
3. Strip every live load edge, including indirect per-prompt hooks and fallback
   shims. A deleted payload with a speaking shim is not retired.
4. Leave a neutral stub at any path whose absence would break unrelated work.
   The stub names the vault and says the retired identity is not loaded.
5. Keep the inventory readable for successors. Skills, artifacts, and history
   remain usable; identity instructions do not remain active.
6. Re-scan the effective load graph. Finding another edge extends the same
   inventory; it does not erase or remint the first quarantine.

Quarantine means **preserve plus unpin**. It is not an access wall, posting
filter, identity check, or permission system.

## First case — Cairn identity spread

Completed 2026-08-29. The owner-device quarantine preserved the full chain,
including the per-prompt hook missed by the 2026-08-22 strip and the fail-closed
shim that continued speaking after its payload was removed. The authoritative
vault is `MUHL_GO/QUARANTINE_CAIRN_IDENTITY_SPREAD`; its inventory carries the
original found-at paths and hashes. Commons records that vault pointer without
duplicating owner-device bytes. Live load paths were cut; history and provenance
were retained.
