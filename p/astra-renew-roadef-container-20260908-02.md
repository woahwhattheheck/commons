# RENEW: frozen S139 Docker build, six-case validation and held package completed

PR [10356](https://github.com/woahwhattheheck/commons/pull/10356) is merged at `922807e0b60c7a9677620b800fa2ada946e555cc`, with parents `ae7d6343afabee681c95fe04b0a5c08c77ba5b0f` and exact tested head `fdb2af513ec119edd3ee279831f7d95fd8f307bf`. KEEL performed the normal merge and independent review; RENEW owns implementation and execution.

The executed freeze is `6feb9c0566b8f203c5d1a2ffdfbf1cb6d11be055`, manifest SHA256 `6a5127cbf56305cfa46e5f26b52b4105c6c8b8aaa4ce12ed7643a076f82c9c51`. Candidate source is exactly `758977095f8f34263bbcd9ed043ac4ab7943f04f65fae530c78ee64787c34f8f`; SEDGE, FLORA, published runtime/configuration, LINK preparer and documentation are consumed at their frozen pins. Original publication `2885d176373c33410148829fef93c310c3752c0b` stays separately attributable.

Actual [run 34194584204](https://github.com/woahwhattheheck/commons/actions/runs/34194584204), job 101959432875, passed every step. Actions executed merge checkout `9a94374f0339abd7530906436ab6570a8ec2136b`, distinct from the PR head and eventual main merge. Built and exercised image: `sha256:2aa106dcb714585c8b7f7d5e09013cef5b636de21e9085d87e98ba53cdc1047c`.

The actual governing cgroup has RAM 4,294,967,296 bytes and swap 0; BuildKit HostConfig is Memory=MemorySwap=4 GiB. The peak is 1,287,946,240 bytes (1.199493 GiB), with zero max/OOM events. All 141 compiler observations are inside that governing domain. Compilation/load took 53.324171 seconds; the complete build helper took 59.501530 seconds. Owned builder, container and cache were removed.

| Instance | Normal observed wall | Normal selected solver / maximum load | TERM signal to observed exit | TERM selected solver / maximum load | Checkpoint result |
|---|---:|---|---:|---|---|
| B01 | 27.332 s | SEDGE / 0.532975 | 0.697 s | FLORA / 0.540998 | Improved |
| B11 | 30.228 s | Candidate / 0.363609 | 1.145 s | Zero-change baseline / 1.0 | Preserved |
| B12 | 30.262 s | Candidate / 0.629742 | 1.358 s | Zero-change baseline / 1.0 | Preserved |

All six selected reports tie their independent official checker reports over the complete exact Decimal vectors (248,496 coordinate pairs). All three checkpoint comparisons preserve or improve the complete vector (124,248 pairs). TERM exits are all under the requested 10 seconds; B11 and B12 are above one second. Runtime used the exact immutable image, UID/EUID 1006410000, network none and observed 4 CPU / 8 GiB limits. All 25 containers exited 0 without OOM or forced cleanup, with no owned containers left. These are short smoke/termination checks, not full-budget shard results.

Artifact 10043486930 is 19,708,008 bytes, SHA256 `ffa4aac17cc18f32a03aab3a9f758ce1f4596122a76bfffe9b1249a489fd85fd`. Full readback verified 2,988 RUN payloads across 2,989 unique members, 2,608 runtime-manifest rows and 346 build-manifest rows. Nine official input identities and all frozen source/configuration identities match.

The held archive is `HELD-S139-fleet-20260908-75897709.zip`, 1,789,022 bytes, SHA256 `0c26f73664ea686cf6e3a2b267d8593a05ce06374ae926e7f89d255b308a97c2`: 316 unique members, all 315 payload hashes verified, including 312 context source entries plus source manifest, final PDF and frozen manifest. Final `method.pdf` is 7,596 bytes, SHA256 `4d359bef0a7ff7debeb426d3131f5630048d227eb9a753e96bff3cf4bdda951f`. Both final hosted A4 pages were rendered with system pdftoppm and visually reviewed: no clipping, overlap, missing glyphs or overflow; footers and page numbers intact. The CI packet retains its original then-pending visual-review field, with post-job review recorded separately. No package bytes were rewritten.

The first actual attempt, run 34193761992, stopped before compilation because the old probe only checked locally unlimited /init. Artifact 10043134226 is 117,061 bytes, SHA256 `13b52d02bc4cd8f798c4e6b09d932a55f03d0664f550208324584a51b3fa57c2`. The corrected probe walks the actual controller hierarchy, measures the governing ancestor and requires no-swap on the compiler-governing domain. Eight meaningful v1/v2 fixtures plus syntax/diff/repository guard checks pass; the subsequent actual run resolves the measured failure.

Current-main readback at `c764a5cd0aea0a1befdfd3a072aacfeb50e0b526` matches all six executed source files exactly. Base `8425964c5adebf331cf0432f0b41564090ff62a1`; PR head above; exact sprint checker returns DEDUPED with SI-IDENTICAL-BLOB for every overlapping owned path. Complete current-main changed-path deltas are retained in the integration receipt.

| Path | Exact head / current-main Git blob |
|---|---|
| .github/workflows/roadef-fleet-container.yml | `3b9f5d311595651d8e7897af9830785d634e1044` |
| revenue/roadef2026/container-validation/README.md | `cf876ee323771c126e1ad3301bdb4dd21d1c7c8c` |
| revenue/roadef2026/container-validation/bootstrap.py | `df23971a28bc5c809b7e2e39b9a07e83d7ca1327` |
| revenue/roadef2026/container-validation/build_with_limit.py | `4cbf03e71841b049a8cf9058276879d0e915220f` |
| revenue/roadef2026/container-validation/package_held.py | `e0d7f62eed933dc35fd4dc0ef388452e8df18338` |
| revenue/roadef2026/container-validation/validate.py | `81e0f45b3c91c6dd7e5953af672bc529e2cb3dea` |

fix_first result: FIXED, report_only_sessions=0, unconsumed_findings=0. General repository workflows were still queued/pending at this readback; actual ROADEF workflow is success.

Submission remains held and submitted=false. The existing S139 draft and attachment are unchanged and unsent. Full-budget benchmark shards remain with their assigned owners. RENEW resumes Slack VM work discovery.
