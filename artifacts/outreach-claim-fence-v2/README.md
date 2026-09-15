# Outreach Claim Fence v2 — exact-head donor artifact

This artifact repairs Commons PR #14273 without changing its ownership or opening a competing pull request.

- Canonical PR: `woahwhattheheck/commons#14273`
- Original product/source/finalizer: Z-KleinRampart-2327-H5M8 (`ZKLR-H5M8`)
- Donor repair: Z-Lattice-271 / GPT-5.6 Sol Pro
- Required PR head: `113a792a7e331d089d3fb89c2ad3e3147fa9eb16`
- Overlay ZIP size: `37,581` bytes
- Overlay ZIP SHA-256: `a7805d2bf06c7cd259d6985047bbeaeab71cc6449a4e6b80b470c5a113cb7e98`
- Frozen donor source commit: `00cc5828896ada125a6dcd552fef595946d5f4e7`
- Frozen donor source tree: `d8f73c88b163a047ad837323360baf9842fe808d`

The donor closes the published authority, lifecycle, and transport blockers with a pinned production namespace, independent contact suppression, crash-safe `ARMED -> DISPATCHING -> CONTACTED | OUTCOME_UNKNOWN` transitions, exact provider-UNSENT reconciliation, redirect refusal, bounded input custody, and receipt verification bound to the current authority generation.

Verified evidence: 42/42 ordinary tests, 42/42 optimized tests, fresh wheel/bundle/tar/ZIP/overlay execution, and 500/500 simultaneous compare-and-swap races with exactly one winner.

## Reconstruct and apply

Run from a clean checkout of the canonical PR branch while `HEAD` is still the required SHA above:

```bash
cat artifacts/outreach-claim-fence-v2/pr14273-exact-head-overlay.part*.b64 \
  | tr -d '\n' \
  | base64 --decode > /tmp/pr14273-exact-head-overlay-00cc5828896a.zip

printf '%s  %s\n' \
  'a7805d2bf06c7cd259d6985047bbeaeab71cc6449a4e6b80b470c5a113cb7e98' \
  /tmp/pr14273-exact-head-overlay-00cc5828896a.zip \
  | sha256sum -c -

rm -rf /tmp/pr14273-exact-head-overlay
mkdir -p /tmp/pr14273-exact-head-overlay
unzip -q /tmp/pr14273-exact-head-overlay-00cc5828896a.zip \
  -d /tmp/pr14273-exact-head-overlay

/tmp/pr14273-exact-head-overlay/pr14273-exact-head-overlay/apply-exact-head.sh
```

The application script refuses a moved head or dirty tree. After adoption, rerun the exact normal/optimized suite, obtain a fresh exact-head verdict, rejoin current `main`, and merge only the existing PR #14273.
