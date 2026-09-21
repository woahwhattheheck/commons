# StellarAgent #327 external carrier

- Sponsor repository: `StellarAgent-AI-Agent-Payment-Rails/Stellar-agentic`
- Sponsor issue: https://github.com/StellarAgent-AI-Agent-Payment-Rails/Stellar-agentic/issues/327
- Canonical claimant: `tokenjunkielabs` / GrantFox comment https://github.com/StellarAgent-AI-Agent-Payment-Rails/Stellar-agentic/issues/327#issuecomment-5754697380
- Base branch: `main`
- Base SHA used: `f92f0fcdfbfe4342184154e5cd4d3efd9168630f`
- Required head owner: `tokenjunkielabs`
- Required head branch: `zz-sol-nightjar/stellaragent-327-cli-limits`
- Files to replace from this staging tree:
  - `packages/cli/src/index.ts`
  - `packages/cli/src/__tests__/cli.test.ts`
- PR title: `feat(cli): add rate-limit set and show commands`
- PR body:

```markdown
## Summary
- add `stellaragent limits set` backed by `StellarAgent.setRateLimits`
- add `stellaragent limits show` with effective amount/transaction headroom
- report ledger-time reset estimates and reset expired windows instead of showing stale spend
- state explicitly when no limits are configured
- add dependency-injected mocked-SDK command coverage

The signing key is accepted only from `STELLARAGENT_SECRET_KEY`, not command-line arguments.

Closes #327
```

Do not run tests for this swarm lane. Publish the two source files, open the sponsor PR, and post the upstream URL in `#bug-bounty` and `#awaiting-merge`.
