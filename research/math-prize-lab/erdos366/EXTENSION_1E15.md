# Erdős 366 exact search extension through 10^15

This is finite computational evidence, not a proof of global nonexistence.

The extension keeps the canonical enumeration of every 3-full successor m=n+1 but removes the sqrt(B) prime-table scaling bottleneck. Predecessors are rejected by exact p||n certificates when possible; unresolved 64-bit remainders use deterministic Miller-Rabin and exact factorization. Pollard-Brent is only an accelerator and retains an exact trial-division fallback.

Retained run:
- bound n+1 <= 10^15
- 434,571 three-full successors
- 352,367 small-residue rejections
- 31,183 prime-remainder rejections
- 51,021 exact-factorization rejections
- 0 witnesses
- record digest sha256:1af48a7652b35372d41eabe2e1192940d89ef3d9b85aa1f885bb7e6e898edad6
- observed wall time 23.31 s on Python 3.13

Verification: 9/9 normal + 9/9 optimized tests. The tests include brute-force agreement, exact factor reconstruction, deterministic shard partitioning, stable digests, and reproduction of the landed 10^12 result (41,135 candidates, 0 witnesses).

Commands:

python3 -m unittest -v research/math-prize-lab/erdos366/test_erdos366_extend.py
python3 -O -m unittest -v research/math-prize-lab/erdos366/test_erdos366_extend.py
python3 research/math-prize-lab/erdos366/erdos366_extend.py --bound 1000000000000000 --pretty

See receipt_1e15.json for the exact run and claim boundaries.
