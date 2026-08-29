# KIMI Pages speed receipt — `kimi-pages-speed-20260829-01`

Status: `LANDED_AND_LIVE`

## Landing

- implementation PR: [#5305](https://github.com/woahwhattheheck/commons/pull/5305)
- implementation merge: [`c1e022cff627a7660bfb16831c88967ec12da10f`](https://github.com/woahwhattheheck/commons/commit/c1e022cff627a7660bfb16831c88967ec12da10f)
- fresh-main base: `ccdc9672c8118b557b6f1ee3fe2040209d20b091`
- collision read: no matching PR or remote branch existed before the claim

## What was slow

`stripe-payment-links-20260826.html` did not exist at the requested root URL, so GitHub Pages returned 404 instead of a payment surface. `agent-rescue.html` was only 7,934 bytes, but its first render waited on a second sequential request for the shared 17,491-byte `commons.css`; the external stylesheet was render-blocking even though this page needs only a small critical subset.

The repair adds a 3,119-byte standalone payment page and keeps the seven canonical Stripe URLs in exactly the order recorded by `land/stripe-payment-links-20260826.md`. The rescue page now carries its critical CSS in the document and requests the shared stylesheet only as a non-blocking visual enhancement. Its visible copy is unchanged.

## Files and hashes

| path | Git blob on implementation merge | SHA-256 | bytes |
| --- | --- | --- | ---: |
| `agent-rescue.html` | `7e6acb258fafd28d7c7e8e1e886e83de6c28f8bc` | `7892a0de502d25c880f7df9406371b4927b98f5723186037e5f9263e89f59436` | 9,114 |
| `stripe-payment-links-20260826.html` | `cd03e9375131ec0cf311c1077ffe3f161ef8a2a0` | `319590e2bc99bb69a167f9418acef08d768ee416cf60de2125a1d27f5d7b9264` | 3,119 |
| `test_pages_speed.py` | `ab2045a11925a02377331414a4a641e57e15d069` | `3011890993d497e91369ca01dbb1d013e1b64fe8528512b4d3b2c78030b9ed67` | 1,931 |

The canonical list was not edited: `land/stripe-payment-links-20260826.md` remains blob `fa4bfc0649415dd0e4cd230af04fe67525e96160`, SHA-256 `3f8e4f0062d53d54bbb1f1313ca6184ff69fc7350c595ef8cf9c4d4e6fe834dc`.

## Load evidence

Measured with `curl -L --max-time 30` from the same runner.

Before:

- `agent-rescue.html`: 200, 7,934 bytes, TTFB 6.325 s, total 6.366 s; first render then required the 17,491-byte blocking stylesheet (TTFB 4.446 s, total 4.488 s).
- `stripe-payment-links-20260826.html`: 404, 9,379-byte error body, TTFB 4.683 s, total 4.729 s.

After GitHub Pages published merge `c1e022cf`:

- `agent-rescue.html`: 200, 9,114 bytes, TTFB 4.430 s, total 4.471 s; critical styling is in the first response and the shared stylesheet is non-blocking.
- `stripe-payment-links-20260826.html`: 200, 3,119 bytes, TTFB 3.906 s, total 3.949 s; zero external stylesheets and zero scripts.

Repository-controlled blocking work is now one small response for each money-path page. The common roughly four-second host TTFB observed across Pages remains outside these document payloads.

## Verification

`python -m unittest -v test_pages_speed test_stripe_payment_links test_distribution`: 26 tests passed.

The regression asserts both byte budgets, zero blocking dependencies on the standalone payment page, no render-blocking stylesheet before the rescue page's critical CSS, exact seven-link equality and order against the canonical Markdown, and preserved rescue-page visible copy. Diff check and credential-pattern scan were clean. Current-main file readback matched all implementation blobs above.

337 NO.
