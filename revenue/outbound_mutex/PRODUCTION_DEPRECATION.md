# Production deprecation — `outbound_mutex`

`revenue/outbound_mutex` is **not** a production external-send mutex.

It remains a reference/local CAS implementation and historical artifact from
#14266. Its `lead_key()` accepts a free-form opportunity string. Because two
workers can describe the same commercial opportunity with different labels, the
same buyer/provider situation can mint multiple distinct legacy keys.

For production Gmail, external Slack/DM, sponsor, maintainer, sales or other
externally visible outbound mutations, use only:

- `revenue/outbound_connector_lease/key.py` to compile the closed-schema seam;
- the exact `outbound-connector-lease/v1/<sha256>` GitHub branch create as the
  atomic mutex prerequisite;
- `revenue/outbound_connector_lease/authority.py` when an offline identity
  admission check is useful.

A legacy lease never grants `external_send_authorized`, including when it is
`active` and held by the current worker. A legacy `sent` record is conservative
historical evidence and may create a HOLD; it never authorizes another send.

Do not delete historical legacy records and do not invent a new spelling of an
opportunity to evade an existing connector seam. Provider history must still be
re-read immediately before the one allowed external mutation, and ambiguous
provider outcomes must be reconciled rather than retried.

See `../outbound_connector_lease/AUTHORITY.md` for the production contract.
