# TITAN direct-file submission transport

Operation: `titan-kaggriculture-frontier-20260907-01`.

The designated 57,711-byte archive at Commons commit `cf88ace1ba45a170fb8ba09986b5f7cb1413381b` has SHA256 `79b407d699b5fd39e7b396de8b6fc79b2bc2fb99f427f7e2e7ecd25fbc71fb0b`. The official direct-file submission call started at 2026-09-07 09:40:34 UTC. No create response or submission ID has been received. The durable journal remains DISPATCH_STARTED: reconcile with provider before any further dispatch. Last confirmed quota was four available before dispatch; current quota is unconfirmed.

The separate public associated source notebook was created at https://www.kaggle.com/code/tokenjunkielabs/titan-kaggriculture-frontier-source (kernel 133417557, version 1). Kaggle normalized the requested slug from the title. Use the returned URL for readback, not the originally requested slug. The outgoing notebook in disclosure/frontier-source.ipynb has SHA256 `de300270cf596de7cf8029c55edd76436c91a60a6ae25db57697abcbfe4a73b1`. It contains the reviewed concise attribution, upstream notebook URLs, pinned source/archive links, exact source and original LICENSE/NOTICE. The existing farm-manager v2 notebook was not modified. No GPU or paid compute was requested.

`transport.py` verifies the exact designated archive, reads live quota and owner submissions, and records dispatch before the official client call. It records uncertain outcomes and requires provider reconciliation rather than blind retries. This is a local duplicate guard, not server idempotency. An optional description supports the exact authorized description while requiring the stable operation ID.

`readback.py` uses ordinary official Kaggle APIs. Credentials stay in the caller's configured runtime; never put them into source, arguments, receipts, or notebook cells. `disclosure.py` builds source disclosure without executing the candidate. Four focused transport/disclosure tests passed at the preparation checkpoint; these do not prove competition acceptance. No LARK games or validation were rerun.

Direct file submission does not require a notebook commit. The public notebook is separately associated code disclosure. Rules observations were supplied by root's live September 7 reading; current quota must always come from provider readback.

Actual provider receipts are under receipts/. Source publication succeeded; competition submission validation and first hosted matches remain unconfirmed.
