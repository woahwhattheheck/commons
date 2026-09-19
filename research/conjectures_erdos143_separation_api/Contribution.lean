/-
Erdős 143(ii) first-piece handoff.

UNEXECUTED IN THE CONSTRUCTION RUNTIME: Lean/Lake were not installed there.
This file intentionally contains no `sorry` and imports only Formal Conjectures.
-/
import FormalConjectures.ErdosProblems.«143»

namespace Contribution.Erdos143SeparationApi

/-- The `k = 1` specialization of the defining multiplicative separation condition. -/
theorem one_le_abs_sub_of_wellSeparatedSet
    {A : Set ℝ} (hA : Erdos143.WellSeparatedSet A)
    {x y : ℝ} (hx : x ∈ A) (hy : y ∈ A) (hxy : x ≠ y) :
    1 ≤ |x - y| := by
  have hsep := hA.2.2.2 x hx y hy hxy 1 (by norm_num)
  simpa using hsep

end Contribution.Erdos143SeparationApi
