# Independent authority model

The qualification manifest is not a trust root. It is caller input. Current readiness is derived from verifier time plus independently retained authority packets whose exact SHA-256 values must already be present in the evaluator source-bound trust-root sets.

Production/source-bound trust-root sets are intentionally empty while the buyer questionnaire is unavailable. Synthetic tests may rebind the public TRUSTED_* names and call evaluate(..., now=...); that helper is non-authoritative and cannot emit CURRENT commercial readiness. evaluate_current / the CLI bind roots at source definition time and refuse a caller clock.
