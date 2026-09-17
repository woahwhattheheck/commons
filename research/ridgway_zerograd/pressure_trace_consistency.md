# Pressure-trace consistency blocker for the zero-gradient Nitsche prize

Status: **rigorous formulation-level counterexample and repair boundary; not a complete prize proof.**

Issue: #14998  
Operation: `RIDGWAY-ZEROGRAD-PRESSURE-TRACE-COUNTEREXAMPLE-ZSOL-20260917`

This note closes one ambiguity left by the existing `proof_reduction.md`: for a general nonconstant pressure, the pressure-free velocity Nitsche kernel written in Gjerde–Scott's Eq. (27)/(28) is not the full mixed Stokes consistency identity on divergence-free tests when normal velocity is weakly enforced.

The result is intentionally narrow. It proves a missing pressure-normal boundary term, gives two exact counterexamples, and states the minimum repair choices. It does **not** prove the full Scott–Vogelius–Nitsche convergence theorem, does not establish a quartic annulus lower bound, and does not claim the advertised prize.

## 1. The source-level mismatch

Gjerde–Scott's Stokes integration-by-parts identity, Eq. (5), contains the full Cauchy traction. With viscosity normalized to one, their identity has the structure

`(f,v) = 1/2 (D(u),D(v)) - (p,div v) - <(D(u)-pI)n,v>`

for a divergence-free exact solution, modulo the paper's symmetric-gradient convention and the displayed `grad div u` term, which vanishes when `div u=0`.

On an exactly divergence-free test `v`, the *volume* pressure term disappears, but the boundary contribution does not:

`(f,v) = a(u,v) - <D(u)n,v> + <p,v·n>`.

For an exact no-slip solution on the true boundary, `u=0` implies the tangential derivative of the trace is zero. Together with `div u=0`, this gives the familiar boundary identity needed to identify the velocity traction with the normal derivative under the paper's convention. The pressure-normal term remains separate.

By contrast, Gjerde–Scott Eq. (27) defines the velocity Nitsche form using `partial_n u`, its adjoint counterpart, and the penalty term. Eq. (28) then couples that velocity form to the usual volume `b(v,p)`. There is no explicit pressure-normal boundary term in the displayed weak-boundary form.

Therefore exact divergence freedom alone cannot justify replacing the full mixed traction by the pressure-free velocity flux whenever the test space permits `v·n != 0` on the weak boundary.

## 2. Exact low-degree counterexample on a fully weak square

Take

- `Omega=[0,1]^2`,
- exact velocity `u=0`,
- pressure `p=x`,
- forcing `f=grad p=(1,0)`, and
- test velocity `v=(1,0)`.

Then `v` has polynomial degree zero and `div v=0`. Thus it belongs to every full continuous `[P_k]^2` velocity space if the boundary is weakly imposed.

Exact arithmetic gives

`(f,v)_Omega = 1`,

`(p,div v)_Omega = 0`,

and, by the divergence theorem,

`<p,v·n>_boundary = 1`.

At `u=0`, every velocity-only Nitsche term in the published kernel is zero. Hence the pressure-free kernel produces left-hand side zero while the exact forcing functional equals one. The consistency defect is exactly `-1` in the `lhs-rhs` convention used by the executable certificate.

This is already enough to disprove a general statement that exact divergence freedom by itself deletes pressure from the weak-boundary Stokes consistency relation.

## 3. Mixed-boundary analogue: strong outer wall, weak inner obstacle

The sponsor geometry is not fully weak: the exterior boundary is strong while the curved obstacle boundary is the Nitsche boundary. The same pressure-normal defect survives that topology.

Use the square annulus

`Omega = [-2,2]^2 \ [-1,1]^2`,

with the outer square strongly constrained and the inner square weak. Define the polynomial stream function

`psi=(4-x^2)^2 (4-y^2)^2 (1+y)`

and

`v=curl psi=(partial_y psi,-partial_x psi)`.

Then:

- `div v` is identically zero by equality of mixed derivatives;
- the double factors `(4-x^2)^2` and `(4-y^2)^2` make **both components** of `v` vanish as polynomial traces on all four outer edges;
- `v` therefore respects the strong outer boundary exactly;
- the velocity has total degree eight, so this is a formulation-level mixed-boundary witness rather than a claim that this exact polynomial belongs to the sponsor's quartic discrete space.

Again choose `p=x`, `u=0`, `f=(1,0)`. The executable exact-rational certificate computes

`(f,v)_Omega = -2436/5`,

`(p,div v)_Omega = 0`,

and the pressure-normal work on the weak inner boundary

`<p,v·n>_inner = -2436/5`.

The exact inner-edge partition is

- `x=1`: `-162`,
- `x=-1`: `-162`,
- `y=1`: `-816/5`,
- `y=-1`: `0`.

The velocity-only Nitsche kernel at `u=0` is again zero. Thus the missing mixed-boundary consistency term is not an artifact of making the entire boundary weak.

## 4. Why this is not automatically an `h_Gamma^(3/2)` remainder

The already-landed geometry argument concerns the trace of the exact no-slip velocity on the displaced polygonal boundary. That trace is `O(h_Gamma^2)`, and the Nitsche half-order weight converts it into `O(h_Gamma^(3/2))`.

The pressure term is structurally different. A generic estimate is

`|<p-c,v_h·n>| <= ||h_e^(1/2)(p-c)||_Gamma_h ||h_e^(-1/2)v_h||_Gamma_h`.

Exact divergence freedom and zero normal flux on the other strong boundary allow subtraction of a **global constant** `c`, because the total weak-boundary flux vanishes. They do not permit independent edgewise constants without additional orthogonality.

For a smooth, genuinely nonconstant pressure on a boundary of `O(1)` length and quasi-uniform boundary scale `h_e~h_Gamma`, the first weighted factor is generically only `O(h_Gamma^(1/2))` when `c` is a global constant. Therefore the pressure-normal term cannot simply be filed under the already-proved `O(h_Gamma^(3/2))` velocity-geometry residual.

This paragraph is an **upper-bound scaling warning, not a quartic discrete lower-bound theorem**. A sharper method-specific cancellation could exist, but it must be proved from the actual Scott–Vogelius normal-trace space or from an additional pressure-trace mechanism.

## 5. Why the published manufactured test can hide the defect

The manufactured example immediately preceding the Nitsche experiment uses constant pressure. For `p=c`,

`<p,v_h·n>_Gamma_h = c int_Gamma_h v_h·n`.

If `v_h` is exactly divergence free and has zero normal flux on the remaining strong boundary, the divergence theorem makes this integral zero. Constant pressure therefore lies in a special cancellation class.

Consequently a successful constant-pressure numerical experiment does not by itself validate pressure robustness or consistency of the displayed weak-normal formulation for a general Stokes pressure.

## 6. Independent 2026 corroboration: weak normal velocity needs pressure-trace control

Neilan, Olshanskii, and von Wahl, *An unfitted divergence-free higher order finite element method for the Stokes problem* (arXiv:2512.12050v2, 22 July 2026), study a different divergence-free Stokes method, so their paper is not a proof of the Ridgway prize theorem. It is nevertheless directly relevant to the mechanism.

They explicitly identify a loss of pressure robustness associated with weak enforcement of the normal velocity and introduce a boundary Lagrange multiplier. Their discrete formulation contains

`c_h(lambda_h,v_h)=int_Gamma_h lambda_h n_h·v_h`,

with the multiplier approximating the pressure trace / normal-traction information needed at the weak boundary. Their no-flow pressure test (`u=0` with nonconstant pressure) is designed precisely to expose spurious velocity generated by imperfect pressure decoupling.

That contemporary independent treatment supports the algebraic conclusion here: weak normal velocity is where pressure can re-enter a nominally divergence-free velocity equation through the boundary.

## 7. Minimum theorem repairs

A prize-ready theorem must close this blocker explicitly. Viable routes include:

1. **Stress-consistent Nitsche formulation.** Use the full Stokes traction, including pressure-normal work, and analyze the resulting mixed method, adjoint terms, stability, and geometry residuals.
2. **Pressure-trace / normal-constraint multiplier.** Introduce a stable boundary variable or constraint that carries the pressure-normal information while retaining the weak-boundary freedom needed to avoid the original strong zero-gradient pathology.
3. **Prove a discrete cancellation theorem.** Show that the actual Scott–Vogelius weak-boundary normal-trace space is orthogonal to the relevant pressure trace up to the required `O(h_Gamma^(3/2)+h_Omega^k)` order. This cannot be assumed from `div v_h=0` alone.
4. **Restrict the theorem.** A result limited to the constant-pressure manufactured solution may exploit the constant-flux cancellation, but it would not be the general mixed Stokes theorem suggested by the prize statement.

Closing this pressure blocker still leaves the other previously recorded requirements: curved-to-polygonal divergence-compatible approximation/transfer, weak-boundary inf-sup and pressure recovery, complete geometry residual closure, a full PDE penalty sweep, independent mathematical review, and publication.

## 8. Reproducibility and evidence ceiling

`pressure_trace_counterexample.py` uses only Python's `fractions.Fraction`. Its retained tests verify the low-degree square witness, exact zero strong outer trace for the annulus stream-function witness, exact forcing/pressure-boundary equality, and the four edge contributions under both normal Python and real `python -O`.

The machine-readable certificate is stored in `results/pressure_trace_counterexample.json`.

Truth ceiling:

- **proved here:** pressure-free weak-normal velocity consistency fails in the displayed general form; exact low-degree fully-weak witness; exact mixed-boundary formulation witness;
- **not proved here:** a quartic mixed-boundary discrete lower bound, the full convergence theorem, publication, prize eligibility/award, receivable, or cash.

No sponsor or author contact is performed by this carrier.