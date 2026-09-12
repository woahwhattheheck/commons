# TITAN-V3-S13-CERTIFIED-PREFIX695-RUNTIME-COMPOSITION-20260910-01

## Exact stack

- direct parent: Commons draft #12095 head `05b64a03855be9856a03801ed608407707eb0404`
- certificate donor: Commons draft #12067 head `cbfff2bec813e2c2609ce9c5819b74669e98c566`
- certificate implementation blob: `89a3325eb541ae0e8a81e1e0a426292820f10d98`
- source replay: episode `107223760`, SHA-256
  `c72ad0d81c65f93f4988f147e5e4bd50a2edfa3aaa631455e76e9e80dfb81b18`
- prefix cutoff: step `695`

## Decision rule

The incumbent action is computed first on every observation. A source route row
may replace the selected components only when all of the following hold:

1. the live player equals the source replay seat;
2. the exact route row exists and is well formed;
3. the action hash and reviewed certificate mode/seat are unchanged; and
4. the certificate recomputed from the live prestate equals the embedded source
   certificate byte-for-byte under canonical JSON.

Any failure latches permanent handoff before route emission. There is no retry
later in the trajectory.

## Evidence boundary

This is an applicability and fail-closure carrier. It does not prove source
trajectory reachability from the frozen incumbent, hidden-rival market outcome,
gameplay strength, leaderboard transfer, or promotion readiness. The dedicated
frozen panel reuses existing seeds only and reports those questions separately.
