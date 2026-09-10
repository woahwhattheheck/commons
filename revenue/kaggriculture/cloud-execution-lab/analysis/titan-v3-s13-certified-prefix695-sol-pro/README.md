# TITAN V3 S13 exact-certified prefix-695

This additive research child closes the executable seam between:

- draft **#12095**, the high-scoring Pensukesan prefix-695 route; and
- draft **#12067**, the reviewed exact own/prestate action certificate.

It does **not** promote the leader route. It answers the stricter question: can a
retained replay action still be emitted when the live state is exactly in the
source action's reviewed applicability domain?

## Contract

`certified_prefix.py` reads the generated prefix arm without executing it,
strictly decodes its contiguous tape, binds the exact source replay, aligns
frame `i+1`'s action to frame `i`'s pre-action observation, and verifies every
tape action and structural signature. It then embeds #12067's certificate beside
each retained row and emits a deterministic child arm plus a receipt.

`certified_route_runtime.py` advances the frozen incumbent **before** every
route check. It emits no replay-derived component unless the live certificate
matches the embedded source certificate. Missing rows, malformed actions,
configuration drift, source-seat drift, or certificate mismatch irreversibly
hand control to that already-advanced incumbent for the rest of the game.

The source seat is intentionally bound. Cross-seat transplantation is not
silently treated as equivalent. The market certificate binds own/private and
public market prestate only; it makes no claim about the rival's hidden
simultaneous market queue or exact market outcome.

## Reproduction

The dedicated workflow:

1. verifies the child is a direct successor of #12095 head
   `05b64a03855be9856a03801ed608407707eb0404`;
2. fetches #12067 head `cbfff2bec813e2c2609ce9c5819b74669e98c566`,
   verifies `action_applicability.py` blob
   `89a3325eb541ae0e8a81e1e0a426292820f10d98`, and checks certificate parity;
3. runs all focused contracts;
4. downloads and hashes replay `107223760`, materializes the exact frozen
   control, rebuilds the full and prefix-695 arms, then emits the certified arm;
5. reuses the existing four frozen seeds in both seats against Arlene and V1,
   producing a three-arm exact-cell report. No fresh seed is consumed.

A `CERTIFICATE_REJECTS_TRANSPLANT` result is a useful result: it means the prior
uplift depended on actions applied outside their exact source domain. A
`CERTIFIED_SURVIVOR` still requires T08's broader paired tail gates before any
promotion decision.

No canonical runtime, config, archive, pointer, provider, Kaggle, promotion,
release, or submission state is changed.
