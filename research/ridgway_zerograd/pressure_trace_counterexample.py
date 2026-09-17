#!/usr/bin/env python3
"""Exact pressure-trace consistency counterexamples for Commons #14998.

This module is deliberately dependency-free.  It does not solve the prize theorem.
It certifies two narrow algebraic facts:

1. On a fully weak boundary, u=0, p=x, f=(1,0) and the constant
   divergence-free test v=(1,0) already expose the missing pressure-normal
   work: (f,v)=1 while every velocity-only Nitsche term at u=0 is zero.

2. The same phenomenon survives the sponsor topology "strong outer boundary,
   weak obstacle boundary".  On a square annulus we construct an exact
   polynomial stream function whose curl is divergence free and vanishes on
   the entire strong outer boundary.  With p=x and f=(1,0), its forcing
   pairing equals the pressure-normal flux on the weak inner boundary and is
   exactly -2436/5, while the pressure volume pairing is zero.

The second velocity has polynomial degree 8.  It is therefore a
formulation-level mixed-boundary consistency witness, not a claim that this
exact polynomial lies in the sponsor's k=4 discrete space.
"""
from __future__ import annotations

from fractions import Fraction
import json
from typing import Dict, Iterable, Tuple

Q = Fraction
Monomial = Tuple[int, int]
Poly = Dict[Monomial, Q]
Poly1 = Dict[int, Q]


def clean(p: Poly) -> Poly:
    return {m: Q(c) for m, c in p.items() if c}


def add(*polys: Poly) -> Poly:
    out: Poly = {}
    for p in polys:
        for m, c in p.items():
            out[m] = out.get(m, Q(0)) + c
    return clean(out)


def scale(p: Poly, a: Q | int) -> Poly:
    a = Q(a)
    return clean({m: a * c for m, c in p.items()})


def mul(*polys: Poly) -> Poly:
    out: Poly = {(0, 0): Q(1)}
    for b in polys:
        nxt: Poly = {}
        for (i, j), ca in out.items():
            for (k, ell), cb in b.items():
                m = (i + k, j + ell)
                nxt[m] = nxt.get(m, Q(0)) + ca * cb
        out = clean(nxt)
    return out


def derivative(p: Poly, axis: str) -> Poly:
    out: Poly = {}
    for (i, j), c in p.items():
        if axis == "x" and i:
            out[(i - 1, j)] = out.get((i - 1, j), Q(0)) + c * i
        elif axis == "y" and j:
            out[(i, j - 1)] = out.get((i, j - 1), Q(0)) + c * j
        elif axis not in {"x", "y"}:
            raise ValueError("axis must be x or y")
    return clean(out)


def integrate_rect(p: Poly, xa: int, xb: int, ya: int, yb: int) -> Q:
    total = Q(0)
    for (i, j), c in p.items():
        ix = Q(xb ** (i + 1) - xa ** (i + 1), i + 1)
        iy = Q(yb ** (j + 1) - ya ** (j + 1), j + 1)
        total += c * ix * iy
    return total


def restrict_x(p: Poly, x0: int) -> Poly1:
    out: Poly1 = {}
    for (i, j), c in p.items():
        out[j] = out.get(j, Q(0)) + c * (Q(x0) ** i)
    return {j: c for j, c in out.items() if c}


def restrict_y(p: Poly, y0: int) -> Poly1:
    out: Poly1 = {}
    for (i, j), c in p.items():
        out[i] = out.get(i, Q(0)) + c * (Q(y0) ** j)
    return {i: c for i, c in out.items() if c}


def integrate_1d(p: Poly1, a: int, b: int) -> Q:
    return sum(
        (c * Q(b ** (degree + 1) - a ** (degree + 1), degree + 1)
         for degree, c in p.items()),
        Q(0),
    )


def degree(p: Poly) -> int:
    return max((i + j for (i, j) in p), default=-1)


ONE: Poly = {(0, 0): Q(1)}
X: Poly = {(1, 0): Q(1)}
Y: Poly = {(0, 1): Q(1)}


def square_annulus_witness() -> dict:
    # Omega = [-2,2]^2 \ [-1,1]^2.
    # psi has a double zero on every outer edge, so both components of
    # v=curl(psi) vanish there.  The (1+y) factor prevents cancellation
    # of the weak-inner-boundary pressure work.
    fx = mul(add(scale(ONE, 4), scale(mul(X, X), -1)),
             add(scale(ONE, 4), scale(mul(X, X), -1)))
    fy = mul(add(scale(ONE, 4), scale(mul(Y, Y), -1)),
             add(scale(ONE, 4), scale(mul(Y, Y), -1)))
    psi = mul(fx, fy, add(ONE, Y))
    vx = derivative(psi, "y")
    vy = scale(derivative(psi, "x"), -1)
    div_v = add(derivative(vx, "x"), derivative(vy, "y"))
    assert not div_v

    # Strong outer boundary: v == 0 as a polynomial trace, not merely at nodes.
    for x0 in (-2, 2):
        assert not restrict_x(vx, x0)
        assert not restrict_x(vy, x0)
    for y0 in (-2, 2):
        assert not restrict_y(vx, y0)
        assert not restrict_y(vy, y0)

    # p=x, f=grad p=(1,0).  Because div v=0, the volume pressure
    # coupling vanishes identically, but the weak-boundary pressure work need not.
    forcing_pairing = (
        integrate_rect(vx, -2, 2, -2, 2)
        - integrate_rect(vx, -1, 1, -1, 1)
    )
    pressure_volume_pairing = Q(0)

    # Inner-square outward normal is outward from the fluid, i.e. into the hole.
    p_vx = mul(X, vx)
    p_vy = mul(X, vy)
    edge_flux = {
        "inner_right_x=1": -integrate_1d(restrict_x(p_vx, 1), -1, 1),
        "inner_left_x=-1": integrate_1d(restrict_x(p_vx, -1), -1, 1),
        "inner_top_y=1": -integrate_1d(restrict_y(p_vy, 1), -1, 1),
        "inner_bottom_y=-1": integrate_1d(restrict_y(p_vy, -1), -1, 1),
    }
    pressure_boundary_flux = sum(edge_flux.values(), Q(0))

    assert forcing_pairing == Q(-2436, 5)
    assert pressure_boundary_flux == forcing_pairing
    assert pressure_volume_pairing == 0

    return {
        "domain": "[-2,2]^2 minus [-1,1]^2",
        "strong_boundary": "outer square",
        "weak_boundary": "inner square",
        "pressure": "p=x",
        "forcing": "f=(1,0)",
        "stream_function": "(4-x^2)^2(4-y^2)^2(1+y)",
        "velocity": "v=(d_y psi,-d_x psi)",
        "velocity_degree": max(degree(vx), degree(vy)),
        "divergence_polynomial": {},
        "strong_outer_trace_zero": True,
        "forcing_pairing": str(forcing_pairing),
        "pressure_volume_pairing": str(pressure_volume_pairing),
        "pressure_boundary_flux": str(pressure_boundary_flux),
        "inner_edge_fluxes": {k: str(v) for k, v in edge_flux.items()},
        "pressure_free_kernel_lhs_at_u_zero": "0",
        "consistency_defect_lhs_minus_rhs": str(-forcing_pairing),
        "scope": (
            "mixed-boundary formulation-level witness; velocity degree 8, "
            "not a k=4 discrete-membership claim"
        ),
    }


def fully_weak_low_degree_witness() -> dict:
    # Omega=[0,1]^2, u=0, p=x, f=(1,0), v=(1,0).
    # v is degree 0 (hence belongs to any full P_k velocity space, k>=0)
    # and exactly divergence free.  If the boundary is weak, v is admissible.
    return {
        "domain": "[0,1]^2",
        "boundary": "fully weak",
        "pressure": "p=x",
        "forcing": "f=(1,0)",
        "test_velocity": "v=(1,0)",
        "velocity_degree": 0,
        "divergence": "0",
        "forcing_pairing": "1",
        "pressure_volume_pairing": "0",
        "pressure_boundary_flux": "1",
        "pressure_free_kernel_lhs_at_u_zero": "0",
        "consistency_defect_lhs_minus_rhs": "-1",
        "scope": "exact low-degree weak-boundary consistency witness",
    }


def certificate() -> dict:
    return {
        "schema": "commons.ridgway-zerograd-pressure-trace-counterexample/v1",
        "fully_weak_low_degree": fully_weak_low_degree_witness(),
        "strong_outer_weak_inner": square_annulus_witness(),
        "theorem_ceiling": (
            "proves a pressure-normal consistency defect for the pressure-free "
            "velocity Nitsche kernel when normal velocity is weak; does not prove "
            "the full prize theorem or a k=4 annulus lower bound"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(certificate(), indent=2, sort_keys=True))
