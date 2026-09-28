# V3.1 rating split: submission identity, not a source-code regression

Observed 2026-09-27. This note audits the historical V3.1 rating discrepancy in [TITAN-WIN-20260927-01](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1790531203742919). It does not change an agent or authorize an upload.

| Submission | Archive custody | Rating observation |
| --- | --- | --- |
| Original #56172377 | V3.1 source `a90d888f03987ef0b35cfd20ec3519c6144db08a`; archive SHA-256 `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`, 579,497 bytes, 148 members; submitted 2026-09-11 20:36:50 UTC | 2823.3, rank 63 in a Sep 12 snapshot, as recorded in the fleet order. Historical peak, not current rank. |
| Preservation reupload #56220248 | [Release readback](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789356885914399) identifies the **same local archive SHA-256**, COMPLETE and public-active on Sep 14 | **Fresh initial rating 600.0** on Sep 14; 1351.6 in the Sep 27 fleet order. |

The original custody is recorded in [V3-MANIFEST.json](../../v4/donor/V3-MANIFEST.json). The release readback reports the reupload's local archive digest and COMPLETE state; it is not a cryptographic hash returned by Kaggle for the remote stored bytes.

## Established cause and remaining possibilities

**The old rating did not transfer.** The same archive was uploaded under a new submission ID and the provider readback explicitly gave #56220248 a fresh 600.0. Kaggle's [Evaluation rules](https://www.kaggle.com/competitions/kaggriculture/overview/evaluation) say a passing upload receives a default rating and then joins matchmaking; wins/losses and opponents' ratings move it over subsequent episodes. The 2823.3 and 1351.6 observations are therefore different submission histories at different dates, not a paired quality measurement.

The size of the **post-reset** difference is unresolved. Kaggle matches bots with similar skill ratings, and newer bots play episodes much more frequently. The opponent pool, episode count, and pace may differ between these submission histories; these are plausible contributors, not findings about this particular bot. We do not have the two submission IDs' episode histories, opponent version/rating distributions, status-by-episode, or per-game rewards in this repo. COMPLETE self-play and the frozen archive custody do not rule out a later callback failure or an unfavorable matchup. Kaggle does not publish an update equation that would let us derive 1351.6 from the archive alone.

## One discriminating provider readback

The Kaggle custodian should export public episodes separately for #56172377 and #56220248, with each episode's timestamp, seed, seat, exact opponent submission ID, opponent rating at match time if available, terminal status, both bank rewards, and any agent error/log. Include a timestamped submission record for each ID with W/T/L, rating, first/last episode and total public episodes. Then compare:

1. **Execution:** completed 720-turn games, ERROR/timeout/fallback rate, terminal bank distribution. Any failure cluster makes the cause concrete.
2. **Matchmaking and pool:** opponent submission IDs/rating bands and match dates. Distinguish early 600-band placement from later opponents and from changed versions of the same team.
3. **Outcomes and rating:** W/T/L by opponent band and seat, rating trajectory versus number of completed games. Do not infer Kaggle's private rating equation from coin margins.
4. **Same-cell behavior:** if a common seed/opponent version exists, replay both seats against that exact version with the frozen archive. This tests policy execution while holding game conditions fixed; the two live aggregate ratings cannot.

The [Sep 12 live V4 bank](../../v5/kaggle-live-20260912/README.md) demonstrates why snapshots matter: another submission, #56182437, moved from 1428.2 after 10 public wins to 1622.4 after 14 wins and 2 losses within about 25 minutes. It is a different policy and cannot identify the V3.1 cause.

At the Sep 27 17:42 UTC readback, the latest active pair was challenger #56614912 and D2 #56220277; #56220248 is no longer an active final slot. Kaggle staff say the final Bradley–Terry tournament uses games only when **both** submissions are active at the deadline and the team is ranked by the better of its two active entries ([episode eligibility](https://www.kaggle.com/competitions/kaggriculture/discussion/732931), [team score](https://www.kaggle.com/competitions/kaggriculture/discussion/739410)). Preserve the current pair unless the composition and slot custodian has a measured replacement. Reuploading the old archive again would start another rating history, not recover #56172377's peak.
