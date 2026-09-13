# Inbound reply router hardening boundary

`router.py` is the public compatibility boundary. The original reviewed semantic engine is retained byte-for-byte as `router_base.py`; the wrapper re-exports the same schemas, exceptions and routing API while adding two fail-closed custody fences.

## Ownership freshness

`Policy.max_owner_binding_age_seconds` defaults to 900 seconds and is independently evaluated at the explicit `evaluated_at` time. If any owner-binding row is older than that window, the result is forced to `HOLD` with `owner_binding_stale`. The exact boundary is accepted. Existing active-owner count, scope and owner-ID mismatch fences remain authoritative in the preserved semantic engine. A binding beyond the configured future skew adds `owner_binding_from_future`.

The CLI exposes the same policy as `--max-owner-binding-age-seconds`. This is a custody freshness window, not permission to send a reply.

## File custody

Before either JSON source is consumed, the CLI requires context and evidence to be distinct ordinary non-symlink files and requires any output to be distinct from both by lexical path and existing inode identity. Existing symlink/non-directory ancestor components are rejected. `load_json()` repeats ordinary-file checks and uses `O_NOFOLLOW` when the platform provides it. Receipt publication rechecks the target parent/leaf before staging and immediately before replacement.

These checks close static and long preflight-to-publication alias/redirection seams. They do not claim immunity to a privileged hostile filesystem race inside the final check-to-open or check-to-replace syscall interval.

Every receipt still retains `side_effects_authorized=false`, `reply_send_authorized=false`, `resend_authorized=false`, `payment_authorized=false`, `contract_authorized=false`, `revenue_recognized=false`, and `buyer_acceptance_inferred=false`.
