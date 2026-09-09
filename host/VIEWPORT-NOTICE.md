# Source and attribution

The viewport census/backfill implementation and tests in this package are
Apache-2.0. They were developed from the requirements in Commons issue #2407
and informed by two historical prototype Git blobs named by that issue:

- checker prototype `8e284bd87b7680ea4a765478ad80b9019b0873d1`;
- repair prototype `8fbeda0bfce1fe1894992ed4672aab53638e4c78`.

The delivered implementation is a new hardened version: tracked recursive
inventory, document classification, bounded deterministic cursoring, complete
inventory preimages, per-file postimages, atomic writes, idempotent reapply and
focused failure coverage. The historical prototype bytes are not republished.
