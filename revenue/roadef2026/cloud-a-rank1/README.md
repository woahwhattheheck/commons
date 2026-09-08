# ROADEF set-A rank-1 follow-through

This bounded development follow-through consumes the completed historical set-A
calibration and evaluates only `setA-04`, `setA-14`, and `setA-16`. It reconstructs
the frozen three-kernel candidate exactly, recovers the exact authoritative
incumbent solutions from run `34197720573`, and resumes the unchanged candidate,
SEDGE, and FLORA binaries independently for 60 seconds per lane.

Every output is checked by the unchanged official checker at six and twelve
decimal places. Comparisons use complete sorted Decimal vectors with no cost
tiebreak. The result records all route changes, first differing ranks, source,
input, solution, statistics and checker hashes. The published sprint vector is a
historical comparator; this workflow does not claim matched hardware, matched
allowance, qualification rank, or general superiority.

The three authoritative incumbent gaps are:

- A04: time 1, link 43 → 12, MLU 0.587276 versus reference 0.581237;
- A14: time 1, link 215 → 122, MLU 0.533147 versus reference 0.517621;
- A16: time 1, link 131 → 228, MLU 0.079918 versus reference 0.044262.

The workflow does not modify the frozen candidate, final B panel, S139 draft,
attachment, or submission state. It uses no new solver implementation or input
exporter and does not rerun the other 17 A cases.
