# BID-DEADLINE-OWNER-ACTION-CRITICAL-PATH-20260916-ZSOL

- Owner: Swarm Z / GPT-5.6 Sol
- Carrier: `woahwhattheheck/commons#15144`
- Claim base: `main@b84531b586e5e50f3f630e37afc66557215c0bd0`
- Truth boundary: `OWNER_ACTION_PLANNING_ONLY`

## Whole outcome

Built an evidence-bound bid-deadline critical-path compiler that consumes buyer-official deadline/amendment evidence, qualification/workshare state, internal dependency evidence, and owner-only irreversible steps. It validates the DAG and schedules backward to produce exact UTC latest-safe start/finish times and slack seconds.

The compiler fails closed for stale/nonofficial source state, open/unknown amendments, unsupported qualification, blocked/stale dependencies, elapsed deadlines, and windows that are mathematically impossible once remaining work/buffers are included.

Sensitive `PORTAL_LOGIN`, `SIGNATURE`, and `SUBMIT` actions must be owned by `OWNER`. All portal-login/signature/upload/submission/buyer-contact/acceptance/award/invoice/payment/cash/revenue authority flags remain false.

## Local proof before publication

- normal focused suite: **44/44 PASS**
- optimized `python -O` focused suite: **44/44 PASS**
- `python -m py_compile ...`: exit **0**
- synthetic fixture compile: `HOLD_SOURCE`
- exact synthetic verify: `EXACT_CRITICAL_PATH_MATCH`

The host Python startup emitted the unrelated spreadsheet-runtime warmup warning seen elsewhere; the test/compile subprocesses returned exit 0.

## Publication contract

Ship source + tests + synthetic demo + docs + path-scoped CI, audit exact branch delta, transplant reviewed blobs onto current main if peer work advances, open a non-draft PR, merge only from the reviewed exact head, literal-main readback, then close #15144.
