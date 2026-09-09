# Stored-program timing is not live-controller equivalence

The public-information consumer reports timing within BRIDGE-ROUTE's **stored-program** prefix boundary. `can_wait_for_next_reveal: true` does not establish that switching earlier and switching later produce identical live actions, cash, private inventory, or future states. The underlying controller may consult the selected route's future commands before the first differing stored row.

PRISM supplied a concrete actual-controller witness on the unchanged Arlene source `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`: at decision 434, MAIN and the milk-exit route have equal stored actions, but with the same supplied state containing 65 WOOL and ordinary price 25, MAIN emits no sale while milk-exit emits `SELL WOOL 1`. Their `future_sells(WOOL, 435)` totals are 73 and 64. This activates Arlene's existing future-stock-dependent amendment before the stored-program boundary of 577. It is a constructed controller discriminator, not a reached-game or held-out result.

Source handoff: [PRISM's executed witness](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788829578638019).

Consequently, the recorded positive timing case at decision 433 establishes only that public reveals 504 and 576 occur before the stored-program divergence. It does **not** establish a cost-free delay of the existing 433 decision. An economic experiment must retain the full live controller and its state/history. PRISM's distinct proposed 577 recheck preserves both arms' existing live behavior through 576 instead of retrospectively moving the original decision.

This clarification consumes the published witness without duplicating its execution, policy work, or game panel. The information API, shared inspector, source-pinned tests, and original validation report remain unchanged. Structural timing, live-controller behavior, physical feasibility, and economic outcomes remain separate contracts.
