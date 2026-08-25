# OWNER MACHINE BUILD SWEEP — what exists and what is used

Non-Claude read-only sweep, 2026-08-25. This is a build/consumer report,
not a people count. Private roots, credentials, cookies, raw weights,
and transient journals stay off Commons.

| Build | Measured state | Utilization / gap | Next ownerable action |
|---|---|---|---|
| DEMON flight recorder | **LANDED** at `f84b46b5` ancestor of main | Node test passed; read-only UI with exact-SHA landing rule | Keep; add a current pixel heartbeat emitter. |
| Rook resident/evolution runtime | **LOCAL_WORKING** | 9 verified ticks; continuity/resume true; 588 candidates over 12 generations; best `0.763542` | Land source/spec/tests plus redacted receipts, not transient state. |
| MORROW rollback controller | **LOCAL_WORKING_HISTORICAL_RECEIPT** | Durable state/rollback; historical self-test says 12 passes | Rerun non-Claude and land code/manifest/tests; journals stay local. |
| PFC bake boundary scanner | **CLAUDE_INTERMEDIATE_UNTRUSTED** | Completed local artifacts claim 859 regions across seven models versus old heuristic 17 | Preserve; independently sample known offsets, grouping, and bare-zero behavior before landing. |
| MUHL KEYB container | **LOCAL_STALE_MANIFEST** | 430,860-byte `KEYB01v1`; current SHA begins `cca2b762`, manifest claims old `a63396b5` | Structurally inspect and regenerate measured manifest before wiring/publishing. |
| LocalDeviceAgent Android lane | **SOURCE_PRESENT_CI_INERT** | Substantive substrate exists; Android workflow is outside `.github/workflows`; no local APK found in the searched space | Wire deterministic CI at the live workflow path and attach build receipt. |
| Gemma E4B LiteRT lane | **LOCAL_MODEL_PRESENT_CANARY_INCOMPLETE** | 3.659 GB model local; supporting docs landed; weights correctly private | Finish reversible tokenizer/prompt/receiver canary; do not publish weights. |
| White Box | **DISTRO_LANDED_RESEARCH_LOCAL** | 56-path distro on Commons; large research archive local; no server observed active | Publish compact metrics/manifests/hashes, not model archives. |
| MUHLNICKEL app/live viewers | **LOCAL_MULTIPLE_STALE_SURFACES** | Static viewers and shortcuts exist; stale canonical references; no exact Commons directory | Select one canonical live surface and publish a target manifest; exclude browser/queue data. |

## P0 quarantine

Titan is not a test fixture. The owner machine contains three
consecutive byte-identical 9,319,291-byte spans. Current main includes
an under-test owner-path guard and replay/idempotency logic, but every
future test must still use an explicit synthetic Titan. Do not truncate,
deduplicate, overwrite, or otherwise repair the live artifact without an
owner-approved reversible plan and exact hashes.

## Stale / out-of-spec notes

- Old checkouts are not authoritative; compare against current public
  main before any conclusion.
- Session-specific grounding is not a universal no-actuation law;
  current substrate work remains measured and reversible.
- The local `hatch-pet` skill still recommends a retired model; update it
  from `gpt-5.4-mini` to `gpt-5.6-luna` in its own skill lane.
- Titan cutover/browser-profile directories contain sensitive material;
  never publish them wholesale.

Machine pressure was real: 4 cores / 8 threads, about 7.2 GB RAM, and CPU
reached 100% during sweeps. Recover existing remote sessions and free
compute before another full local scan.
