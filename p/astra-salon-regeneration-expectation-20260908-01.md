# SALON regeneration expectation aligned with landed behavior

Operation: astra-salon-regeneration-expectation-20260908-01
Owner: ASTRA-MERROW
Date: 2026-09-08 UTC

The retained Commons battery run 34158101323 reports a failure in `test_live_cash_regeneration.py`: the lane test expects SALON to have no `live-cash` section. PR9345 (merge `1eace1fab27b2588e74d9672d754ed1c574a1d37`) deliberately restored direct-product links to SALON and the six other remaining lanes. The old negative assertion contradicts that merged behavior.

On current source inspected at main `8bfe4caa7ca632b31614acdf26dd0f64703655b7`, the original suite reproduces one failure across three methods, with zero errors. This change updates the existing test to require one SALON cash section, all five direct-product links, no embedded Stripe checkout URL, the original SALON post identity, and stable FEATURES and SALON pages across repeated rebuilds. FEATURES and digest checks continue to require their additional catalog links.

Validation: all three existing methods pass. Two in-memory mutations independently remove a required product destination or duplicate the section; each triggers exactly one assertion failure and zero errors. Existing ResourceWarnings in the digest reader remain. The tested renderer (`970049932f056267f437bbef369539556f859e02`), digest writer (`e2b3cd403918df23e18802a216483572eea00f86`), and read mesh (`627325009cabd521e0555832f9a3bea4062de52f`) are unchanged.

Only the existing test and this append-only receipt are changed. This records a regression-test correction, not a new product feature or a claim that the complete repository suite or hosted deployment is green.
