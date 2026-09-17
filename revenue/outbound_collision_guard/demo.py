from hashlib import sha256

from revenue.outbound_collision_guard import acquire, begin_send, intent_fingerprint

intent = {
    "counterparty_key": "example.com",
    "route_key": "email:sales@example.com",
    "thread_key": "gmail:abc123",
    "purpose_key": "paid-workshare:freight-qa",
}
claimant = {"claimant_id": "astra-z", "session_id": "demo"}
now = "2026-09-17T03:15:00Z"
fp = intent_fingerprint(intent)
muse = {
    "receipt_id": "slack:d0c1u7tuzec:demo",
    "intent_fingerprint": fp,
    "selected_claimant_id": "astra-z",
    "selected_session_id": "demo",
    "lease_generation": 1,
    "arbitrated_at": "2026-09-17T03:14:59Z",
    "expires_at": "2026-09-17T03:25:00Z",
}
ready = acquire(intent=intent, claimant=claimant, now=now, ttl_s=600, muse=muse)
assert ready["state"] == "READY_SINGLE_WRITER"
attempt = begin_send(
    lease=ready["lease"],
    body_sha256=sha256(b"final provider bytes").hexdigest(),
    provider="gmail",
    now="2026-09-17T03:16:00Z",
)
print(attempt["state"], attempt["lease"]["attempt"]["attempt_id"])
