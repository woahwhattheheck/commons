# HIVE006 trusted webhook authentication — successor custody receipt

Operation: `HIVE006-TRUSTED-WEBHOOK-AUTH-20260909-01`  
Successor repair: `HIVE006-PR12115-EXACT-HEAD-CUSTODY-TRUTH-CLOSURE-20260910-01`  
Original recovery claim: Slack `1789079608.915029` in `#hive-commerce-builds`  
Review consumed: `5173031294` on predecessor head `c8257adbc171b39c75bc44d3795c15b9502daafe`  
Successor publication parent: `acbbd1a7245ef61628211637eb88655fa93a1c4c`

## Scope

This remains the same additive provider-authentication edge. The executable webhook and its focused test are reused byte-for-byte from the reviewed predecessor. The successor changes only workflow custody plus documentation/receipt truth.

Exact six additive paths and SHA-256 content identities:

- `revenue/hive/voice-support-desk/twilio_webhook.py` — `7a1b06b0a6818f0281c9cae3a229a547cd1160f6e7fe9362bbc304e144518847`
- `revenue/hive/voice-support-desk/test_twilio_webhook.py` — `13a6c52660d234253a334631ca28b842d85d87b9befff021c6c92e3dda6fdca2`
- `revenue/hive/voice-support-desk/TRUSTED-WEBHOOK.md` — `6447446c231f3b4f5ae36e1ccb1611e2bf7b25f3ba205a824c33ac0e3caf9417`
- `revenue/hive/voice-support-desk/requirements-webhook.txt` — `ed12e5430207fced55142afe9b3f46a346eb5697ae5fed3e0857252446b01e0c`
- `.github/workflows/hive006-trusted-webhook-auth.yml` — `7dda3c8dda8b874b921645d72d4ed89332dc969cff398908b23bfff5209cebf8`
- this receipt

## Security contract

- loopback-only Python listener behind HTTPS termination;
- exact operator-configured public HTTPS origin + raw request target are supplied to Twilio's validator; Host/Forwarded headers are not trusted for signature identity;
- all received form fields are passed to `twilio.request_validator.RequestValidator`; ambiguous duplicate field names fail closed;
- missing/invalid signature or validator exception returns 403 before **per-request MerchantGate dispatch and request-driven Store access**;
- process startup still constructs the configured `MerchantGate`/`Store` and may create or migrate its local SQLite schema before any request arrives; this successor does not claim zero pre-auth startup DB access;
- runtime `TWILIO_AUTH_TOKEN` only, never CLI/database/bundle/log material;
- pinned `twilio==9.11.0`; no local HMAC clone;
- signed provider requests still require the merchant order-reference + support-code gate;
- no invented timestamp/replay field: exact provider retries remain subject to the landed call-turn and dial-result replay/conflict semantics.

## Exact-head hosted contract

The successor workflow:

1. checks out `${{ github.event.pull_request.head.sha || github.sha }}` explicitly;
2. sets `persist-credentials:false` and `fetch-depth:2`;
3. asserts checked-out `HEAD` equals that event head;
4. asserts `HEAD^` is exactly successor publication parent `acbbd1a7245ef61628211637eb88655fa93a1c4c`;
5. asserts the base→head delta is additive-only and exactly the six paths listed above;
6. installs the pinned Twilio SDK, compiles the edge plus landed desk/merchant modules, runs original + authenticated-edge suites, and finishes with a clean-tree assertion.

Hosted success must be recorded separately. This receipt does not pre-claim a runner result.

## Boundary

No live call, token access, provider/account mutation, customer/order mutation, payment, spend, deployment, or owner-PC action was performed. The nonblocking IPv6-loopback usability note from review `5173031294` is intentionally not folded into this custody/truth repair.
