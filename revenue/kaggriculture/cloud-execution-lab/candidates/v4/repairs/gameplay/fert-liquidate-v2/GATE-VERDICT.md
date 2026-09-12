# GATE VERDICT — r04_fert_liquidate v2

- v1: REJECTED — Mode A revenue-timing + buy stripping → ±$35k chaotic swings.
- v2: 9/9 tests pass (normal + python -O). Gated neutral/safe, mechanically
  non-negative: acts only at shed>=98 with fertilizer present, dumps
  min(fert, total-90), never strips buys, fail-closed on missing stock.
- Default OFF. v4.1 candidate (filed after v4 freeze).
