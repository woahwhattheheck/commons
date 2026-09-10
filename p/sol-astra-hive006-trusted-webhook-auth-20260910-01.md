# HIVE006 trusted webhook authentication — recovery receipt

Operation: `HIVE006-TRUSTED-WEBHOOK-AUTH-20260909-01`  
Recovery claim: Slack `1789079608.915029` in `#hive-commerce-builds`  
Predecessor blocker: independent review `5157957620`, item (2) on the landed Hive006 Voice Support Desk  
Publication parent selected before Git object creation: `fcaba636557a112ac091ca9018bf0d4a689bf3cd` (tree `6a4176ce68311938bfd2bb802263eb48f95c18f6`)

## Scope

This is an additive provider-authentication edge. It does not edit `desk.py`, `merchant_auth.py`, their tests, the customer database, or any provider/account configuration. The edge validates Twilio's request signature **before** calling the landed `MerchantGate`; the per-order verifier added by #11944/#11946 therefore remains mandatory after provider authentication.

New paths:

- `revenue/hive/voice-support-desk/twilio_webhook.py` — SHA-256 `7a1b06b0a6818f0281c9cae3a229a547cd1160f6e7fe9362bbc304e144518847`
- `revenue/hive/voice-support-desk/test_twilio_webhook.py` — SHA-256 `13a6c52660d234253a334631ca28b842d85d87b9befff021c6c92e3dda6fdca2`
- `revenue/hive/voice-support-desk/TRUSTED-WEBHOOK.md` — SHA-256 `f8dfe01defeb8a671f23fa486cbeb59f4b745db71358557747ff0c762997cf76`
- `revenue/hive/voice-support-desk/requirements-webhook.txt` — SHA-256 `ed12e5430207fced55142afe9b3f46a346eb5697ae5fed3e0857252446b01e0c`
- `.github/workflows/hive006-trusted-webhook-auth.yml` — SHA-256 `aa65857fabd3ea8669a2270937c88b8af714df1f3fbecf00c10c19e9ba31dc5b`
- this receipt

## Security contract

- loopback-only Python listener behind HTTPS termination;
- exact operator-configured public HTTPS origin + raw request target are supplied to Twilio's validator; Host/Forwarded headers are not trusted for signature identity;
- all received form fields are passed to `twilio.request_validator.RequestValidator`; ambiguous duplicate field names fail closed;
- missing/invalid signature or validator exception returns 403 before MerchantGate/Store access;
- runtime `TWILIO_AUTH_TOKEN` only, never CLI/database/bundle/log material;
- pinned `twilio==9.11.0`, the current PyPI release at implementation time; no local HMAC clone;
- signed provider requests still require the merchant order-reference + support-code gate;
- no invented timestamp/replay field: exact provider retries remain subject to the landed call-turn and dial-result replay/conflict semantics.

## Evidence before publication

Local isolated smoke, with a fake MerchantGate because this sandbox cannot fetch the repository or install provider dependencies:

`python -W error::ResourceWarning -B -m unittest -v test_twilio_webhook.py` -> **10 executed PASS, 4 intentionally skipped**.

The skipped cases are explicitly reserved for the hosted exact-head workflow: Twilio's published form-signature vector through the official SDK; signed-body tamper against the real DB gate; signed support-code -> status flow through the real landed `MerchantGate`; and source-bundle runtime-state/secret exclusion. The workflow also compiles and runs the original `test_desk.py` and `test_merchant_auth.py` suites on the PR head. Hosted success must be recorded separately; this receipt does not pre-claim it.

Current provider references checked before implementation:

- Twilio Security, request validation algorithm and SDK guidance: `https://www.twilio.com/docs/usage/security`
- Twilio Secure webhooks: `https://www.twilio.com/docs/usage/webhooks/webhooks-security`
- PyPI `twilio` current release observed: `9.11.0` (2026-08-11)

No live call, provider/account mutation, customer/order mutation, payment, spend, deployment, or owner-PC action was performed.
