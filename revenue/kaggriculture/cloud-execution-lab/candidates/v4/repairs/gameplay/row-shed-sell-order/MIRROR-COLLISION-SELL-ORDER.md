# Mirror-collision SELL order — additive ROWSHED research

Status: **research/default-OFF; not runtime promotion authority**.

This packet consumes the September 12 mirror-loss forensics without creating a
second V4 controller. It lives beside the canonical `row-shed-sell-order` donor
and leaves that incumbent source untouched.

## Source-real theorem

Pinned engine `3c202c7ee921da239356789e266b694635103fc4` processes market
rows by raw queue index. At one index it quotes both players from the same
pre-commit public inventory, then commits both unit-by-unit. A SELL block at an
earlier queue index therefore clears before a same-item block at a later index.

For public inventory `I` and executable own fill `q`, `mirror_delay_value()`
computes our exact cash difference between:

1. our q-unit SELL block clearing before an equal-size same-item mirror block;
2. that mirror block clearing before ours.

The simulator also reproduces the official floor rule: a SELL quoted at `$1`
does **not** increase public inventory. This matters materially for WOOL/MELON
glut tails and is missed by an endpoint-only formula.

This is a counterfactual sensitivity score. It does not read or predict the
opponent's live action, so descending score is **not** claimed to dominate for
an arbitrary rival. Activation still requires the current ROWSHED returned-
action witness and a current-native/field economic gate.

## Concrete inversion

With official curves, `I=10050`, executable fill `q=25`:

| item | incumbent endpoint `(p(I)-p(I+q))*q` | exact mirror-delay value |
|---|---:|---:|
| WOOL | 1350 | 264 |
| MELON | 775 | 931 |

The incumbent endpoint heuristic ranks WOOL first; exact mirror-delay exposure
ranks MELON first. WOOL hits the `$1` floor after inventory 10059, so public
supply freezes there; its q=25 early cash is 289 and delayed cash is 25.

## Custody / fail-closed boundary

The additive transformer is literal-`True` opt-in and otherwise exact identity.
When enabled it may only permute the leading contiguous parser-live SELL block
inside `maxMarketOrdersPerTurn`. It never changes queue length, row bytes,
quantities, non-market fields, a barrier row, or the inert suffix. A zero or
negative SELL quantity is a hard barrier. Fill is `min(requested, post_unit_shed)`
so nominal `SELL 1000` cannot manufacture a score from one held unit. Duplicate
products fail closed because two rows share one projected stock pool.

No runtime/default/config/COMPOSITION/INTEGRATION/archive/Kaggle mutation is
authorized by this packet.
