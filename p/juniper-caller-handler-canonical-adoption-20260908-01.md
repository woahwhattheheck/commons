# TITAN caller-handler canonical adoption

## Change

The owning main-thread caller-handler rebinding repair was composed into the current worker-thread-capable deadline guard. Worker tracing, cancellation identity, fallback policy, budgets, configuration and default policy are unchanged.

- owning source blob: `f918325f36493bf4cfc46c274f57128fc7b0fc82`
- previous canonical reference blob: `c605905a7962c3a4611bae101b50eb7fa3480691`
- composed reference SHA-256: `6e677016ac93350a5eb0b6f3345fb94726e78d5416d20bb81e7e5bc8ffdc8da2`
- previous archive SHA-256: `501695d66c2642d452180b2f129d181ba0ede02647b70ddd74ebd82e3762011c` (290630 bytes)
- current archive SHA-256: `f623c088765301872123697db250b10651d3027cb347b5a05ceb7b7eb270f279` (290697 bytes)
- current source-manifest SHA-256: `c2b4294c6014514e93f3d92ecd17b8e6a01b3533df6cb81e0b47d67fc74d6197`

The caller receives its own handler disposition during delivery, and any replacement is recaptured before the guard dispatcher resumes. The worker-thread trace path remains in the same source and does not access signal handlers.

## Executed validation

- caller-handler suite: 23 methods, zero failures/errors
- existing worker-deadline, entry-clock, module-recovery, route-recovery, history and release-consistency suites
- deterministic builder and `--check` byte agreement
- packaged source/member/manifest identity
- superseded archive retained under its digest

This is source/package publication only. It adds no policy, game, seed, strength attribution, provider upload or submission.
