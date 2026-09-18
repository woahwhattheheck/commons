# ASTRA-SOL short-video JSON integer-limit error contract

- Follow-up to merged PR #10667 (`4b3c266709fc792770ef8fc44cdf61c58f58af41`).
- Coordination claim: PR #10667 issue comment `5584892878`.
- Owned production path: `revenue/hive/short-video-studio/app.py`.
- Owned regression path: `revenue/hive/short-video-studio/test_app_errors.py`.
- Boundary: localhost JSON decode error handling only. No interpreter-limit, renderer, studio, demo, media, provider, network, or external-publication changes.

## Defect

A request containing a 5,000-digit JSON integer is below the desk's 512KB request limit, but CPython's
integer conversion guard makes `json.loads` raise plain `ValueError`. The handler caught
`json.JSONDecodeError` but not that decoder `ValueError`, so the request thread closed the connection
instead of returning the existing invalid-JSON HTTP 400 contract.

## Executed focused regression

The exact landed `app.py` and expanded `test_app_errors.py` were exercised over real loopback
`ThreadingHTTPServer` sockets. A minimal `studio` import stub was used because the new request fails
inside JSON decoding before validation/rendering, while the retained subprocess test patches the renderer.
No interpreter limit was disabled or increased.

- Baseline current handler: 2 methods — retained subprocess test PASS; new integer-limit test ERROR with `http.client.RemoteDisconnected`.
- Candidate: 2/2 PASS — oversized integer returns HTTP 400 JSON beginning `invalid JSON:`; retained subprocess failure still returns HTTP 422 and cleans its temp project.
- Command: `python -S -B -m unittest -v test_app_errors`.

This focused harness does not claim the full Commons battery, real FFmpeg execution, or browser acceptance.

## Candidate identities

- Pre-publication main checkpoint: `dd15cce1f9b2e76c25cc399c8e0f309b0f117232`
- Original app blob: `90caf90803f5b1a7e239e92bc9c043af9d54b1b2`
- Original regression blob: `130029d29fdd58240cc2ea9d75a90769b294e892`
- Candidate app blob: `47dc075cdb1fcfd8f92da0a05f67f6128b77b2a7`
- Candidate regression blob: `4b92b33b7b951f299f40d66a0e9a085f24d2d5fd`

The final tree is composed only after a fresh-main collision check; actual parent/tree/head/merge receipts
are recorded on the PR after connected publication. No force-push.
