# Ridgway–Freudenthal Scott–Vogelius lane

Issue: https://github.com/woahwhattheheck/commons/issues/14999

This is the isolated research surface for the Freudenthal/Kuhn divergence problem. It does not submit anything to the Ridgway Scott Foundation or claim a prize.

## Usable two-cube quartic mean repair

[The constructed operator and derivation](P4_MEAN_REPAIR.md) realize any twelve zero-sum cell-average divergences with a continuous piecewise-quartic velocity, zero boundary trace, and zero divergence on every tetrahedral edge.

```sh
python research/ridgway_freudenthal/p4_mean_repair.py \
  --means 1 0 0 0 0 0 0 0 0 0 0 -1
```

Python 3.10+, standard library only. The reusable sparse rational operator is `p4_mean_repair_basis.json`. Its tetrahedra and Bernstein coefficient ordering are explicit. The exact construction has 189 unknowns, edge rank 122, combined edge/mean rank 133, and 202 nonzero operator coefficients. It establishes the local mean-repair image, not the full mesh-uniform theorem.

## Rectangular-grid composition

[The grid solver and derivation](P4_GRID_MEAN_REPAIR.md) extend the local operator to any rectangular Kuhn grid with at least two cubes, including exact translation and isotropic scale. Use `p4_grid_mean_repair.py input.json --output velocity.json`. It matches all zero-sum cell means, preserves zero edge divergence and boundary trace, and returns shared sparse Bernstein coefficients. The guide also gives an explicit fixed-patch bound and explains how to preserve a raw lift's edge traces while removing its cell means. The whole-domain bound depends on the cube count; it is not the mesh-uniform theorem.

## Protected body-diagonal lift

[The degree-four body-diagonal operator](P4_BODY_DIAGONAL_LIFT.md) now accepts any
twelve interior cubic edge coefficients and returns a continuous quartic field
with those traces, zero divergence on every other edge, zero patch boundary trace,
and zero cell means. It composes the existing local mean repair on a fixed two-cube
patch. Run `p4_body_diagonal_lift.py --trace 1 -1 2 -2 3 -3 4 -4 5 -5 6 -6`.
The exact 189×12 map has 270 nonzeros and a reference seminorm-squared bound of
1728 times the trace-coefficient norm squared.

[The degree-five companion](P5_BODY_DIAGONAL_LIFT.md) accepts eighteen coefficients
and degree-elevates the same quartic mean correction. Its exact 432×18 map has
1,763 nonzeros and seminorm-squared bound `39744/49` in trace-coefficient norm.
Use `p5_body_diagonal_lift.py --trace` with eighteen values, three per cell.
Other edge classes, neighbor selection/transport and the global theorem remain
separate work.

## Singular interior face-diagonal lift

[The face-diagonal operator](FACE_DIAGONAL_LIFT.md) supplies both degrees on the
fixed shared face of two Kuhn cubes. It reconstructs the actual checkerboard
source relation `y1-y2-y3+y4=0` per mode, then builds a protected, zero-cell-mean
lift for every compatible trace. Use `face_diagonal_lift.py --degree 4` or
`--degree 5`, with eight or twelve trace coefficients. Admissible dimensions are
six and nine; final maps have 34 and 174 nonzero coefficients. Other orientations,
edge classes, the full census and global assembly remain separate.

## Original problem

On a Freudenthal tetrahedral mesh of a cubical domain, let `V_h^k` be the continuous vector degree-k polynomial space with zero boundary trace, and let `Q_h^k = div V_h^k`.

The sponsor's original question asks for an inf-sup constant independent of mesh size for every fixed `k ≥ 4`; Zhang established the higher-degree `k ≥ 6` case. The September 2026 Alfyorov preprint proposes a proof for the two lower degrees. Its complete argument and sponsor disposition are not certified here.

Sponsor and original research sources:
- https://people.cs.uchicago.edu/~ridg/prizes/kuhnprize.pdf
- https://people.cs.uchicago.edu/~ridg/prizes/prizes.html
- Farrell–Mitchell–Scott, arXiv:2211.05494
- Alfyorov, Research Square DOI `10.21203/rs.3.rs-10887173/v1`

## Existing results retained

The original `kuhn.py` supplies the six exact positively oriented tetrahedra, with each six-times-volume equal to one. The earlier local divergence calculation covers a single unrestricted polynomial cell and does not encode inter-cell continuity or boundary conditions.

[The earlier Zhang-import audit](verification_alfyorov/ZHANG_IMPORT_AUDIT.md) distinguishes raw edge matching, already available at degree four, from the degree-six element-mean correction used in Zhang's construction. The new two-cube operator supplies a degree-four local mean correction; it does not by itself establish the separate protected edge-star lifting.

Still unresolved in this lane: the full protected-map/census reconstruction, its actual global source-space compatibility, and the mesh-uniform theorem. No prize, payment, or submission is asserted.
