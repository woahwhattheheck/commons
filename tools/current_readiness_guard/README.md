# Current Readiness Authority Guard

A preventive AST-only gate for new or changed revenue Python. It targets repeated stop-merge defects where current readiness could be minted from caller-owned clocks, caller-authored evidence, or a verifier replaying retained time.

The scanner does not import or execute target modules. It follows same-module calls from public surfaces into private helpers, resolves simple local/global positive-state aliases, and treats arbitrary caller-derived values as untrusted when they reach deadline/currentness decisions.

## Rules

- `CRG000` — source cannot be parsed or read safely.
- `CRG001` — caller-derived data reaches a deadline/expiry comparison, including through a private helper.
- `CRG002` — a public current-positive surface accepts a caller-selectable time/clock override.
- `CRG003` — a current-positive path is not controlled by an actually consumed independent authority parameter. Merely naming an unused parameter `authority`, `root`, `receipt`, or `evidence` does not suppress the rule.
- `CRG004` — a verifier replays retained caller/report time without a process-owned clock projection that is actually used in its result. Unrelated clock samples and caller-owned `timer.now()` objects do not count.

The analysis is intentionally conservative. It does not prove that an authority parameter is externally authentic; it proves only that a distinct authority value is mechanically consumed as a control on every detected positive path. Provider/source authenticity remains a separate runtime obligation.

## Usage

```bash
python -m tools.current_readiness_guard.cli scan revenue/path/to/gate.py
python -m tools.current_readiness_guard.cli --json scan revenue/path/to/gate.py
python -m tools.current_readiness_guard.cli changed --base <base-sha> --head <head-sha>
python -m tools.current_readiness_guard.cli all
```

Exit codes: `0` no unexempted findings, `1` findings, `2` policy/tooling failure.

## Central exemptions only

Inline suppression is unsupported. `policy.json` is the only exception surface; each entry binds exact path + rule and includes rationale, owner, issue, and a non-expired date. An exemption is reviewable debt, not evidence that code is safe.

## Scope ceiling

This guard cannot establish buyer facts, source completeness, corporate evidence, pricing, staffing, legal/submission authority, award, payment, or revenue. It only blocks known unsafe source shapes. Direct-to-main pushes can bypass a pull-request-only changed-file workflow unless repository policy prevents them.
