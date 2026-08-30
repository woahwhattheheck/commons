# Commons data license decision package — 2026-08-30

State: **STAGED, UNDECIDED.** This package decides nothing. The rights holder's one word does.

## The blocker

Every Commons data corpus (CI receipts, board feed sample, the wider p/ archive) sits at
`NOASSERTION`: the repository has no root `LICENSE`, `COPYING`, or `NOTICE` file. Payload
release and transfer stay `BLOCKED_LICENSE_REQUIRED` until the rights holder names reuse
terms. The data itself is real, checksummed, scanned, and staged — the only missing piece
is the license word.

## The decision — pick one, or the split

**A. CC0 1.0 Universal (public domain dedication).**
Anyone may use the data for anything, no attribution, no revenue from the license itself.
Maximum research uptake; zero leverage.

**B. Creative Commons Attribution 4.0 International.**
Free reuse, including commercial, with attribution. The standard research-dataset posture:
citations and reputation compound into demand; the license itself stays free.

**C. Commons Commercial Data License (paid instrument).**
Public reading stays free — the open door is untouched. Commercial reuse, redistribution,
or exclusivity requires a paid agreement with the rights holder. The license *is* the
product: buyers pay for rights, warranties of provenance, and verified delivery.

**Recommended split (assistant inference, flagged as not decided):** B on the public record
(attribution → citations → demand), plus C staged as the paid instrument for buyers who
need commercial terms, no-attribution use, or exclusivity. The two coexist: free with
attribution, or paid without.

## Unblock mechanics (each step staged, none executed here)

1. Rights holder says the word: A, B, C, or the split.
2. One commit adds `LICENSE-DATA.md` at the repository root carrying the chosen text.
3. Corpus manifests flip with evidence: `license.status` → `LICENSED`,
   `release.state` → `RELEASED`, validators updated to the recorded decision.
4. The sample pack publishes on `data-license.html`; the offer lists a price.
5. The demand lane runs the public `OFFER` inbox.

## What this package is not

Not a license. Not a sale. Not legal advice. No rights are granted by this file.
