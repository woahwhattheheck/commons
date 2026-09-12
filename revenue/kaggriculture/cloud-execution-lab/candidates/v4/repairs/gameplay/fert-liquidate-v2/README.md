# r04_fert_liquidate v2 — fertilizer overflow loss-prevention

Antigravity's $1 fertilizer warehouse, minimal safe form (credit: Antigravity).

The engine destroys any collected item that doesn't fit in the 100-cap shed.
This lane converts would-be-destroyed fertilizer into cash instead of letting
it be destroyed for $0. It ONLY acts when the shed is imminently full
(>= 98 total items) and holds fertilizer, dumping just enough to reach 90.

v1 was REJECTED: Mode A (early revenue-timing sales + buy stripping) changed
early-game cash flow and produced chaotic ±$35k cell swings. v2 is cash-flow
neutral until the moment of imminent destruction and never strips buys.

Default OFF. Flag: r04_fert_liquidate=true.
