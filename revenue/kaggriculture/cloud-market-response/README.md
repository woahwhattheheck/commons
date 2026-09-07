# T12: public-history market response

Experimental callable, not a replacement for the selected frozen SELL policy.

Use `from policy import ResponsePolicy`; create one instance per actor/match,
then `policy.act(observation, configuration)`. `policy.agent` is the file-agent
entrypoint. `ResponsePolicy(enabled=False)` retains the unchanged SELL optimizer
with the same observation diagnostics. Runtime has no engine, seed, network,
private-rival or persistent replay input. Existing sibling SELL runtime and all
its licenses remain required; its scheduler SHA256 is pinned in policy.py.

`FlowHistory.add(FlowInterval(...))` accepts completed observation intervals.
`window_prediction(product, now, end)` returns complete historical window
samples, totals and empirical bounds; `scenarios` preserves batch timing with
explicit relative order and phase uncertainty. These are conditional cases,
not calibrated probabilities. Censored intervals are not fictitious zero sales.

SORREL's unmodified adapter supplies interval identification and an independent
receipt cross-check. MarketPath supplies the existing exact paired-receipt
scoring. The policy retains one authoritative Arlene call, parent routes,
non-SELL order indices, purchase/cash reservations and shed/slot feasibility.
It augments a completed frozen-SELL plan, not the weaker raw tape reference.

This is the source checkpoint. Validation scripts, preserved v1 negative
results, frozen development/held results and reproduction instructions are
being attached in the same T12 work batch. No hosted game or rating is claimed.
