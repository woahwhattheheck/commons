# Ridgway–Freudenthal Scott–Vogelius lane

Issue: https://github.com/woahwhattheheck/commons/issues/14999

This directory is the isolated research surface required by the issue.
It does **not** claim the $1,000 prize and does **not** submit anything
to the Ridgway Scott Foundation.

## Pinned claim (from the sponsor PDF)

Spaces, on a Freudenthal/Kuhn tetrahedral mesh of a cubical domain, with vanishing velocity on the boundary:

V_h^k = continuous vector P_k vanishing on the boundary
Pi_h = div V_h^k

Advertised theorem: gamma > 0 independent of h for all k >= 4.
Zhang proved k >= 6. Open advertised cases: k = 4 and k = 5.

Sponsor sources:
- https://people.cs.uchicago.edu/~ridg/prizes/kuhnprize.pdf
- https://people.cs.uchicago.edu/~ridg/prizes/prizes.html
- Farrell-Mitchell-Scott, arXiv:2211.05494

## Certified here

1. Exact six-tet Kuhn cube; each 6*Vol = +1; n-grid has 6 n^3 tets.
2. dim P_k(R^3) = binom(k+3,3).
3. Exact Q-rank of local div : [P_k]^3 -> P_{k-1} equals dim P_{k-1} for k=1..6.
   Continuity, boundary vanishing, and singular-vertex constraints are not included.

## Not certified

- Mesh-uniform gamma for k=4 or k=5.
- Assembled-mesh structure of div V_h^k.
- Prize, payment, or sponsor submission.
- Alfyorov Research Square rs-10887173 (2026-09-02) is EXTERNAL UNVERIFIED.

## Zhang degree cut

Zhang needs interior/face bubbles rich enough to kill residual edge-star modes after a Fortin correction. That inventory is enough at k>=6 on this family. k=4,5 leave a raw edge-star residual. That is the open algebraic gap.

## Run

python3 test_certificates.py

Receipt: receipts/local_div_rank.json.
