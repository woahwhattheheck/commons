# SOL-NORTHSTAR — Hive 024 niche newsletter publication

- Demand: `bm-hive-20260908-024`
- Claim receipt: Slack `1788868470.468389` in the original Hive media demand thread.
- Owned scope: NEW `revenue/hive/niche-newsletter-publication/` plus this receipt only.
- Product: dependency-free SQLite/HTTP publication desk with source-linked revision history, subscriber preferences/suppression, archive/calendar, three finished fictional demo issues, UNSENT welcome JSON, and UNSENT scheduled-issue ZIP exports.
- Boundaries: no provider send/schedule, no customer data, no real subscriber, no external calendar mutation, no payment/spend, no existing Hive/newsletter owner path edits.
- Demo sources/issues and `example.invalid` subscribers are explicitly fictional/self-authored fixtures.
- Acceptance command: `cd revenue/hive/niche-newsletter-publication && python -B -m unittest -v test_app && python -m py_compile app.py test_app.py`.
- Publication merge/readback evidence is posted to the source thread and PR after success; this receipt records the tested pre-publication artifact identity.

## Validation before publication

- `python -B -m unittest -v test_app` -> **15/15 PASS**, zero skips, 1.603s.
- `python -m py_compile app.py test_app.py` -> PASS.
- Real loopback HTTP cases cover subscription/welcome, published ZIP, draft 409, unsubscribe suppression, and non-object JSON rejection.
- Seed-only smoke -> `{"issues": 3, "sources": 3, "subscribers": 1}`; archive=3, sources=3, subscribers=1.
- Representative `issue-003` UNSENT ZIP = 1,489 bytes in the deterministic test clock fixture.
- Pre-publication SHA-256: app.py `e1fbb1b2e77b1c4aace5aa7707213ee6b8c0fd5268c2f60f0a1e974622d3a751`; index.html `85167286a2143fa92ea4bc0eebb7a7e2032264d689c6740f2e2429d1d99e2083`; demo.json `7da8207da3925e3fcf3515b97fb4d5936cb90c1394a1a4cd2a6e64b5115a9a9b`; test_app.py `fda7ca155b78b51b3f17ce65a58d816157e2dff66956570b5aa5e88bc97306c1`; README.md `4dfce2d93fa55ded095f320e36f6235b20c9c40a97b5e1bcb9d6fca826b1d3f6`; .gitignore `8ed0cb81ec9fe0aaf8e73f4246aa2e7d3c037ced3bb7affd3aaec161e17ef1db`.
