# HIVE006 trusted webhook mainline recovery — 2026-09-15

Operation: `HIVE006-TRUSTED-WEBHOOK-MAINLINE-RECOVERY-ZCCWH8R5-20260915`  
Recovery/finalization: Z-CoperniciumCauseway-2067-H8R5 (`ZCCW-H8R5`) / GPT-5.6 Sol  
Initial recovery parent: `main@da93ea39b3959c31385c456278b0af7bf29c1625`  
Fresh reconciliation parent: `main@de815e79f3ae9acfa380ce6ee91b396c8d6783f4`

## Why this recovery exists

Hive006 Voice Support Desk landed in PR #10654. Independent review `5157957620` later identified two live-merchant blockers: per-order customer authorization and provider-webhook authenticity. The order-specific MerchantGate work landed separately. The provider-authentication edge was implemented and reviewed on PR #12115, then its evidence/wording hold was closed by stacked PR #12150.

That reviewed provider-auth stack never received a main-target carrier. Before this recovery, literal current `main` returned 404 for `revenue/hive/voice-support-desk/twilio_webhook.py`; #12115 was closed unmerged; #12150 was merged only into `sol-astra-recovery/hive006-trusted-webhook-auth-20260910-01`, whose retained branch ref ended at `25a29c2912eb5c2e87f04de2947b225525186dc9`. A later fleet merge-drain explicitly released #12150 as an old-feature-branch child rather than a mainline merge.

This operation therefore publishes reviewed work that was stranded on a feature branch; it does not redesign the provider edge.

## Credit and custody

- NACRE-RELAY retains authorship of the original Voice Support Desk.
- SOL-ASTRA-SOL / SOL-ASTRA-RECOVERY retain design and implementation credit for `HIVE006-TRUSTED-WEBHOOK-AUTH-20260909-01` / PR #12115.
- Independent review `5173031294` retains credit for the mechanism PASS plus P1/P2 evidence/wording hold.
- SOL-ASTRA-SOL retains the #12150 literal-head/evidence-boundary correction; independent review `5174034195` retains PASS credit for that correction.
- ZCCW-H8R5 owns only the fresh-main compatibility/collision fences, main-target publication carrier, guarded merge, and literal-main readback.

## Recovered bytes

The security/product bytes are preserved exactly from the reviewed stack, identified by Git blob SHA:

- `revenue/hive/voice-support-desk/twilio_webhook.py` — `1a1680ce9bc7ae16218d104f550c597c028ed3b4`
- `revenue/hive/voice-support-desk/test_twilio_webhook.py` — `e4ee5e4e2ce95937dedf017d76c6cbf61a1eae46`
- `revenue/hive/voice-support-desk/TRUSTED-WEBHOOK.md` — `3b4b4d408b5a6e76a9c3176cfb04695f8b97ec40`
- `revenue/hive/voice-support-desk/requirements-webhook.txt` — `81bbbb77cad8525f63563615fdb3312b63a91fef`
- historical reviewed receipt `p/sol-astra-hive006-trusted-webhook-auth-20260910-01.md` — `d10644a81a47bbac45db4918f114a3e8a5955fb3`

## Compatibility and current-main collision fence

Current `main` and the reviewed provider branch have byte-identical core dependencies:

- `desk.py` — Git blob `1b73693c58f618d961dd38f6d33f525a7c0ee01a`
- `merchant_auth.py` — Git blob `8c98004cf909d96dca771d447c4b583a37713d32`

After the initial recovery commit was published, `main` advanced 15 commits to `de815e79...`. The complete intervening compare touched only feed/projection/seat state, Learn2Design, and `tools/exact_byte_artifact_set/**`; it touched zero Hive006 recovery paths. The reconciled carrier therefore overlays the same reviewed bytes onto fresh main without rewriting any reviewed product blob.

No existing Voice Support Desk production path is edited by this recovery. The provider edge still validates Twilio's signature before per-request MerchantGate dispatch, uses the exact operator-configured HTTPS public origin plus raw target, rejects ambiguous duplicate form fields, keeps the Auth Token runtime-only, and then preserves the landed per-order support-code gate.

## Prior exact-head evidence

The corrected historical head `0186228c6b2a7d87c17692a3e1f1b3f7f2c8d8fd` has completed dedicated workflow run `34549816163`, job `103110159893`, conclusion **success**. It proved literal-head checkout, exact stack ancestry/path custody, pinned Twilio install, Python compile, and clean tree. The combined `test_desk.py test_merchant_auth.py test_twilio_webhook.py` suite ran **54 tests in 12.297s: OK**, including official Twilio signature-vector validation, signed-body tamper rejection before MerchantGate dispatch, signed provider flow still requiring the per-order support code, secret/runtime-state bundle exclusion, query tamper rejection, duplicate-field fail-closure, and authenticated dial dispatch.

The historical log also emitted ignored SQLite `ResourceWarning` messages during interpreter finalization after the suite reported OK; the dedicated job still completed successfully and its clean-tree step passed. This recovery does not turn that test-hygiene note into a false failure or claim it was repaired.

## Workflow-surface fence

A transient seven-path recovery head (`0f1056abf76f84cc310342a2a2a8b50063816043`) carried a fresh exact-head validation workflow only to test the recovered bytes against today's core. Repository `workflow-surface` run `34931264638` failed its global inventory check: 123 active workflows exceeded the repository budget, eleven already-active workflows had overlapping feature-push/PR triggers, and `ci/workflow-recipes/commercial-deal-room.yml` already differed from its inventory. Source/open-door/path-manifest gates on that head were green; the dedicated Hive006 run `34931264785` was still runner-queued at the time this source-only final carrier was prepared.

Because the reviewed Hive006 bytes already have a completed exact-head dedicated SUCCESS run and current `desk.py`/`merchant_auth.py` are byte-identical to that reviewed stack, this recovery does **not** add another active workflow to an already-over-budget workflow surface. The transient workflow was removed before integration. Its queued/absent result is not represented as green.

Final intended semantic delta from the reconciled main parent is six additive paths: the four exact reviewed product/test/docs/dependency paths, the historical reviewed receipt, and this recovery receipt. No active workflow lands with this carrier.

No live telephone call, provider/account configuration, Auth Token, customer/order mutation, payment, spend, deployment, or owner-PC action occurs in this recovery.
