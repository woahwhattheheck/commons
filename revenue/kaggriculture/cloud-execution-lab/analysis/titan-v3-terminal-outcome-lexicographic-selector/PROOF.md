# Safety argument

Let `I_s` be the incumbent terminal result and `C_s` a candidate terminal result for modeled scenario `s`. Define:

- `own(X_s)` as TITAN terminal cash;
- `margin(X_s) = own(X_s) - rival(X_s)`;
- `outcome(X_s)` as `L=-1`, `T=0`, or `W=1` according to the sign of `margin(X_s)`.

A non-incumbent plan is eligible only if, for every required scenario:

1. `outcome(C_s) >= outcome(I_s)`;
2. when `outcome(C_s) = outcome(I_s)`, both `own(C_s) >= own(I_s)` and `margin(C_s) >= margin(I_s)`;
3. `own(C_s)` is at least the predeclared absolute floor;
4. when `own(C_s) < own(I_s)`, the outcome is strictly improved and the sacrifice is no greater than the predeclared cap;
5. at least one scenario is strictly improved in outcome, own cash, or margin; and
6. the candidate commitment differs from the incumbent commitment.

The selector may return a candidate only from this eligible set. Therefore a returned candidate has no modeled W/T/L regression. In any scenario where the outcome class is unchanged it has no own-cash or margin regression. Any own-cash sacrifice is confined to an outcome-improved scenario and is bounded by both the absolute floor and sacrifice cap.

The final rank cannot weaken those invariants because ranking is applied only after eligibility. A candidate must also have a rank strictly greater than the incumbent. If more than one candidate shares the greatest admissible rank, the selector preserves the incumbent rather than inventing a tie-break. Malformed or incomplete evidence raises `ContractError`, and the CLI writes no replacement output until a complete report has been produced and sealed.

This is a conditional theorem over the supplied terminal certificates. It does not prove that the upstream engine, evaluator, scenario set, terminal trace, or bank values are truthful. Those are explicit integration preconditions and must be established by the executing carrier.
