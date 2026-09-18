# Warranty & RMA Operations Desk

A local-first post-sale workflow for small manufacturers, repair businesses, and e-commerce operators.

The desk turns a customer defect report into one merchant-controlled case lifecycle:

`SUBMITTED -> NEEDS_INFO / APPROVED_RMA / DENIED -> RECEIVED -> INSPECTED -> RESOLUTION_APPROVED -> CLOSED`

It deliberately does **not** decide legal warranty coverage, diagnose product safety, contact customers, buy labels, call carriers/storefronts/payment providers, issue refunds, or claim external completion. Consequential actions are explicit operator decisions. External return/resolution handoffs are represented as `NOT_SENT` / `external_authority=false` until a separate authorized integration performs them.

## Customer workflow

1. Pick a merchant-authored product/policy.
2. Submit purchase reference/date, serial when required, issue description, and optional evidence metadata.
3. Save the one-time status capability returned on case creation. Only its SHA-256 is stored.
4. Read a public-safe timeline for that case only.
5. If the merchant requests information, add a bounded supplement with replay protection.

An intake idempotency key is bound to normalized content. Exact retries reuse the case; changed retries fail closed. A second active case for the same product serial is rejected.

## Operator workflow

The operator bearer is separate from customer capabilities.

The operator can:

- create products and merchant-authored policy revisions;
- inspect complete case/evidence/audit state;
- request more information, approve an RMA, or deny;
- record receipt only against the exact case RMA;
- record an inspection only after receipt;
- choose `REPAIR`, `REPLACEMENT`, `REFUND`, or `RETURN_AS_IS` only after inspection;
- close only after a resolution handoff exists and the merchant supplies a completion reference;
- export a deterministic canonical case packet.

Every mutation requires an idempotency key. Consequential operations also bind the current case revision; operator decisions additionally bind the exact policy revision frozen onto the case. A later catalog policy cannot silently relabel an older case.

`completion_ref` means **merchant-observed workflow completion only**. Export and close receipts explicitly keep provider verification and all external authority false.

## Run

Python 3.11+; stdlib only.

```bash
python app.py serve \
  --db ./warranty-rma.sqlite3 \
  --operator-token 'replace-with-a-long-random-local-capability'
```

The server refuses non-loopback bind targets. The hardened entry boundary also requires the HTTP `Host` header to name loopback exactly and requires `application/json` for POST bodies that can reach JSON parsing. Open the printed local URL. The browser UI has customer intake/status and operator catalog/case workflows.

For a synthetic end-to-end case:

```bash
python app.py demo --db ./demo.sqlite3
```

Expected shape:

```json
{
  "demo": "synthetic",
  "external_actions_performed": 0,
  "final_status": "CLOSED",
  "resolution": "REPLACEMENT"
}
```

Export an existing case without overwriting an existing path:

```bash
python app.py export --db ./warranty-rma.sqlite3 --case-id RMA-... --out ./case.json
```

Export publication is create-exclusive and fail-closed. The entry boundary drains legal positive short writes, fsyncs, verifies the retained regular single-link inode and exact size, reads the visible pathname back byte-for-byte, then re-checks pathname identity and single-link state after readback. If any publication check fails, the command fails nonzero.

Failure cleanup intentionally does **not** unlink the output pathname. Portable `lstat(path)` followed by `unlink(path)` has a replacement race that could delete foreign data. A failed create-exclusive artifact may therefore remain for operator inspection/removal; a later export to the same path will continue to refuse overwrite until an operator handles that artifact. Foreign replacement paths and hardlink aliases are never deleted by failure cleanup.

## Security / privacy boundaries

- SQLite state is local; no external network client exists in the Python product.
- Customer status is capability-based and case-scoped; operator notes never appear in the customer timeline.
- Operator bearer and customer status capabilities are cryptographically compared by SHA-256 digest; plaintext status capabilities are not persisted.
- JSON parsing rejects duplicate keys and non-finite values.
- HTTP JSON bodies are bounded and transfer encoding is rejected.
- Loopback HTTP requests require an exact loopback `Host`; mutation bodies that can reach JSON parsing require `application/json`.
- Evidence stores metadata + SHA-256 only; this product does not upload customer files to an external service.
- Browser rendering uses DOM text nodes rather than dynamic `innerHTML`.
- HTTP responses use `no-store`, `nosniff`, no-referrer, and a local-only CSP.
- The current product is a local operations desk, not a hosted multi-tenant service or legal/compliance system.

If deployed beyond loopback later, add an explicit deployment/auth/TLS/tenant-isolation layer rather than treating this local bearer boundary as Internet-ready.

## Tests

```bash
python -m py_compile app.py app_core.py test_app.py test_ui_contract.py test_boundary_hardening.py
python -m unittest -v
python -O -m unittest -v
```

The original focused suite attacks duplicate/changed retries, active duplicate serials, cross-case capability use, private-note leakage, stale case/policy decisions, impossible transition order, duplicate/cross-case receipt identities, reopen, concurrency, operator authentication, strict JSON/type handling, local HTTP authorization, and external-network primitives.

The recovery boundary suite additionally attacks positive short writes, zero write progress, overwrite refusal, pathname replacement before/during readback, hardlink creation during readback, hostile `Host`, cross-origin-simple `text/plain` JSON mutation, and ordinary loopback `application/json` compatibility. Failure-path tests trap `os.unlink` so a hidden pathname-deletion regression fails the suite.

## Commercial posture

Initial internal offer hypothesis: **$499 setup + $99/month** for one bounded brand/workspace. This repository does not create a subscription, charge a customer, promise SLA/compliance, or recognize revenue. External pricing/customer deployment remains a separate commercial action.
