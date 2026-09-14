# Current Readiness Authority Guard

A preventive static-analysis gate for **new or changed revenue Python**. It exists because exact-head reviews repeatedly found current-readiness surfaces whose authority could be minted by the same caller packet they were supposed to verify: backdated `as_of` fields, caller-selectable current clocks, one-packet `*_READY` decisions, and verifiers that replay a receipt's retained clock rather than reacquiring process time.

This tool does **not** prove buyer facts, source completeness, corporate evidence, pricing, legal authority, staffing, or submission authority. It only detects a narrow set of code shapes that have already caused real stop-merge findings in this repository.

## Rules

- `CRG000` — source could not be parsed/read safely enough to analyze.
- `CRG001` — caller-derived time participates in a deadline/expiry comparison.
- `CRG002` — a public readiness surface accepts caller-selectable time/clock parameters and can emit a current-positive state.
- `CRG003` — a public readiness surface can emit `READY`/`*_READY`/`VALID`/`CLEAR`/`REUSABLE` from one caller data packet without a separate authority/root/receipt/evidence input.
- `CRG004` — a public verifier feeds retained caller/report time into a current projection without sampling process UTC itself.

Analysis is AST-only. Scanned revenue modules are never imported or executed.

## Usage

```bash
python -m tools.current_readiness_guard.cli scan revenue/path/to/gate.py
python -m tools.current_readiness_guard.cli --json scan revenue/path/to/gate.py
python -m tools.current_readiness_guard.cli changed --base <base-sha> --head <head-sha>
python -m tools.current_readiness_guard.cli all  # advisory full-repo audit
```

Exit codes: `0` no unexempted findings, `1` findings, `2` policy/tooling failure.

## Central exemptions only

Inline comments cannot suppress findings. `policy.json` is the only exception surface. Each exemption binds an exact repository path + rule and must include rationale, owner, tracking issue, and a non-expired `YYYY-MM-DD` expiration date. Duplicate, malformed, or expired policy entries fail closed.

Example:

```json
{
  "schema": "commons-current-readiness-guard-policy/v1",
  "exemptions": [
    {
      "path": "revenue/example/legacy_gate.py",
      "rule": "CRG003",
      "rationale": "Legacy gate is isolated while authority adapter #123 is completed",
      "owner": "Z-Example",
      "issue": "#123",
      "expires": "2026-10-01"
    }
  ]
}
```

An exemption is reviewable debt, not evidence that the code is safe.

## CI scope

The workflow triggers for pull requests touching `revenue/**/*.py` or the guard itself. It runs py_compile and the hostile/safe corpus under normal and optimized Python on 3.11/3.13, then diffs the exact PR base/head and scans only changed revenue Python. Existing unrelated revenue modules are not retroactively seized by this landing.

Direct-to-main pushes can bypass a pull-request-only changed-file fence unless repository policy prevents them; this package does not claim branch-protection authority.
